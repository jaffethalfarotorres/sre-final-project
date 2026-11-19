# Runbook: ServiceDown / ReplicaDown / SyntheticProbeFailing

**Alerts:**
- `ServiceDown` (critical, pages): **no** app pod can be scraped for 1 minute. Either every replica answers `up == 0`, or Prometheus finds no app pod at all (`absent()`, for example the Deployment is scaled to 0). Users get nothing.
- `ReplicaDown` (warning: Slack, email and phone push, but no AWX job and no Incident Commander): some app pods are down, but at least one still answers, for 5 minutes. The other replica serves users. The 5 minutes let a normal restart or rolling update finish without noise.
- `SyntheticProbeFailing` (critical, pages): the blackbox exporter, acting as a user, probes `/` of the app. Fewer than 90% of the probes in the last 2 minutes got HTTP 2xx, for 2 minutes.

**Severity.** Decide the incident level (see [`../INCIDENT-RESPONSE.md`](../INCIDENT-RESPONSE.md)):
- **Sev-1:** `ServiceDown` or `SyntheticProbeFailing` fires. Users are affected. Name an Incident Commander.
- **Sev-3:** only `ReplicaDown` fires and the probe still passes. The other replica is serving. Fix the pod today. No Incident Commander is needed.

Note: while `ServiceDown` fires, Alertmanager mutes the error, latency, probe and burn-rate alerts of the same service (not `ErrorBudgetExhausted`), because they are symptoms of the same outage. `ReplicaDown` mutes nothing, so a real problem on the pod that still serves still pages (for example `HighErrorRate`).

## 1. Acknowledge
- Acknowledge in Slack (or the phone push), and name an Incident Commander if this is a Sev-1 (see [`../INCIDENT-RESPONSE.md`](../INCIDENT-RESPONSE.md)).

## 2. Diagnose
Check the pods. Count how many app pods are `Running` and `READY 1/1`: none means `ServiceDown`, some means `ReplicaDown`. No pod at all? Check the replica count first (`kubectl get deployment sre-metrics-app -n application`); a scale to 0 is fixed with `kubectl scale deployment sre-metrics-app -n application --replicas=2`.
```bash
kubectl get pods -n application -o wide
kubectl describe deployment sre-metrics-app -n application
kubectl get events -n application --sort-by=.lastTimestamp | tail -20
```

| What you see | Likely cause | Action |
| --- | --- | --- |
| `ImagePullBackOff` / `ErrImagePull` | Bad image tag in the last release | `kubectl rollout undo deployment/sre-metrics-app -n application` |
| `CrashLoopBackOff` | App fails at startup | `kubectl logs deployment/sre-metrics-app -n application --previous` |
| `OOMKilled` in the describe output | Memory limit too low | Raise the limit in `k8s/application.yaml`, then re-apply |
| `Pending` | Node out of CPU or memory | `kubectl describe pod ...` (see Events); free resources or grow Minikube |
| Pods `Running` but probe failing | Service selector or network problem | `kubectl get endpoints sre-metrics-app -n application` |

## 3. Mitigate
- Roll back or restart. Run from the repo root with the lab virtual environment active (`source ~/.venvs/sre-lab/bin/activate`, see Lab 05 M10 step 1), so Ansible finds the `kubernetes` library:
  ```bash
  ansible-playbook -i ansible/inventory.ini ansible/runbooks/restart-app.yml -e ansible_python_interpreter="$(command -v python3)"
  ```
- Confirm the app answers:
  ```bash
  kubectl get --raw /api/v1/namespaces/application/services/sre-metrics-app:5000/proxy/
  ```

## 4. Verify and close
- All app pods are `Running` and `READY 1/1`, and `sum(up{job="kubernetes-pods", namespace="application", app="sre-metrics-app"})` in Prometheus equals the number of replicas (2).
- `probe_success` is back to 1 in the **SLO and Error Budget** dashboard, and the alerts resolve.
- Write a postmortem for Sev-1 and Sev-2 incidents.
