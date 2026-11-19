#!/usr/bin/env python3
"""
Policy as code with Kyverno (SRE Academy 2027, module M20), the same on macOS, Windows and Linux.

1. Installs Kyverno (pinned) if missing and applies policy/workload-baseline.yaml in Audit mode.
2. Prints the PolicyReport for the application namespace (the app should pass every rule).
3. Demonstrates enforcement: with the policy switched to Enforce, a pod that uses :latest, has no
   limits and runs as root is rejected by the Kubernetes API server (server-side dry run, nothing is created).
4. Switches the policy back to Audit.

    python scripts/policy_setup.py            (use python3 on Mac/Linux)
"""

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KYVERNO_VERSION = "v1.13.4"
KYVERNO_URL = f"https://github.com/kyverno/kyverno/releases/download/{KYVERNO_VERSION}/install.yaml"
POLICY = "sre-workload-baseline"

BAD_POD = {
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": {"name": "policy-test", "namespace": "application"},
    "spec": {"containers": [{"name": "web", "image": "nginx:latest"}]},
}


def run(*args, check=True, stdin=None):
    result = subprocess.run(list(args), capture_output=True, text=True, input=stdin)
    if check and result.returncode != 0:
        sys.exit(f"{' '.join(args)} failed:\n{result.stderr}")
    return result


def set_mode(mode):
    patch = json.dumps({"spec": {"validationFailureAction": mode}})
    run("kubectl", "patch", "clusterpolicy", POLICY, "--type=merge", "-p", patch)


def main():
    sys.stdout.reconfigure(line_buffering=True)  # show progress immediately, even when piped
    if run("kubectl", "get", "deployment", "kyverno-admission-controller", "-n", "kyverno", check=False).returncode:
        print(f"Installing Kyverno {KYVERNO_VERSION} (about 2 minutes)...")
        # Server-side apply: the Kyverno CRDs are too large for client-side apply annotations.
        run("kubectl", "apply", "--server-side", "--force-conflicts", "-f", KYVERNO_URL)
    for name in ("kyverno-admission-controller", "kyverno-background-controller", "kyverno-reports-controller"):
        run("kubectl", "rollout", "status", f"deployment/{name}", "-n", "kyverno", "--timeout=300s")

    print("Applying the SRE workload baseline policy in Audit mode...")
    for _ in range(12):  # the webhook may need a few seconds after the rollout
        if run("kubectl", "apply", "-f", str(ROOT / "policy" / "workload-baseline.yaml"), check=False).returncode == 0:
            break
        time.sleep(5)
    run("kubectl", "wait", "--for=condition=Ready", f"clusterpolicy/{POLICY}", "--timeout=120s")

    print("Waiting for the background scan to report on existing pods...")
    summary = {}
    for _ in range(24):
        reports = json.loads(run("kubectl", "get", "policyreport", "-n", "application", "-o", "json").stdout)
        summary = {"pass": 0, "fail": 0, "warn": 0, "error": 0, "skip": 0}
        for report in reports.get("items", []):
            for key in summary:
                summary[key] += report.get("summary", {}).get(key, 0)
        if summary["pass"] + summary["fail"] > 0:
            break
        time.sleep(5)
    print(f"PolicyReport for namespace application: {summary}")
    if summary["fail"]:
        print("  Some app pods violate the baseline. See: kubectl get policyreport -n application -o yaml")

    print("\nEnforcement demo: switching to Enforce and submitting a non-compliant pod (dry run)...")
    set_mode("Enforce")
    time.sleep(3)
    try:
        result = run("kubectl", "apply", "--dry-run=server", "-f", "-", check=False, stdin=json.dumps(BAD_POD))
    finally:
        set_mode("Audit")
    output = (result.stderr + result.stdout).lower()
    if result.returncode != 0 and ("blocked" in output or "denied" in output):
        print("Rejected by the admission webhook, as expected:")
        print("  " + result.stderr.strip().replace("\n", "\n  "))
        print("\nThe policy is back in Audit mode. Change validationFailureAction to Enforce in")
        print("policy/workload-baseline.yaml to block violations permanently.")
        return 0
    print("The bad pod was NOT rejected; check the Kyverno logs:")
    print(result.stdout, result.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
