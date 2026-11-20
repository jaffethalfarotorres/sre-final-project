# Runbook: AlertmanagerDown

## Symptom

**Alert:** `AlertmanagerDown` (critical): Prometheus has not been able to scrape Alertmanager for 2 minutes. Either the Alertmanager pod does not answer, or Prometheus finds no Alertmanager target at all.

This alert is special. Alertmanager is the component that delivers every other alert, so if it is down, **this alert cannot reach anyone either**. You will see it only in Prometheus (`Alerts` page, http://localhost:9090/alerts), or because the always-on `AlwaysFiringDemoAlert` stopped showing up in Alertmanager. Real teams add an outside "dead man's switch" for this reason: a service that complains when the always-firing alert stops arriving.

## Impact

Nobody is paged for anything while Alertmanager is down: a real outage of the shop would pass in silence. Treat it as a **Sev-2**: users are not affected yet, but the safety net is gone (see [`../INCIDENT-RESPONSE.md`](../INCIDENT-RESPONSE.md)).

## Diagnosis

### Check the pod
```bash
kubectl get pods -n monitoring -l app=alertmanager
kubectl describe pod -n monitoring -l app=alertmanager
kubectl logs -n monitoring deployment/alertmanager --tail=30
```

| What you see | Likely cause | Action |
| --- | --- | --- |
| `CrashLoopBackOff` and a config error in the logs | A bad change to `k8s/alertmanager.yaml` or the Secret | Fix the file, then re-apply (see Mitigation) |
| `CreateContainerConfigError` | The Secret `alertmanager-secret` is missing | `python scripts/lab_up.py` creates it from the example file |
| `Pending` or `OOMKilled` | Not enough memory on the node | `kubectl describe pod ...` (see Events); free resources |
| Pod `Running` but the target is down | Service or network problem | `kubectl get endpoints alertmanager -n monitoring` |

### Check what Prometheus sees
In Prometheus, open **Status > Targets** and find the `alertmanager` job, or run the query `up{job="alertmanager"}` (1 is up, 0 is down).

## Mitigation

Restart or re-apply Alertmanager. The lab's own command re-applies everything and waits until it is ready:
```bash
python scripts/lab_up.py
```
Then confirm it answers (this prints `OK`):
```bash
kubectl get --raw /api/v1/namespaces/monitoring/services/alertmanager:9093/proxy/-/ready
```

## Escalation

- **In this lab:** the person running the exercise is the next person to call. Tell them what you saw, what you tried and what you need.
- **A real team adds:** the on-call schedule, the owner of the alerting platform, and a second, independent notification path (an outside dead man's switch) so a silent Alertmanager is noticed in minutes.

## Verify and close

- `up{job="alertmanager"}` is `1` in Prometheus and `AlertmanagerDown` is no longer active.
- The always-on `AlwaysFiringDemoAlert` is visible again in Alertmanager (http://localhost:9093).
- If an incident was declared, write a short postmortem (see [`../POSTMORTEM-TEMPLATE.md`](../POSTMORTEM-TEMPLATE.md)): what would have been missed during the gap?
