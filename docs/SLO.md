# Service Level Objectives: sre-metrics-app

This page applies SRE Academy topic 0 (SLI, SLO, SLA and error budgets) to this project. The numbers are live: Prometheus computes them from [`k8s/config/prometheus/slo.yml`](../k8s/config/prometheus/slo.yml), and Grafana shows them on the **SLO and Error Budget** dashboard.

## Definitions in one line each
- **SLI** (indicator): a measurement of what users experience. Example: the share of requests that succeed.
- **SLO** (objective): the target for an SLI over a time window. Example: 99% of requests succeed over 30 days.
- **SLA** (agreement): a promise to customers with consequences if it is missed. Always looser than the SLO.
- **Error budget**: `1 - SLO`, the amount of failure allowed. While budget is left, the team can ship features and take risks. When it is gone, reliability work comes first.
- **Burn rate**: how fast the budget is being spent. At 1×, the budget lasts exactly 30 days. At 6×, it lasts 5 days. At 14.4×, it lasts about 2 days.
- **Highest possible burn rate**: `1 / (1 - SLO)`. With a 99% SLO that is `1 / 0.01 = 100×`: every single request fails. So a burn rate is always between 0× (nothing fails) and 100× (everything fails).

## Our SLOs

| Category | SLI (how it is measured) | SLO (30 days) | Error budget |
| --- | --- | --- | --- |
| Availability | Requests without HTTP 5xx ÷ all requests (`http_requests_total`) | 99% | 1% of requests may fail |
| Latency | `/store` requests faster than 500 ms ÷ all `/store` requests (`http_request_duration_seconds`) | 95% | 5% may be slower than 500 ms |
| Synthetic availability | Blackbox exporter probes of `/` that get HTTP 2xx (`probe_success`) | Alert below 90% over 2 min | — |

**Why 99% and not 99.9%?** The demo app fails about 0.5% of `/store` calls on purpose (1 in 200, `STORE_ERROR_RATE=0.005` in [`app/app.py`](../app/app.py)), so the dashboards always have a little real data. Counting all requests (health checks and probes never fail), that is about 0.2% of the traffic. With 99% the normal failures use about one fifth of the budget, and a drill is clearly visible. With 99.9% the normal failures alone (0.2%) would already be twice the budget (0.1%), so the SLO would be broken all the time and would teach nothing. On a real service, start from what users need (for example 99.9%, about 43 minutes of downtime per month), and raise the SLO when it is consistently over-achieved.

**SLA:** none. This is a greenfield, internal service. The course recommends postponing the SLA until the SLO has been met for a few quarters.

## Alerts on the SLO
Multi-window burn-rate alerts. The long window proves the problem is real; the short window proves it is still happening, so the alert also clears soon after the fix. Both windows must agree. The thresholds are the standard ones from the Google SRE Workbook (chapter "Alerting on SLOs").

| Alert | Condition | What it means | Action |
| --- | --- | --- | --- |
| `ErrorBudgetFastBurn` (critical) | burn rate above 14.4× over 1 h **and** over 5 m, for 2 m | 2% of the 30-day budget gone in 1 hour | Page: incident now |
| `ErrorBudgetSlowBurn` (warning) | above 6× over 6 h **and** over 30 m, for 15 m | 5% of the budget gone in 6 hours | Look at it today |
| `ErrorBudgetTicket` (warning) | above 1× over 3 days **and** over 6 h, for 30 m, and more than 100,000 requests in the 3-day window | On track to spend the whole budget | Ticket for this sprint |
| `ErrorBudgetExhausted` (critical) | remaining budget below 0 **and** more than 500,000 requests in the 30-day window, for 5 m | The budget is spent | Apply the error budget policy |

The request guards keep a drill on a fresh cluster from firing the long-window alerts: there, "3 days" or "30 days" only holds a few hours of data.
- **Ticket guard: 100,000 requests** in 3 days, about 1 day of demo traffic.
- **Exhausted guard: 500,000 requests** in 30 days, about 4.5 days of demo traffic. One drill is about 3,000 failures, and normal traffic fails about 0.2%. One drill stays inside the 1% budget only when `3,000 + 0.002 × N < 0.01 × N`, so when N is above 375,000 requests. 500,000 adds some margin. A promtool test checks that 1 day of traffic plus one drill does **not** fire `ErrorBudgetExhausted`.

**Where 14.4 comes from.** A 30-day window has 720 hours. Spending 2% of the budget in 1 hour means burning `0.02 × 720 = 14.4` times faster than "exactly on budget". In the same way, 5% in 6 hours is `0.05 × 720 / 6 = 6`.

**Alertmanager inhibition.** When `ServiceDown` fires, the error, latency, probe and burn-rate alerts are muted (they are symptoms of the same outage). `ErrorBudgetExhausted` is not muted. When `ErrorBudgetFastBurn` fires, the slow burn and the ticket are muted. When `ErrorBudgetSlowBurn` fires, the ticket is muted. Muted alerts still show in the Alertmanager UI as "inhibited". See `inhibit_rules` in [`k8s/alertmanager.yaml`](../k8s/alertmanager.yaml).

**Tested without a cluster.** [`tests/rules/`](../tests/rules/) holds `promtool` unit tests: the alerts stay silent on normal traffic, the page fires at 15× and stays silent at 14×, the drill fires it, and one drill on a 1-day-old cluster does not exhaust the budget. CI runs them.

## Limits of this lab
- **Prometheus keeps 31 days** of data (`--storage.tsdb.retention.time=31d` in [`k8s/prometheus.yaml`](../k8s/prometheus.yaml)), so the 30-day window fits.
- **But the data lives on an `emptyDir` volume.** When the Prometheus pod restarts or moves, all history is lost. So the "30-day" budget really covers only the time since the last Prometheus restart. After a restart the budget starts again from full, and the request guards keep the long-window alerts quiet for a few days.
- **In production**, use persistent storage (a PersistentVolumeClaim) and long-term storage such as Thanos or Mimir, so the SLO window survives restarts and upgrades.

## Error budget policy
- **Budget above 50%:** normal feature work. Experiments and risky changes are allowed.
- **Budget between 0 and 50%:** releases need a rollback plan, and the reliability backlog gets reviewed weekly.
- **Budget spent:** feature freeze. Only fixes and rollbacks ship until the budget recovers. Write a postmortem for every incident that used budget.
- **Quarterly review:** compare the SLO with what users experienced. Adjust the SLO if it is always met with budget to spare, or never met.

## Worked example (from the course)
With a 99.9% monthly SLO, the error budget is 0.1% of 30 days, which is 43.2 minutes. After a 35-minute outage, 8.2 minutes remain, so one more small incident would freeze deployments.

The same arithmetic for this app, step by step:

1. **Traffic.** The traffic generator, the probes and the health checks send about 1.3 requests per second. That is about 3.4 million requests in 30 days.
2. **Budget.** A 99% SLO allows 1% of them to fail: about 34,000 failed requests per month.
3. **Normal day.** About 0.2% of requests fail (the 0.5% of `/store`). The burn rate is `0.2% / 1% = 0.2×`. Normal traffic uses about one fifth of the budget.
4. **The drill.** `scripts/trigger-alert` starts the `errload` pod: about 4 failing calls per second to `/error` for 12-14 minutes, about 3,000 failed requests in total.
5. **The 5-minute burn rate** jumps to about 75×: roughly 75% of the requests in those 5 minutes fail (`75% / 1%`). The maximum would be 100×.
6. **The 1-hour burn rate** grows more slowly, because the hour still holds a lot of normal traffic. After about 3-5 minutes of drill it passes 14.4×. Add the 2 minutes of `for:`, and `ErrorBudgetFastBurn` fires about 6-10 minutes after the start (sooner on a cluster younger than 1 hour). After 10 minutes of drill the 1-hour burn rate is about 35×.
7. **Cost.** 3,000 failed requests are about 9% of the monthly budget. A short drill is not cheap, which is exactly why a fast burn pages someone.

## Useful queries
```promql
sli:availability:ratio_rate30d               # availability over 30 days
slo:availability:error_budget_remaining      # 1 = full budget, 0 = spent
slo:availability:burn_rate5m                 # current speed of spending (0x to 100x)
slo:availability:burn_rate1h                 # the page fires when this AND the 5m rate are above 14.4
```
