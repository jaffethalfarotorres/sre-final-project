#!/usr/bin/env python3
"""
AI-assisted SRE setup (SRE Academy 2027, modules M17-M18), the same on macOS, Windows and Linux.

1. Creates a Grafana service account with the Viewer role and a token that expires in 8 hours.
2. Stores the token in the "mcp-grafana-token" Secret and deploys the Grafana MCP server in the cluster.
3. Creates the read-only Kubernetes identity (built-in "view" role) and writes a kubeconfig for it,
   valid for 8 hours, to ~/.kube/sre-ai-readonly.config (outside the repository).
4. Checks that the MCP server answers and prints the tools it exposes.

Afterwards run scripts/dashboards.* (it forwards the MCP server to http://localhost:8000/mcp) and open the
repository in Claude Code or IBM Bob: .mcp.json and .bob/mcp.json already point at that URL.

    python scripts/ai_setup.py            (use python3 on Mac/Linux)
"""

import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAFANA_PORT = 13000
MCP_PORT = 18000
KUBECONFIG_OUT = Path.home() / ".kube" / "sre-ai-readonly.config"


def kubectl(*args, check=True, stdin=None):
    result = subprocess.run(["kubectl", *args], capture_output=True, text=True, input=stdin)
    if check and result.returncode != 0:
        sys.exit(f"kubectl {' '.join(args)} failed:\n{result.stderr}")
    return result.stdout.strip()


def http(method, url, body=None, headers=None):
    if not url.startswith("http://localhost:"):  # only the local port-forwards
        raise ValueError(url)
    request = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
        return response.status, response.read().decode(), response.headers


def port_forward(target, local, remote):
    process = subprocess.Popen(["kubectl", "port-forward", "-n", "monitoring", target, f"{local}:{remote}"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(4)
    return process


def grafana_viewer_token():
    secret = kubectl("get", "secret", "grafana-admin-credentials", "-n", "monitoring", "-o", "json")
    data = json.loads(secret)["data"]
    user = base64.b64decode(data["admin-user"]).decode()
    password = base64.b64decode(data["admin-password"]).decode()
    auth = {"Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()}
    base = f"http://localhost:{GRAFANA_PORT}/api"

    _, body, _ = http("GET", f"{base}/serviceaccounts/search?query=ai-viewer", headers=auth)
    accounts = json.loads(body)["serviceAccounts"]
    if accounts:
        account_id = accounts[0]["id"]
    else:
        _, body, _ = http("POST", f"{base}/serviceaccounts", {"name": "ai-viewer", "role": "Viewer"}, auth)
        account_id = json.loads(body)["id"]
    name = f"mcp-{int(time.time())}"
    _, body, _ = http("POST", f"{base}/serviceaccounts/{account_id}/tokens",
                      {"name": name, "secondsToLive": 8 * 3600}, auth)
    return json.loads(body)["key"]


def mcp_tools():
    """Initialize an MCP session over streamable HTTP and list the server's tools."""
    url = f"http://localhost:{MCP_PORT}/mcp"
    accept = {"Accept": "application/json, text/event-stream", "Host": "localhost:8000"}
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "sre-lab-setup", "version": "1.0"}}}
    _, _, headers = http("POST", url, init, accept)
    session = {"Mcp-Session-Id": headers.get("Mcp-Session-Id", ""), **accept}
    http("POST", url, {"jsonrpc": "2.0", "method": "notifications/initialized"}, session)
    _, body, _ = http("POST", url, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, session)
    try:
        message = json.loads(body)  # plain JSON response
    except json.JSONDecodeError:  # or a server-sent event stream: take the first "data:" line
        line = next(line for line in body.splitlines() if line.startswith("data:"))
        message = json.loads(line[len("data:"):])
    return sorted(tool["name"] for tool in message["result"]["tools"])


def main():
    sys.stdout.reconfigure(line_buffering=True)  # show progress immediately, even when piped
    print("1) Creating a Grafana Viewer token for the MCP server (expires in 8 hours)...")
    forward = port_forward("service/grafana", GRAFANA_PORT, 3000)
    try:
        token = grafana_viewer_token()
    finally:
        forward.terminate()
    secret = kubectl("create", "secret", "generic", "mcp-grafana-token", "-n", "monitoring",
                     f"--from-literal=token={token}", "--dry-run=client", "-o", "yaml")
    kubectl("apply", "-f", "-", stdin=secret)

    print("2) Deploying the Grafana MCP server and the read-only Kubernetes identity...")
    kubectl("apply", "-f", str(ROOT / "k8s" / "ai" / "readonly-rbac.yaml"))
    kubectl("apply", "-f", str(ROOT / "k8s" / "ai" / "mcp-grafana.yaml"))
    kubectl("rollout", "restart", "deployment/mcp-grafana", "-n", "monitoring")  # pick up a new token
    kubectl("rollout", "status", "deployment/mcp-grafana", "-n", "monitoring", "--timeout=180s")

    print(f"3) Writing a read-only kubeconfig (8 hours) to {KUBECONFIG_OUT} ...")
    sa_token = kubectl("create", "token", "ai-readonly", "-n", "monitoring", "--duration=8h")
    server = kubectl("config", "view", "--minify", "-o", "jsonpath={.clusters[0].cluster.server}")
    ca = kubectl("config", "view", "--minify", "--raw", "-o",
                 "jsonpath={.clusters[0].cluster.certificate-authority-data}")
    if not ca:  # Minikube stores the CA as a file path; embed it
        ca_path = kubectl("config", "view", "--minify", "-o", "jsonpath={.clusters[0].cluster.certificate-authority}")
        ca = base64.b64encode(Path(ca_path).read_bytes()).decode()
    KUBECONFIG_OUT.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    config = {
        "apiVersion": "v1", "kind": "Config", "current-context": "ai-readonly",
        "clusters": [{"name": "minikube", "cluster": {"server": server, "certificate-authority-data": ca}}],
        "users": [{"name": "ai-readonly", "user": {"token": sa_token}}],
        "contexts": [{"name": "ai-readonly", "context": {"cluster": "minikube", "user": "ai-readonly"}}],
    }
    # The file holds a bearer token: readable by its owner only (0600), also when an older file exists.
    fd = os.open(KUBECONFIG_OUT, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.chmod(KUBECONFIG_OUT, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(json.dumps(config, indent=2))
    can_delete = subprocess.run(["kubectl", "--kubeconfig", str(KUBECONFIG_OUT), "auth", "can-i", "delete",
                                 "pods", "-n", "application"], capture_output=True, text=True).stdout.strip()
    print(f"   ai-readonly can delete pods? {can_delete}  (expected: no)")

    print("4) Checking the MCP server...")
    forward = port_forward("service/mcp-grafana", MCP_PORT, 8000)
    try:
        tools = mcp_tools()
    finally:
        forward.terminate()
    print(f"   {len(tools)} tools available (Viewer token: Grafana writes are refused), "
          f"for example: {', '.join(tools[:8])}")
    print("\nNext:")
    print("  - Run scripts/dashboards.sh (Mac/WSL2) or scripts\\dashboards.ps1: it forwards http://localhost:8000/mcp")
    print(f"  - For cluster access, start your AI tool with KUBECONFIG={KUBECONFIG_OUT}")
    print("  - Open this folder in Claude Code or IBM Bob and follow docs/AI-SRE.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
