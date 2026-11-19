# Runbook: ErrorBudgetFastBurn / ErrorBudgetSlowBurn / ErrorBudgetExhausted

These alerts come from the SLO rules in [`k8s/config/prometheus/slo.yml`](../../k8s/config/prometheus/slo.yml). The definitions are in [`../SLO.md`](../SLO.md).

| Alert | Meaning | Response |
| --- | --- | --- |
| `ErrorBudgetFastBurn` (critical) | Over the last 5 minutes the app is failing more than 6× faster than the SLO allows, and over the last hour it is above 1×. | Treat as an incident now. Follow [high-error-rate.md](high-error-rate.md). |
| `ErrorBudgetSlowBurn` (warning) | Over 6 hours the budget is being spent faster than planned. | Open a ticket and fix it in the current sprint. |
| `ErrorBudgetExhausted` (critical) | The 30-day budget is gone and the SLO is breached. | Apply the error budget policy below. |

## Error budget policy (from SRE Academy topic 0)
When the budget is exhausted:
1. **Freeze feature releases** until the budget is positive again. Only reliability fixes and rollbacks ship.
2. Hold an **incident review** and write a postmortem for the events that used the budget.
3. Add the action items to the backlog with priority over features.
4. Review the SLO itself at the quarterly review. If it is always met with lots of budget left, raise it. If it is impossible to meet, discuss it with the product owner.

## Check where the budget went
- **Grafana > SLO and Error Budget:** the burn rate panel shows when the spending happened.
- **Prometheus:** this query shows which endpoint failed most:
  ```
  sum by (endpoint) (increase(http_requests_total{namespace="application",status=~"5.."}[1d]))
  ```
