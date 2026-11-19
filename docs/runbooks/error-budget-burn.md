# Runbook: ErrorBudgetFastBurn / ErrorBudgetSlowBurn / ErrorBudgetTicket / ErrorBudgetExhausted

These alerts come from the SLO rules in [`k8s/config/prometheus/slo.yml`](../../k8s/config/prometheus/slo.yml). The definitions are in [`../SLO.md`](../SLO.md). The SLO is 99% availability over 30 days, so the error budget is 1% of requests. A burn rate of 1x spends the budget in exactly 30 days.

Each alert needs two windows to agree: the long window proves the problem is real, the short window proves it is still happening.

| Alert | Rule (from slo.yml) | Meaning | Response |
| --- | --- | --- | --- |
| `ErrorBudgetFastBurn` (critical) | burn rate above 14.4x over 1 h **and** over 5 m, for 2m | 2% of the 30-day budget is gone in 1 hour. | **Page now.** Treat it as an incident. Follow [high-error-rate.md](high-error-rate.md). |
| `ErrorBudgetSlowBurn` (warning) | burn rate above 6x over 6 h **and** over 30 m, for 15m | 5% of the budget is gone in 6 hours. | **Act today.** Find the cause during working hours today. |
| `ErrorBudgetTicket` (warning) | burn rate above 1x over 3 d **and** over 6 h, for 30m, and more than 100,000 requests in 3 days | On track to spend the whole budget before the 30 days end. | **Open a ticket** and fix it in the current sprint. |
| `ErrorBudgetExhausted` (critical) | remaining 30-day budget below 0, for 5m, and more than 500,000 requests in 30 days | The 30-day budget is gone and the SLO is breached. | Apply the error budget policy below. |

When `ErrorBudgetFastBurn` fires, Alertmanager mutes the slow burn and the ticket (same problem). When `ErrorBudgetSlowBurn` fires, it mutes the ticket. The request guards keep the long-window alerts quiet on a young cluster: there, "3 days" or "30 days" only holds a few hours of data, so one drill would look like a month of failures. See [`../SLO.md`](../SLO.md) for the numbers.

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
