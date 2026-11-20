#!/usr/bin/env python3
"""
Smoke test for the SRE final project: one command a teacher, a grader or an AI coding agent can run.

    Windows (PowerShell):  python scripts\\smoke_test.py            (add --cluster when the lab is running)
    Mac or Linux:          python3 scripts/smoke_test.py

It never deploys, changes, commits or deletes anything in the project or the cluster (Python may leave its usual
__pycache__ folders, which Git ignores). It prints one line per check:

    PASS  the check ran and passed.
    FAIL  the check ran and failed (the output tail and a fix follow).
    SKIP  the check could not run on this laptop (the tool is missing or not started); the line says how.

Part A runs without a cluster: the main CI checks (pytest, flake8, the Kustomize render, Helm lint and the
Prometheus rule tests with promtool in Docker). CI also runs bandit, pip-audit, kubeconform and amtool.
Part B (--cluster) reads the running Minikube lab with
kubectl only: pods, Prometheus targets, loaded alert rules, Alertmanager and Grafana health.

Options:
    --cluster        also run part B against the current kubectl context (it must be "minikube")
    --quick          skip the promtool check (it pulls a 250 MB Docker image the first time)
    --no-setup       do not create .venv with pytest and flake8 when they are missing (they are then SKIP)
    --report FILE    also write the results as a Markdown table to FILE (a relative FILE is inside the repository;
                     reports/ is not tracked by Git)

Exit code: 1 if any line is FAIL, else 0. Uses only the Python standard library.
"""

import argparse
import collections
import datetime
import json
import os
import platform
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labpods  # noqa: E402

Result = collections.namedtuple("Result", "status name detail fix")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WINDOWS = platform.system() == "Windows"
PY = "python" if WINDOWS else "python3"
LAB_NAMESPACES = labpods.LAB_NAMESPACES
KEY_ALERTS = ("HighErrorRate", "ServiceDown", "ErrorBudgetFastBurn")
PROMETHEUS_IMAGE = "prom/prometheus:v2.54.1"
# Read-only GET requests through the Kubernetes API server's service proxy (no port-forward needed).
PROXY = "/api/v1/namespaces/monitoring/services/{svc}/proxy{path}"


def run(cmd, timeout=900):
    """Run a command in the repository root. Returns (exit code, combined output); 127 if not found."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        proc = subprocess.run(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              universal_newlines=True, timeout=timeout)
        return proc.returncode, proc.stdout or ""
    except FileNotFoundError:
        return 127, ""
    except subprocess.TimeoutExpired:
        return 124, "timed out after {} s".format(timeout)


def tail(text, lines=6):
    return "\n".join(line for line in text.strip().splitlines()[-lines:])


def last_line(text):
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    return lines[-1] if lines else ""


def has_module(name, python=None):
    code, _ = run([python or sys.executable, "-c", "import " + name], timeout=60)
    return code == 0


VENV_PY = os.path.join(ROOT, ".venv", "Scripts" if WINDOWS else "bin", "python.exe" if WINDOWS else "python")
DEV_PY = None  # the Python that has pytest and flake8; set by main()


def dev_python(setup=True):
    """A Python with pytest and flake8: this one, the repository's .venv, or a new .venv made now (gitignored)."""
    if has_module("pytest") and has_module("flake8"):
        return sys.executable
    if os.path.exists(VENV_PY) and has_module("pytest", VENV_PY) and has_module("flake8", VENV_PY):
        return VENV_PY
    if not setup:
        return None
    print("Setting up the test tools once, in .venv inside the repository (1-2 minutes; Git ignores it)...",
          flush=True)
    if not os.path.exists(VENV_PY) and run([sys.executable, "-m", "venv", ".venv"], timeout=300)[0] != 0:
        return None
    code, _ = run([VENV_PY, "-m", "pip", "install", "-q", "-r", "requirements-dev.txt"], timeout=900)
    return VENV_PY if code == 0 else None


DEV_FIX = ("install the dev tools once: {py} -m venv .venv, then .venv{sep}{bin}{sep}python -m pip install "
           "-r requirements-dev.txt, and run this script with .venv{sep}{bin}{sep}python").format(
    py=PY, sep="\\" if WINDOWS else "/", bin="Scripts" if WINDOWS else "bin")


# ---------- Part A: no cluster ----------

def check_python():
    v = sys.version_info
    found = "{}.{}.{}".format(v[0], v[1], v[2])
    if v >= (3, 10):
        return Result("PASS", "Python 3.10+", found, "")
    return Result("FAIL", "Python 3.10+", found, "install Python 3.10 or newer (docs/GUIDE.md step 2)")


def check_pytest():
    if not DEV_PY:
        return Result("SKIP", "Unit tests (pytest)", "pytest is not installed for this Python", DEV_FIX)
    code, out = run([DEV_PY, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"])
    if code == 0:
        return Result("PASS", "Unit tests (pytest)", last_line(out), "")
    return Result("FAIL", "Unit tests (pytest)", tail(out), "read the failing test above")


def check_flake8():
    if not DEV_PY:
        return Result("SKIP", "Code style (flake8)", "flake8 is not installed for this Python", DEV_FIX)
    code, out = run([DEV_PY, "-m", "flake8", "app", "tests", "scripts", ".claude/hooks",
                     "--max-line-length=120"])
    if code == 0:
        return Result("PASS", "Code style (flake8)", "no findings", "")
    return Result("FAIL", "Code style (flake8)", tail(out), "fix the lines above")


def check_kustomize():
    if not shutil.which("kubectl"):
        return Result("SKIP", "Kubernetes manifests (kubectl kustomize k8s)", "kubectl not found",
                      "run scripts/preflight.py, then the setup kit (docs/GUIDE.md step 2)")
    code, out = run(["kubectl", "kustomize", "k8s"], timeout=120)
    if code != 0:
        return Result("FAIL", "Kubernetes manifests (kubectl kustomize k8s)", tail(out), "fix the manifest above")
    kinds = [line.split(":", 1)[1].strip() for line in out.splitlines() if line.startswith("kind:")]
    return Result("PASS", "Kubernetes manifests (kubectl kustomize k8s)",
                  "{} objects render ({} Deployments)".format(len(kinds), kinds.count("Deployment")), "")


def check_helm():
    if not shutil.which("helm"):
        return Result("SKIP", "Helm chart (helm lint)", "helm not found (optional tool)",
                      "only needed for the Helm path; CI runs this check on every push")
    code, out = run(["helm", "lint", "helm/sre-metrics-app"], timeout=120)
    if code == 0:
        return Result("PASS", "Helm chart (helm lint)", last_line(out), "")
    return Result("FAIL", "Helm chart (helm lint)", tail(out), "fix the chart above")


def docker_running():
    if not shutil.which("docker"):
        return False
    code, _ = run(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=60)
    return code == 0


def check_promtool(quick):
    name = "Alert and SLO rules (promtool check + 2 rule test files)"
    if quick:
        return Result("SKIP", name, "skipped with --quick", "run again without --quick")
    if not docker_running():
        return Result("SKIP", name, "Docker is not running", "start Docker Desktop (or Rancher Desktop) and run again")
    script = ("promtool check rules k8s/config/prometheus/alerts.yml k8s/config/prometheus/slo.yml"
              " && promtool test rules tests/rules/*.test.yml")
    code, out = run(["docker", "run", "--rm", "-v", "{}:/w:ro".format(ROOT), "-w", "/w", "--entrypoint", "sh",
                     PROMETHEUS_IMAGE, "-c", script], timeout=900)
    if code == 0:
        checked = out.count("SUCCESS: ")
        tests = sum(1 for line in out.splitlines() if line.strip() == "SUCCESS")
        return Result("PASS", name, "{} rule files checked, {} rule test files passed".format(checked, tests), "")
    return Result("FAIL", name, tail(out), "fix the rule or the test named above")


# ---------- Part B: the running lab (read-only kubectl) ----------

def kubectl_json(args):
    code, out = run(["kubectl"] + args + ["-o", "json"], timeout=60)
    if code != 0:
        return None
    try:
        return json.loads(out)
    except ValueError:
        return None


def proxy_get(svc, path):
    code, out = run(["kubectl", "get", "--raw", PROXY.format(svc=svc, path=path)], timeout=60)
    return code, out


def check_context():
    code, out = run(["kubectl", "config", "current-context"], timeout=30)
    ctx = out.strip()
    if code == 0 and ctx == "minikube":
        return Result("PASS", "kubectl context", ctx, "")
    return Result("FAIL", "kubectl context", ctx or "none",
                  "start the lab (scripts/deploy.*) or run: kubectl config use-context minikube")


def check_pods():
    data = kubectl_json(["get", "pods", "-A"])
    if data is None:
        return Result("FAIL", "Lab pods", "kubectl cannot reach the cluster", "start it: minikube start")
    bad, count, app_ready = [], 0, 0
    for pod in data.get("items", []):
        ns = pod["metadata"]["namespace"]
        if ns not in LAB_NAMESPACES or not labpods.counts(pod):
            continue
        count += 1
        if not labpods.is_ready(pod):
            phase = pod.get("status", {}).get("phase") or "unknown"
            bad.append("{}/{} ({})".format(ns, pod["metadata"]["name"], phase))
        elif pod["metadata"]["name"].startswith("sre-metrics-app"):
            app_ready += 1
    if count == 0:
        return Result("FAIL", "Lab pods", "no pods in " + ", ".join(LAB_NAMESPACES),
                      "deploy the lab: scripts/deploy.ps1 (Windows) or scripts/deploy.sh")
    if bad or app_ready < 2:
        detail = "not ready: " + ", ".join(bad) if bad else "only {} app replica(s) ready".format(app_ready)
        return Result("FAIL", "Lab pods", detail, "wait a minute and run again; then kubectl describe pod <name>")
    return Result("PASS", "Lab pods", "{} pods ready in 3 namespaces, {} app replicas".format(count, app_ready), "")


def check_targets():
    code, out = proxy_get("prometheus:9090", "/api/v1/targets?state=active")
    try:
        targets = json.loads(out)["data"]["activeTargets"]
    except (ValueError, KeyError, TypeError):
        return Result("FAIL", "Prometheus targets", "Prometheus did not answer", "kubectl -n monitoring get pods")
    down = sorted({t["labels"].get("job", "?") for t in targets if t.get("health") != "up"})
    jobs = sorted({t["labels"].get("job", "?") for t in targets})
    if not targets or down:
        return Result("FAIL", "Prometheus targets", "down: " + (", ".join(down) or "no targets"),
                      "open http://localhost:9090/targets (scripts/dashboards.*) to see the error")
    return Result("PASS", "Prometheus targets", "{} targets up in {} jobs: {}".format(
        len(targets), len(jobs), ", ".join(jobs)), "")


def check_rules():
    code, out = proxy_get("prometheus:9090", "/api/v1/rules?type=alert")
    try:
        groups = json.loads(out)["data"]["groups"]
    except (ValueError, KeyError, TypeError):
        return Result("FAIL", "Alert rules loaded", "Prometheus did not answer", "kubectl -n monitoring get pods")
    names = {r["name"] for g in groups for r in g.get("rules", [])}
    missing = [a for a in KEY_ALERTS if a not in names]
    firing = sorted({r["name"] for g in groups for r in g.get("rules", []) if r.get("state") == "firing"})
    if missing:
        return Result("FAIL", "Alert rules loaded", "missing: " + ", ".join(missing),
                      "re-apply the config: kubectl apply -k k8s (a person runs it)")
    real = [name for name in firing if name != "AlwaysFiringDemoAlert"]
    detail = "{} alert rules; firing now: {}".format(len(names), ", ".join(real) or "none")
    if "AlwaysFiringDemoAlert" in firing:
        detail += " (plus AlwaysFiringDemoAlert, the always-on pipeline test: expected)"
    return Result("PASS", "Alert rules loaded", detail, "")


def check_http(name, svc, path, expect):
    code, out = proxy_get(svc, path)
    if code == 0 and expect in out:
        return Result("PASS", name, "healthy", "")
    return Result("FAIL", name, tail(out, 2) or "no answer", "kubectl -n monitoring get pods")


def part_b():
    if not shutil.which("kubectl"):
        return [Result("SKIP", "Part B (running lab)", "kubectl not found", "install the tools first (preflight)")]
    ctx = check_context()
    if ctx.status != "PASS":
        return [ctx]
    results = [ctx, check_pods()]
    if results[-1].detail == "kubectl cannot reach the cluster":
        return results
    results += [
        check_targets(),
        check_rules(),
        check_http("Alertmanager ready", "alertmanager:9093", "/-/ready", "OK"),
        check_http("Grafana health", "grafana:3000", "/api/health", '"database"'),
    ]
    return results


# ---------- output ----------

def print_results(title, results):
    print("\n" + title)
    for r in results:
        print("  {:<5} {:<55} {}".format(r.status, r.name, r.detail.splitlines()[0] if r.detail else ""))
        for extra in r.detail.splitlines()[1:]:
            print("        " + extra)
        if r.status != "PASS" and r.fix:
            print("        fix: " + r.fix)


def system_name():
    """Windows 11 still reports release "10"; its build number (22000 and up) tells them apart."""
    if WINDOWS:
        build = sys.getwindowsversion().build
        return "Windows {} (build {})".format("11" if build >= 22000 else "10", build)
    return "{} {}".format(platform.system(), platform.release())


def markdown(results, cluster):
    commit = run(["git", "rev-parse", "--short", "HEAD"], timeout=30)[1].strip() or "unknown"
    lines = [
        "# Smoke test report",
        "",
        "- Date: {} (local time)".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M")),
        "- Commit: `{}`".format(commit),
        "- System: {}, Python {}".format(system_name(), platform.python_version()),
        "- Part B (running lab): {}".format("included" if cluster else "not run (no --cluster)"),
        "",
        "| Result | Check | Detail |",
        "| --- | --- | --- |",
    ]
    for r in results:
        detail = " ".join(r.detail.split()).replace("|", "\\|")
        if r.status != "PASS" and r.fix:
            detail += " (fix: {})".format(r.fix.replace("|", "\\|"))
        lines.append("| {} | {} | {} |".format(r.status, r.name, detail))
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only smoke test of the SRE final project.")
    parser.add_argument("--cluster", action="store_true", help="also check the running Minikube lab")
    parser.add_argument("--quick", action="store_true", help="skip the promtool check (Docker image pull)")
    parser.add_argument("--report", metavar="FILE", help="also write a Markdown report to FILE")
    parser.add_argument("--no-setup", action="store_true",
                        help="do not create .venv with pytest and flake8 when they are missing")
    args = parser.parse_args(argv)

    print("SRE final project smoke test (read-only). Repository: " + ROOT)
    global DEV_PY
    DEV_PY = dev_python(setup=not args.no_setup)
    part_a = [check_python(), check_pytest(), check_flake8(), check_kustomize(), check_helm(),
              check_promtool(args.quick)]
    print_results("Part A: code and config, no cluster needed", part_a)
    results = list(part_a)
    if args.cluster:
        part_b_results = part_b()
        print_results("Part B: the running lab (read-only kubectl)", part_b_results)
        results += part_b_results

    counts = collections.Counter(r.status for r in results)
    print("\nSummary: {} PASS, {} FAIL, {} SKIP".format(counts["PASS"], counts["FAIL"], counts["SKIP"]))
    if not args.cluster:
        print("Lab running? Add --cluster to check the pods, targets and alerts too.")
    if args.report:
        path = os.path.join(ROOT, args.report) if not os.path.isabs(args.report) else args.report
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(markdown(results, args.cluster))
        print("Report written to " + os.path.abspath(path))
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
