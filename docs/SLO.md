# Service Level Objectives: sre-metrics-app

This page applies SRE Academy topic 0 (SLI, SLO, SLA and error budgets) to this project. The numbers are live: Prometheus computes them from [`k8s/config/prometheus/slo.yml`](../k8s/config/prometheus/slo.yml), and Grafana shows them on the **SLO and Error Budget** dashboard.

## Definitions in one line each
- **SLI** (indicator): a measurement of what users experience. Example: the share of requests that succeed.
- **SLO** (objective): the target for an SLI over a time window. Example: 90% of requests succeed over 30 days.
- **SLA** (agreement): a promise to customers with consequences if it is missed. Always looser than the SLO.
- **Error budget**: `1 - SLO`, the amount of failure allowed. While budget is left, the team can ship features and take risks. When it is gone, reliability work comes first.
- **Burn rate**: how fast the budget is being spent. At 1×, the budget lasts exactly 30 days. At 6×, it lasts 5 days.

## Our SLOs

| Category | SLI (how it is measured) | SLO (30 days) | Error budget |
| --- | --- | --- | --- |
| Availability | Requests without HTTP 5xx ÷ all requests (`http_requests_total`) | 90% | 10% of requests may fail |
| Latency | `/store` requests faster than 500 ms ÷ all `/store` requests (`http_request_duration_seconds`) | 95% | 5% may be slower than 500 ms |
| Synthetic availability | Blackbox exporter probes of `/` that get HTTP 2xx (`probe_success`) | Alert below 90% over 2 min | — |

**Why 90% and not 99.9%?** The demo app fails about 5% of `/store` calls on purpose, so the alerts and dashboards always have real data. A 99.9% target would be breached all the time and would teach nothing. On a real service, start from what users need (for example 99.9%, about 43 minutes of downtime per month), and raise the SLO when it is consistently over-achieved.

**SLA:** none. This is a greenfield, internal service. The course recommends postponing the SLA until the SLO has been met for a few quarters.

## Alerts on the SLO
Multi-window burn-rate alerts. The long window proves the problem is real; the short window proves it is still happening.

| Alert | Condition | Action |
| --- | --- | --- |
| `ErrorBudgetFastBurn` | burn rate above 6× over 5 m **and** above 1× over 1 h | Page: incident now |
| `ErrorBudgetSlowBurn` | above 1× over 6 h **and** over 1 h, for 15 m | Ticket for this sprint |
| `ErrorBudgetExhausted` | remaining budget below 0 for 5 m | Apply the error budget policy |

## Error budget policy
- **Budget above 50%:** normal feature work. Experiments and risky changes are allowed.
- **Budget between 0 and 50%:** releases need a rollback plan, and the reliability backlog gets reviewed weekly.
- **Budget spent:** feature freeze. Only fixes and rollbacks ship until the budget recovers. Write a postmortem for every incident that used budget.
- **Quarterly review:** compare the SLO with what users experienced. Adjust the SLO if it is always met with budget to spare, or never met.

## Worked example (from the course)
With a 99.9% monthly SLO, the error budget is 0.1% of 30 days, which is 43.2 minutes. After a 35-minute outage, 8.2 minutes remain, so one more small incident would freeze deployments.

The same arithmetic for this app: at 1 request every 2 seconds, about 1.3 million requests per month, and a 10% budget allows about 130,000 failed requests. `scripts/trigger-alert` sends about 1,000 failing requests, which is less than 1% of the monthly budget but more than 6× the allowed rate for 5 minutes. That is exactly the situation the fast-burn alert is built for.

## Useful queries
```promql
sli:availability:ratio_rate30d               # availability over 30 days
slo:availability:error_budget_remaining      # 1 = full budget, 0 = spent
slo:availability:burn_rate5m                 # current speed of spending
```
