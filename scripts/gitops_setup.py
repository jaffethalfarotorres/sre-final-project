#!/usr/bin/env python3
"""
GitOps with ArgoCD (SRE Academy exercises 17 and 18), the same on macOS, Windows and Linux.

Installs ArgoCD (pinned version) if missing, registers gitops/project.yaml and gitops/application.yaml,
waits until ArgoCD has synced the Helm chart from GitHub into the gitops-staging namespace, and prints
how to open the ArgoCD UI.

    python scripts/gitops_setup.py            (use python3 on Mac/Linux)
"""

import base64
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARGOCD_VERSION = "v2.13.2"
ARGOCD_URL = f"https://raw.githubusercontent.com/argoproj/argo-cd/{ARGOCD_VERSION}/manifests/install.yaml"
APP = "sre-metrics-app-staging"


def kubectl(*args, check=True):
    result = subprocess.run(["kubectl", *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.exit(f"kubectl {' '.join(args)} failed:\n{result.stderr}")
    return result.stdout.strip()


def main():
    sys.stdout.reconfigure(line_buffering=True)  # show progress immediately, even when piped
    if subprocess.run(["kubectl", "get", "deployment", "argocd-server", "-n", "argocd"],
                      capture_output=True).returncode != 0:
        print(f"Installing ArgoCD {ARGOCD_VERSION} (about 2-3 minutes)...")
        subprocess.run(["kubectl", "create", "namespace", "argocd"], capture_output=True)
        # Server-side apply avoids the "annotations too long" error on the large ApplicationSet CRD.
        kubectl("apply", "-n", "argocd", "--server-side", "--force-conflicts", "-f", ARGOCD_URL)
    for name in ("argocd-server", "argocd-repo-server", "argocd-applicationset-controller"):
        kubectl("rollout", "status", f"deployment/{name}", "-n", "argocd", "--timeout=300s")
    kubectl("rollout", "status", "statefulset/argocd-application-controller", "-n", "argocd", "--timeout=300s")

    print("Registering the project and the Application (source: this GitHub repository)...")
    kubectl("apply", "-f", str(ROOT / "gitops" / "project.yaml"))
    kubectl("apply", "-f", str(ROOT / "gitops" / "application.yaml"))

    sync = health = ""
    for _ in range(60):
        sync = kubectl("get", "application", APP, "-n", "argocd", "-o", "jsonpath={.status.sync.status}", check=False)
        health = kubectl("get", "application", APP, "-n", "argocd", "-o", "jsonpath={.status.health.status}",
                         check=False)
        if sync == "Synced" and health == "Healthy":
            break
        time.sleep(5)
    print(f"Application {APP}: sync={sync or 'unknown'}, health={health or 'unknown'}")
    print(kubectl("get", "pods", "-n", "gitops-staging", check=False))

    password = kubectl("get", "secret", "argocd-initial-admin-secret", "-n", "argocd",
                       "-o", "jsonpath={.data.password}", check=False)
    print("\nOpen the ArgoCD UI:")
    print("  kubectl port-forward -n argocd service/argocd-server 8080:443")
    print("  https://localhost:8080  (accept the self-signed certificate warning)")
    if password:
        print(f"  user: admin   password: {base64.b64decode(password).decode()}")
    print("\nTry self-healing: kubectl scale deployment -n gitops-staging --all --replicas=5")
    print("ArgoCD sets it back to the value in Git within a few seconds.")
    return 0 if sync == "Synced" and health == "Healthy" else 1


if __name__ == "__main__":
    sys.exit(main())
