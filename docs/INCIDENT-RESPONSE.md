# Incident response

How this project detects, handles and learns from incidents (SRE Academy topics 1 and 6).

## Lifecycle and the tools for each step

| Step | What happens | In this project |
| --- | --- | --- |
| **Detection** | A monitor notices users are affected | Prometheus rules (`HighErrorRate`, `ServiceDown`, `HighLatency`, SLO burn-rate alerts), Grafana rules (traces and logs), blackbox synthetic probes |
| **Notification** | The right people are told | Alertmanager routes by severity to Slack and email (critical: 10 s group wait, 1 h repeat) |
| **Triage** | Decide severity and owner | Severity table below; every alert links to its runbook (`runbook_url`) |
| **Response & mitigation** | Stop the user impact first | Runbooks in [`runbooks/`](runbooks/); Ansible runbooks `collect-diagnostics.yml` and `restart-app.yml`; `kubectl rollout undo` |
| **Resolution** | Fix the cause, confirm recovery | Alerts send a *Resolved* message (`send_resolved: true`) |
| **Postmortem** | Learn without blame | [`POSTMORTEM-TEMPLATE.md`](POSTMORTEM-TEMPLATE.md) |

## Severity levels

| Level | Definition | Example in this project | Response |
| --- | --- | --- | --- |
| **Sev-1** | Complete outage, all users affected | `SyntheticProbeFailing`, or every app pod down | Incident Commander named, war room, updates every 15 minutes, postmortem required |
| **Sev-2** | Partial outage or clear degradation | `HighErrorRate`, `ErrorBudgetFastBurn` | On-call owns it, updates every 30 minutes, postmortem required |
| **Sev-3** | Minor, no immediate user impact | One pod down while the other serves, `HighLatency`, `ErrorBudgetSlowBurn` | Fix during working hours, ticket |

## Roles (Sev-1 and Sev-2)
- **Incident Commander:** coordinates and decides. Does not debug.
- **Subject-matter experts:** investigate and fix.
- **Communications lead:** posts the internal updates and the status page.
- **Scribe:** keeps the timeline. Its timestamps feed the postmortem and the TTD/TTA/TTR numbers.
- **On-call responder:** acknowledges the page and starts triage.

Use the alert's Slack thread as the war room, so the timeline and the alert stay in one place.

## Measuring the response: TTD, TTA, TTR
These measure the team, not the product.

```
issue starts ──TTD──> alert fires ──TTA──> someone acknowledges ──TTR──> users recovered
```

| Metric | How it is measured here | Target | How this project lowers it |
| --- | --- | --- | --- |
| **TTD** (time to detect) | Alertmanager `startsAt` (alert firing, after `for:`) minus the time the problem started | < 3 min | Short `for:` windows (1-2 min), 10 s scrape interval, synthetic probes, burn-rate alerts |
| **TTA** (time to acknowledge) | Acknowledgement minus the alert's `startsAt` | < 5 min | Severity routing; critical alerts go to Slack and email at once |
| **TTR** (time to resolve) | Alerts resolved minus the time the problem started | < 30 min | Runbook links on every alert, Ansible runbooks, one-command rollback, rolling updates |

Worked example: the issue starts at 10:00, the alert fires at 10:05, it is acknowledged at 10:08 and resolved at 10:30. That gives TTD = 5 min, TTA = 3 min and TTR = 30 min. (The 2026 topic-1 material measured TTR from acknowledgement, which gives 22 min. This course measures TTR from problem start, as the incident form does.)

Measured on this project during testing:
- **TTD for a 5xx burst:** `HighErrorRate` fired about 140 s after the burst started (`scripts/trigger-alert`).
- **TTR for a bad release:** `scripts/rollout_demo.py` prints the time from the bad release to recovery.

## After the incident
1. Within 2 working days, write the postmortem from [`POSTMORTEM-TEMPLATE.md`](POSTMORTEM-TEMPLATE.md).
2. Track every action item as a GitHub issue with the `incident` label.
3. Update the runbook if a step was missing or wrong.
