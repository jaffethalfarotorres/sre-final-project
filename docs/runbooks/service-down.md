# Runbook: ServiceDown / SyntheticProbeFailing

**Alerts:**
- `ServiceDown` (critical): Prometheus could not scrape an app pod (`up == 0`) for 1 minute. The rule checks each pod on its own, so it fires as **critical even when only one pod is down** and the other replica still serves users.
- `SyntheticProbeFailing` (critical): the blackbox exporter, acting as a user, probes `/` of the app. Fewer than 90% of the probes in the last 2 minutes got HTTP 2xx, for 2 minutes.

**Severity:** both alerts arrive as `critical`, so always look at them now. Then decide the incident level (see [`../INCIDENT-RESPONSE.md`](../INCIDENT-RESPONSE.md)):
- **Sev-1:** `SyntheticProbeFailing` also fires, or every app pod is down. Users are affected.
- **Sev-3:** only one pod is down and the probe still passes. The other replica is serving. Fix the pod, but no Incident Commander is needed.

Note: while `ServiceDown` fires, Alertmanager mutes the error, latency, probe and burn-rate alerts of the same service (not `ErrorBudgetExhausted`) (they look like symptoms of the same outage). With one pod down this can hide a real problem on the other pod, so check the **SLO and Error Budget** dashboard too.

## 1. Acknowledge
- Acknowledge in Slack, and name an Incident Commander if this is a Sev-1 (see [`../INCIDENT-RESPONSE.md`](../INCIDENT-RESPONSE.md)).

## 2. Diagnose
Check the pods:
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
- `probe_success` is back to 1 in the **SLO and Error Budget** dashboard, and both alerts resolve.
- Write a postmortem for Sev-1 and Sev-2 incidents.
