# Runbook: ServiceDown / SyntheticProbeFailing

**Alerts:**
- `ServiceDown` (critical): Prometheus could not scrape an app pod for 1 minute.
- `SyntheticProbeFailing` (critical): the blackbox exporter, acting as a user, could not get HTTP 200 from the app.

**Severity:** Sev-1 when the synthetic probe fails, because users are affected. Sev-3 when only one pod is down and the probe still passes, because the other replica is serving.

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
- Roll back or restart:
  ```bash
  ansible-playbook -i ansible/inventory.ini ansible/runbooks/restart-app.yml
  ```
- Confirm the app answers:
  ```bash
  kubectl get --raw /api/v1/namespaces/application/services/sre-metrics-app:5000/proxy/
  ```

## 4. Verify and close
- `probe_success` is back to 1 in the **SLO and Error Budget** dashboard, and both alerts resolve.
- Write a postmortem for Sev-1 and Sev-2 incidents.
