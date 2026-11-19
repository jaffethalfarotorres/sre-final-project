# Runbook: HighLatency / StoreLatencyFromTraces

**Alerts:**
- `HighLatency` (Prometheus, warning): p95 latency of the app is above 500 ms for 2 minutes.
- `StoreLatencyFromTraces` (Grafana, warning): the same check, but measured from trace spans (spanmetrics).

**Severity:** Sev-3, or Sev-2 if it lasts long enough to threaten the latency SLO.

## 1. Diagnose
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

## 2. Mitigate
- **CPU throttling:** scale out:
  ```bash
  kubectl scale deployment/sre-metrics-app -n application --replicas=3
  ```
  Or raise the CPU limit in `k8s/application.yaml`.
- **Started right after a release:** roll back:
  ```bash
  kubectl rollout undo deployment/sre-metrics-app -n application
  ```

## 3. Verify and close
- p95 is back under 500 ms, and the latency error budget stops falling on the **SLO and Error Budget** dashboard.
