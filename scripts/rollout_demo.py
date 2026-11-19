#!/usr/bin/env python3
"""
Rolling update and rollback demo (SRE Academy exercise 18), the same on macOS, Windows and Linux.

1. Releases a broken version of sre-metrics-app (an image tag that does not exist).
2. Shows that the rolling update strategy (maxUnavailable: 0) keeps the old pods serving: the app still
   answers HTTP 200 while the new pod is stuck in ImagePullBackOff.
3. Rolls back with `kubectl rollout undo` and measures the time to recover (MTTR of a bad release).

    python scripts/rollout_demo.py            (use python3 on Mac/Linux)
"""

import subprocess
import sys
import time

NAMESPACE = "application"
DEPLOYMENT = "deployment/sre-metrics-app"
HEALTH_URL = f"/api/v1/namespaces/{NAMESPACE}/services/sre-metrics-app:5000/proxy/"


def kubectl(*args, check=True):
    result = subprocess.run(["kubectl", *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.exit(f"kubectl {' '.join(args)} failed:\n{result.stderr}")
    return result.stdout.strip()


def app_answers():
    """True when the app Service answers through the Kubernetes API proxy."""
    return subprocess.run(["kubectl", "get", "--raw", HEALTH_URL], capture_output=True).returncode == 0


def pods():
    return kubectl("get", "pods", "-n", NAMESPACE, "-l", "app=sre-metrics-app", "--no-headers",
                   "-o", "custom-columns=NAME:.metadata.name,STATUS:.status.phase,"
                   "REASON:.status.containerStatuses[0].state.waiting.reason")


def main():
    kubectl("rollout", "status", DEPLOYMENT, "-n", NAMESPACE, "--timeout=120s")
    print("1) Current release is healthy:")
    print(pods())

    print("\n2) Releasing a broken version (image tag sre-metrics-app:broken does not exist)...")
    kubectl("set", "image", DEPLOYMENT, "app=sre-metrics-app:broken", "-n", NAMESPACE)
    kubectl("annotate", DEPLOYMENT, "-n", NAMESPACE, "--overwrite",
            "kubernetes.io/change-cause=demo: release broken image")
    released = time.time()

    ok, checks = 0, 0
    for _ in range(10):
        checks += 1
        ok += app_answers()
        time.sleep(2)
    print(pods())
    print(f"   During the bad rollout the app answered {ok}/{checks} health checks: the old pods kept serving.")

    stuck = subprocess.run(["kubectl", "rollout", "status", DEPLOYMENT, "-n", NAMESPACE, "--timeout=10s"],
                           capture_output=True, text=True)
    if stuck.returncode != 0:
        print("   The rollout is stuck, as expected (the new pod cannot pull its image).")

    print("\n3) Rolling back with: kubectl rollout undo deployment/sre-metrics-app -n application")
    undo_started = time.time()
    kubectl("rollout", "undo", DEPLOYMENT, "-n", NAMESPACE)
    kubectl("rollout", "status", DEPLOYMENT, "-n", NAMESPACE, "--timeout=180s")
    # Wait until the stuck pod of the broken release has been removed, then show the final state.
    replicas = int(kubectl("get", DEPLOYMENT, "-n", NAMESPACE, "-o", "jsonpath={.spec.replicas}"))
    for _ in range(30):
        if len(pods().splitlines()) <= replicas:
            break
        time.sleep(2)
    print(pods())
    print("\nRollout history:")
    print(kubectl("rollout", "history", DEPLOYMENT, "-n", NAMESPACE))
    print(f"\nRollback took {time.time() - undo_started:.0f} s; bad release to recovery: "
          f"{time.time() - released:.0f} s, with {ok}/{checks} successful health checks during the incident.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
