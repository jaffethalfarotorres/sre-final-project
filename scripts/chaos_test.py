#!/usr/bin/env python3
"""
Chaos engineering test (SRE Academy exercise 19), the same on macOS, Windows and Linux.

Installs Argo Workflows and LitmusChaos if they are missing, then runs chaos/pod-delete-workflow.yaml:
LitmusChaos kills half of the sre-metrics-app pods every 10 seconds for 30 seconds while an HTTP probe
checks that the app keeps answering. Prints the verdict and how fast Kubernetes recovered.

    python scripts/chaos_test.py            (use python3 on Mac/Linux)
"""

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARGO_VERSION = "v3.5.11"
LITMUS_VERSION = "3.0.0"
ARGO_URL = f"https://github.com/argoproj/argo-workflows/releases/download/{ARGO_VERSION}/install.yaml"
LITMUS_URL = f"https://litmuschaos.github.io/litmus/litmus-operator-v{LITMUS_VERSION}.yaml"


def kubectl(*args, check=True, capture=True):
    """Run kubectl and return its standard output as text."""
    result = subprocess.run(["kubectl", *args], capture_output=capture, text=True)
    if check and result.returncode != 0:
        sys.exit(f"kubectl {' '.join(args)} failed:\n{result.stderr}")
    return result.stdout if capture else ""


def exists(kind, name, namespace=None):
    args = ["get", kind, name] + (["-n", namespace] if namespace else [])
    return subprocess.run(["kubectl", *args], capture_output=True).returncode == 0


def ensure_namespace(name):
    if not exists("namespace", name):
        kubectl("create", "namespace", name)


def install_tools():
    if not exists("deployment", "workflow-controller", "argo"):
        print(f"Installing Argo Workflows {ARGO_VERSION}...")
        ensure_namespace("argo")
        kubectl("apply", "-n", "argo", "-f", ARGO_URL)
    if not exists("deployment", "chaos-operator-ce", "litmus"):
        print(f"Installing the LitmusChaos operator {LITMUS_VERSION}...")
        ensure_namespace("litmus")
        kubectl("apply", "-f", LITMUS_URL)
    print("Waiting for Argo Workflows and LitmusChaos to be ready...")
    kubectl("rollout", "status", "deployment/workflow-controller", "-n", "argo", "--timeout=300s")
    kubectl("rollout", "status", "deployment/chaos-operator-ce", "-n", "litmus", "--timeout=300s")
    kubectl("apply", "-f", str(ROOT / "chaos" / "rbac.yaml"))


def app_pods():
    data = json.loads(kubectl("get", "pods", "-n", "application", "-l", "app=sre-metrics-app", "-o", "json"))
    return {pod["metadata"]["name"] for pod in data["items"]}


def main():
    sys.stdout.reconfigure(line_buffering=True)  # show progress immediately, even when piped
    install_tools()
    # Remove a leftover engine from an interrupted run so the experiment starts clean.
    kubectl("delete", "chaosengine", "sre-metrics-app-pod-delete", "-n", "litmus", "--ignore-not-found")

    pods_before = app_pods()
    print(f"App pods before the experiment: {', '.join(sorted(pods_before))}")
    created = kubectl("create", "-f", str(ROOT / "chaos" / "pod-delete-workflow.yaml"))
    workflow = created.split()[0].split("/")[-1]
    print(f"Started Argo Workflow {workflow}. Killing pods for 30 seconds; this takes about 2-3 minutes...")

    started = time.time()
    phase = ""
    while time.time() - started < 600:
        phase = kubectl("get", "workflow", workflow, "-n", "litmus", "-o", "jsonpath={.status.phase}", check=False)
        if phase in ("Succeeded", "Failed", "Error"):
            break
        time.sleep(5)

    result = json.loads(kubectl("get", "chaosresult", "sre-metrics-app-pod-delete-pod-delete", "-n", "litmus",
                                "-o", "json", check=False) or "{}")
    status = result.get("status", {})
    verdict = status.get("experimentStatus", {}).get("verdict", "unknown")
    probes = status.get("probeStatuses", [])

    # Recovery: how long until every app pod is Ready again after the experiment.
    recovery_start = time.time()
    kubectl("rollout", "status", "deployment/sre-metrics-app", "-n", "application", "--timeout=180s")
    recovery = time.time() - recovery_start
    pods_after = app_pods()

    print()
    print(f"Workflow phase        : {phase}")
    print(f"Chaos verdict         : {verdict}")
    for probe in probes:
        print(f"Probe {probe.get('name')}: {probe.get('status', {})}")
    print(f"Pods replaced         : {len(pods_before - pods_after)} of {len(pods_before)}")
    print(f"Time to full recovery : {recovery:.0f} s after the experiment ended")
    print(f"Total duration        : {time.time() - started:.0f} s")
    if verdict == "Pass" and phase == "Succeeded":
        print("\nHypothesis confirmed: the app kept answering while its pods were being killed.")
        return 0
    print("\nHypothesis rejected or experiment incomplete. Inspect with:")
    print(f"  kubectl get workflow {workflow} -n litmus -o yaml")
    print("  kubectl describe chaosresult sre-metrics-app-pod-delete-pod-delete -n litmus")
    return 1


if __name__ == "__main__":
    sys.exit(main())
