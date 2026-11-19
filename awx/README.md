# AWX add-on (SRE Academy exercise 13)

Runs the Ansible runbooks from `ansible/runbooks/` in AWX, and lets Alertmanager start them when an incident happens.

```bash
python3 scripts/awx_setup.py      # about 10-15 minutes the first time; needs ~2.5 GB free in Minikube
```

What the script sets up:

| Piece | Details |
| --- | --- |
| AWX Operator 2.19.1 + AWX instance | [`kustomization.yaml`](kustomization.yaml), [`awx.yaml`](awx.yaml) (laptop-sized resources) |
| Project | This GitHub repository, branch `main` (AWX syncs the runbooks from GitHub) |
| Credential | "OpenShift or Kubernetes API Bearer Token" for the `awx-runbooks` ServiceAccount ([`rbac.yaml`](rbac.yaml)): it can read the app namespace and patch only the app Deployment; it cannot delete pods |
| Job template `collect-diagnostics` | Read-only. Launched automatically by Alertmanager for every critical alert (receiver `awx-collect-diagnostics` in [`k8s/alertmanager.yaml`](../k8s/alertmanager.yaml)) |
| Job template `restart-app` | Remediation. Launched **only by a person** after reading the diagnostics |
| Token | An AWX API token in the `awx-webhook-token` Secret, mounted into Alertmanager |

Verified on 2026-11-19: `HighErrorRate` fired, and 14 seconds later Alertmanager launched `collect-diagnostics`, which succeeded.

**Real-world lesson in [`kustomization.yaml`](kustomization.yaml):** the operator's manifests reference `gcr.io/kubebuilder/kube-rbac-proxy:v0.15.0`, an image that was removed from that registry. The pods stayed in `ImagePullBackOff` until the image was redirected to `quay.io/brancz/kube-rbac-proxy:v0.15.0`. Pinning a version does not protect you if the registry deletes it; mirror what you depend on.

Open the UI:
```bash
kubectl port-forward -n awx service/awx-service 8052:80        # then http://localhost:8052, user admin
kubectl get secret awx-admin-password -n awx -o jsonpath='{.data.password}' | base64 --decode; echo
```

Remove it when you are done (it is the heaviest add-on):
```bash
kubectl delete awx awx -n awx
kubectl delete namespace awx
kubectl delete role,rolebinding awx-runbooks -n application
```
