# Runbook: HighErrorRate / ErrorLogBurst

**Alert:** `HighErrorRate` (Prometheus, critical): more than 5% of requests to `sre-metrics-app` returned HTTP 5xx for 2 minutes. `ErrorLogBurst` (Grafana, warning): more than 100 ERROR log lines in 5 minutes in Loki.
**Severity:** Sev-2. Users see failures on part of their requests. Escalate to Sev-1 if the error ratio stays above 50% or `ServiceDown` also fires.

## 1. Acknowledge (target: within 5 minutes)
- Reply in the alert's Slack thread: "Ack, investigating". That stops the clock for Time To Acknowledge (TTA).
- Open the **Golden Signals** dashboard in Grafana. The **Errors** row shows which signal is failing.

## 2. Diagnose
1. **Which endpoint fails?** In Grafana's **SRE Metrics Demo** dashboard, the *Error Rate* panel splits errors by endpoint.
   - Errors only on `/error`: this is the test endpoint. Someone is running `scripts/trigger-alert`. Confirm in the team channel, then stop the load: `kubectl delete pod errload -n application`.
   - Errors on `/store`: this is a real problem. Continue below.
2. **What do the logs say?** In Grafana, go to **Explore > Loki** and run:
   ```
   {service_name="sre-metrics-app"} | severity_text="ERROR"
   ```
   Click a log line, then **TraceID**, to open the failing request in Jaeger and see which span failed.
3. **Did something change?** Run:
   ```bash
   kubectl rollout history deployment/sre-metrics-app -n application
   ```
   A recent revision is the most likely cause.
4. **Collect evidence automatically.** Run from the repo root with the lab virtual environment active (`source ~/.venvs/sre-lab/bin/activate`, see Lab 05 M10 step 1), so Ansible finds the `kubernetes` library.
   ```bash
   ansible-playbook -i ansible/inventory.ini ansible/runbooks/collect-diagnostics.yml -e ansible_python_interpreter="$(command -v python3)"
   ```
   The report is saved in `reports/`.

## 3. Mitigate
- **A bad release:** roll back first and investigate later:
  ```bash
  kubectl rollout undo deployment/sre-metrics-app -n application
  ```
- **Pods in a bad state:** run the restart runbook. Run from the repo root with the lab virtual environment active (`source ~/.venvs/sre-lab/bin/activate`, see Lab 05 M10 step 1), so Ansible finds the `kubernetes` library.
  ```bash
  ansible-playbook -i ansible/inventory.ini ansible/runbooks/restart-app.yml -e ansible_python_interpreter="$(command -v python3)"
  ```

## 4. Verify and close
- The error ratio is back under 5% and the alert shows **Resolved** in Slack and email.
- Check the **SLO and Error Budget** dashboard and note how much budget was spent.
- Sev-1 and Sev-2 incidents need a postmortem: copy [`../POSTMORTEM-TEMPLATE.md`](../POSTMORTEM-TEMPLATE.md).
