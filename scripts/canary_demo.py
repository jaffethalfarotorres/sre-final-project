#!/usr/bin/env python3
"""
Canary release gated by an SLO (SRE Academy 2027, module M21), the same on macOS, Windows and Linux.

1. Installs Argo Rollouts (pinned) if missing and deploys progressive/rollout.yaml (4 pods + traffic).
2. Releases a GOOD version (only APP_VERSION changes): the analysis passes and the canary is promoted.
3. Releases a BAD version (50% of /store calls fail): the analysis fails at 25% traffic and Argo Rollouts
   aborts and returns every pod to the stable version on its own.
4. Restores the stable spec so the Rollout is Healthy again.

    python scripts/canary_demo.py            (use python3 on Mac/Linux; takes about 10 minutes)
"""

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROLLOUTS_VERSION = "v1.8.0"
ROLLOUTS_URL = f"https://github.com/argoproj/argo-rollouts/releases/download/{ROLLOUTS_VERSION}/install.yaml"
NS = "progressive"


def kubectl(*args, check=True):
    result = subprocess.run(["kubectl", *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.exit(f"kubectl {' '.join(args)} failed:\n{result.stderr}")
    return result.stdout.strip()


def rollout():
    return json.loads(kubectl("get", "rollout", "sre-metrics-app", "-n", NS, "-o", "json"))


def set_env(version, error_rate):
    # A JSON patch that replaces only the env list. (A merge patch on a custom resource would replace the
    # whole containers list and drop the image: CRDs do not support strategic merge.)
    patch = [{"op": "replace", "path": "/spec/template/spec/containers/0/env",
              "value": [{"name": "APP_VERSION", "value": version},
                        {"name": "STORE_ERROR_RATE", "value": error_rate}]}]
    kubectl("patch", "rollout", "sre-metrics-app", "-n", NS, "--type=json", "-p", json.dumps(patch))


def wait_for(phases, timeout=900):
    """Wait until the Rollout reaches one of the given phases, printing progress."""
    started, last = time.time(), ""
    while time.time() - started < timeout:
        status = rollout().get("status", {})
        phase = status.get("phase", "")
        line = f"  phase={phase:<11} step={status.get('currentStepIndex', '-')} " \
               f"canary-weight={status.get('canary', {}).get('weights', {}).get('canary', {}).get('weight', '-')}" \
               f" message={status.get('message', '')}"
        if line != last:
            print(line)
            last = line
        if phase in phases:
            return phase
        time.sleep(5)
    sys.exit(f"Timed out waiting for {phases}")


def last_analysis():
    runs = json.loads(kubectl("get", "analysisrun", "-n", NS, "-o", "json"))["items"]
    if not runs:
        return "no AnalysisRun"
    run = sorted(runs, key=lambda r: r["metadata"]["creationTimestamp"])[-1]
    measurements = run.get("status", {}).get("metricResults", [{}])[0].get("measurements", [])
    values = [m.get("value", "?") for m in measurements]
    return f"{run['metadata']['name']}: {run.get('status', {}).get('phase')} (success rate samples: {values})"


def main():
    sys.stdout.reconfigure(line_buffering=True)  # show progress immediately, even when piped
    if subprocess.run(["kubectl", "get", "deployment", "argo-rollouts", "-n", "argo-rollouts"],
                      capture_output=True).returncode:
        print(f"Installing Argo Rollouts {ROLLOUTS_VERSION}...")
        subprocess.run(["kubectl", "create", "namespace", "argo-rollouts"], capture_output=True)
        kubectl("apply", "-n", "argo-rollouts", "-f", ROLLOUTS_URL)
    kubectl("rollout", "status", "deployment/argo-rollouts", "-n", "argo-rollouts", "--timeout=300s")

    print("Deploying the stable version (4 pods) with steady traffic...")
    kubectl("apply", "-f", str(ROOT / "progressive" / "rollout.yaml"))
    set_env("1.0.0", "0.05")
    wait_for({"Healthy"})

    print("\n1) Releasing a GOOD version 1.1.0 (same 5% background error rate)...")
    set_env("1.1.0", "0.05")
    good = wait_for({"Healthy", "Degraded"})
    print(f"   Result: {good}. {last_analysis()}")

    print("\n2) Releasing a BAD version 1.2.0 (half of the /store calls fail)...")
    set_env("1.2.0", "0.5")
    bad = wait_for({"Degraded", "Healthy"})
    status = rollout().get("status", {})
    print(f"   Result: {bad}, aborted={status.get('abort', False)}. {last_analysis()}")

    print("\n3) Restoring the stable spec (1.1.0) so the Rollout is Healthy again...")
    set_env("1.1.0", "0.05")
    wait_for({"Healthy"})

    ok = good == "Healthy" and bad == "Degraded" and status.get("abort")
    print("\nCanary gate worked: good release promoted, bad release stopped at 25% and rolled back."
          if ok else "\nUnexpected result; inspect: kubectl get rollout,analysisrun -n progressive")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
