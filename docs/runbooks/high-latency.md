# Runbook: HighLatency / StoreLatencyFromTraces

## Symptom

**Alerts:**
- `HighLatency` (Prometheus, warning): p95 latency of the app is above 500 ms for 2 minutes.
- `StoreLatencyFromTraces` (Grafana, warning): the same check, but measured from trace spans (spanmetrics).

## Impact

Users get slow pages: the 95th slowest request takes more than 500 ms, so about 1 request in 20 or more feels slow. Nothing fails yet, but the latency SLO (95% of `/store` requests under 500 ms) is spending its budget, and slow pages can turn into timeouts and errors.

**Severity:** Sev-3, or Sev-2 if it lasts long enough to threaten the latency SLO.

## Diagnosis
1. **Golden Signals > Latency:** the *p95 latency per span* panel shows which span got slow:
   - `GET /store` (the whole request), or
   - `store.load_catalog` (the simulated backend call).
2. **Find a slow request:**
   - In **Explore > Jaeger**, choose service `sre-metrics-app`, set Min Duration to `500ms`, and click **Run query**.
   - Open a trace. The longest bar is the slow span.
3. **Look for saturation:** in **Golden Signals > Saturation**, check whether CPU is near the 0.3-core limit or memory is near 256 MiB:
   ```bash
   kubectl top pods -n application   # needs: minikube addons enable metrics-server
   ```

## Mitigation
- **CPU throttling:** scale out:
  ```bash
  kubectl scale deployment/sre-metrics-app -n application --replicas=3
  ```
  Or raise the CPU limit in `k8s/application.yaml`.
- **Started right after a release:** roll back:
  ```bash
  kubectl rollout undo deployment/sre-metrics-app -n application
  ```

## Escalation
Declare an incident per [`../INCIDENT-RESPONSE.md`](../INCIDENT-RESPONSE.md) and name an Incident Commander if any of these is true: users can see the slowness and it is getting worse, a second team is needed (for example the owner of a slow backend), or it is still unsolved after one hour of focused work.
- **In this lab:** In this lab, the person running the exercise is the next person to call. Tell them what you saw, what you tried and what you need.
- **A real team adds:** the on-call schedule, a second responder, the engineering manager, and the owner of any slow dependency.

## Verify and close
- p95 is back under 500 ms, and the latency error budget stops falling on the **SLO and Error Budget** dashboard.
