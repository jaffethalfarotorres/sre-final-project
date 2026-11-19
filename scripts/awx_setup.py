#!/usr/bin/env python3
"""
AWX incident automation (SRE Academy exercise 13), the same on macOS, Windows and Linux.

1. Installs the AWX Operator and a laptop-sized AWX instance (about 10 minutes the first time).
2. Configures AWX through its REST API: a project pointing at this GitHub repository, an inventory,
   and two job templates built from the Ansible runbooks:
     - collect-diagnostics  read-only, launched automatically by Alertmanager on critical alerts
     - restart-app          remediation, launched only by a person after reading the diagnostics
3. Stores an AWX API token in the "awx-webhook-token" Secret that Alertmanager uses, and launches
   collect-diagnostics once to prove the chain works.

    python scripts/awx_setup.py            (use python3 on Mac/Linux)
Needs about 2.5 GB of free memory in Minikube (see docs/labs/06-delivery-resilience-policy.md,
"Memory rule", and docs/GUIDE.md section 7b).
"""

import base64
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/jaffethalfarotorres/sre-final-project"
LOCAL_PORT = 8052
API = f"http://localhost:{LOCAL_PORT}/api/v2"


def kubectl(*args, check=True, stdin=None):
    result = subprocess.run(["kubectl", *args], capture_output=True, text=True, input=stdin)
    if check and result.returncode != 0:
        sys.exit(f"kubectl {' '.join(args)} failed:\n{result.stderr}")
    return result.stdout.strip()


def wait_for(description, condition, timeout=1200, interval=10):
    started = time.time()
    while time.time() - started < timeout:
        if condition():
            return
        time.sleep(interval)
    sys.exit(f"Timed out waiting for {description}.")


class Awx:
    """Tiny AWX REST client with HTTP basic auth."""

    def __init__(self, user, password):
        self.auth = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()

    def call(self, method, path, body=None):
        url = f"{API}{path}"
        if not url.startswith("http://localhost:"):  # only ever talks to the local port-forward
            raise ValueError(f"unexpected AWX URL: {url}")
        request = urllib.request.Request(url, method=method,
                                         data=json.dumps(body).encode() if body is not None else None,
                                         headers={"Authorization": self.auth, "Content-Type": "application/json"})
        # The URL scheme and host were checked above, so B310 (arbitrary URL schemes) does not apply.
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
                text = response.read().decode()
                return json.loads(text) if text else {}
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:500]
            raise RuntimeError(f"AWX API {method} {path} failed with HTTP {error.code}: {detail}") from error

    def find_or_create(self, collection, name, body):
        found = self.call("GET", f"/{collection}/?name={urllib.request.quote(name)}")["results"]
        if found:
            return self.call("PATCH", f"/{collection}/{found[0]['id']}/", body)
        return self.call("POST", f"/{collection}/", {"name": name, **body})


def install():
    print("Installing the AWX Operator (kubectl apply -k awx)...")
    kubectl("create", "namespace", "awx", check=False)
    for attempt in range(3):  # the CRD may need a moment before the first apply fully succeeds
        if subprocess.run(["kubectl", "apply", "-k", str(ROOT / "awx")], capture_output=True).returncode == 0:
            break
        time.sleep(10)
    kubectl("rollout", "status", "deployment/awx-operator-controller-manager", "-n", "awx", "--timeout=600s")
    kubectl("apply", "-f", str(ROOT / "awx" / "awx.yaml"))
    kubectl("apply", "-f", str(ROOT / "awx" / "rbac.yaml"))
    print("Waiting for AWX to start (the first time takes about 10 minutes)...")
    wait_for("the AWX web deployment", lambda: subprocess.run(
        ["kubectl", "get", "deployment", "awx-web", "-n", "awx"], capture_output=True).returncode == 0)
    kubectl("rollout", "status", "deployment/awx-web", "-n", "awx", "--timeout=1200s")
    kubectl("rollout", "status", "deployment/awx-task", "-n", "awx", "--timeout=1200s")


def configure(awx):
    org = awx.call("GET", "/organizations/?name=Default")["results"][0]["id"]
    project = awx.find_or_create("projects", "sre-final-project", {
        "organization": org, "scm_type": "git", "scm_url": REPO_URL, "scm_branch": "main",
        "scm_update_on_launch": True, "description": "Runbooks from the SRE final project repository"})
    print(f"Project sre-final-project (id {project['id']}): syncing from GitHub...")
    # Start a fresh sync and follow that job (the project status may still show an older sync).
    update = awx.call("POST", f"/projects/{project['id']}/update/", {})
    update_id = update.get("project_update") or update.get("id")

    def project_ready():
        status = awx.call("GET", f"/project_updates/{update_id}/")["status"]
        if status in ("failed", "error", "canceled"):
            sys.exit(f"AWX could not sync the project from GitHub (project update {update_id} {status}). "
                     "Check it in the AWX UI under Jobs.")
        return status == "successful"
    wait_for("the project sync", project_ready, timeout=600, interval=5)

    inventory = awx.find_or_create("inventories", "minikube", {"organization": org,
                                                               "description": "Runs runbooks inside the cluster"})
    group = awx.call("GET", f"/inventories/{inventory['id']}/groups/?name=local")["results"]
    group = group[0] if group else awx.call("POST", f"/inventories/{inventory['id']}/groups/", {"name": "local"})
    host_vars = json.dumps({"ansible_connection": "local",
                            "ansible_python_interpreter": "{{ ansible_playbook_python }}"})
    host = awx.call("GET", f"/inventories/{inventory['id']}/hosts/?name=localhost")["results"]
    if not host:
        host = [awx.call("POST", f"/inventories/{inventory['id']}/hosts/",
                         {"name": "localhost", "variables": host_vars})]
    host = host[0]
    try:
        awx.call("POST", f"/groups/{group['id']}/hosts/", {"id": host["id"]})
    except RuntimeError:
        pass  # already in the group

    # Kubernetes credential for the jobs: the least-privilege awx-runbooks ServiceAccount (awx/rbac.yaml).
    token = base64.b64decode(kubectl("get", "secret", "awx-runbooks-token", "-n", "awx",
                                     "-o", "jsonpath={.data.token}")).decode()
    ca_cert = base64.b64decode(kubectl("get", "secret", "awx-runbooks-token", "-n", "awx",
                                       "-o", "jsonpath={.data.ca\\.crt}")).decode()
    k8s_type = awx.call("GET", "/credential_types/?namespace=kubernetes_bearer_token")["results"][0]["id"]
    credential = awx.find_or_create("credentials", "minikube-awx-runbooks", {
        "organization": org, "credential_type": k8s_type,
        "description": "ServiceAccount awx/awx-runbooks (read app namespace, patch the app Deployment)",
        "inputs": {"host": "https://kubernetes.default.svc", "bearer_token": token,
                   "verify_ssl": True, "ssl_ca_cert": ca_cert}})

    templates = {}
    for name, playbook, description, extra in (
        ("collect-diagnostics", "ansible/runbooks/collect-diagnostics.yml",
         "Read-only. Launched automatically by Alertmanager for critical alerts.", {"print_report": True}),
        ("restart-app", "ansible/runbooks/restart-app.yml",
         "Remediation. Launch by hand after reading the diagnostics (human approval).", {}),
    ):
        templates[name] = awx.find_or_create("job_templates", name, {
            "project": project["id"], "inventory": inventory["id"], "playbook": playbook,
            "description": description, "extra_vars": json.dumps(extra)})
        attached = awx.call("GET", f"/job_templates/{templates[name]['id']}/credentials/")["results"]
        if not any(c["id"] == credential["id"] for c in attached):
            awx.call("POST", f"/job_templates/{templates[name]['id']}/credentials/", {"id": credential["id"]})
        print(f"Job template {name} (id {templates[name]['id']})")
    return templates


def main():
    sys.stdout.reconfigure(line_buffering=True)  # show progress immediately, even when piped
    install()
    password = base64.b64decode(kubectl("get", "secret", "awx-admin-password", "-n", "awx",
                                        "-o", "jsonpath={.data.password}")).decode()
    forward = subprocess.Popen(["kubectl", "port-forward", "-n", "awx", "service/awx-service", f"{LOCAL_PORT}:80"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        awx = Awx("admin", password)
        wait_for("the AWX API", lambda: _ping(awx), timeout=300, interval=5)
        templates = configure(awx)

        token = awx.call("POST", "/tokens/", {"description": "Alertmanager webhook", "scope": "write"})["token"]
        secret = kubectl("create", "secret", "generic", "awx-webhook-token", "-n", "monitoring",
                         f"--from-literal=token={token}", "--dry-run=client", "-o", "yaml")
        kubectl("apply", "-f", "-", stdin=secret)
        kubectl("rollout", "restart", "deployment/alertmanager", "-n", "monitoring")
        print("Alertmanager can now launch collect-diagnostics (token stored in Secret monitoring/awx-webhook-token).")

        job = awx.call("POST", f"/job_templates/{templates['collect-diagnostics']['id']}/launch/", {})
        print(f"Test launch: job {job['id']} started...")
        wait_for("the test job", lambda: awx.call("GET", f"/jobs/{job['id']}/")["status"] in
                 ("successful", "failed", "error", "canceled"), timeout=600, interval=5)
        status = awx.call("GET", f"/jobs/{job['id']}/")["status"]
        print(f"Test job {job['id']}: {status}")
        print("\nOpen AWX:  kubectl port-forward -n awx service/awx-service 8052:80   then http://localhost:8052")
        print("           user admin, password: kubectl get secret awx-admin-password -n awx "
              "-o jsonpath={.data.password} (base64)")
        return 0 if status == "successful" else 1
    finally:
        forward.terminate()


def _ping(awx):
    try:
        return awx.call("GET", "/ping/") is not None
    except (RuntimeError, urllib.error.URLError, ConnectionError, TimeoutError):
        return False


if __name__ == "__main__":
    sys.exit(main())
