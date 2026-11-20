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
| **Sev-1** | Complete outage, all users affected | `SyntheticProbeFailing`, or every app pod down | Incident Commander named, war room, updates every 15 minutes, postmortem required (see [triggers](#when-a-postmortem-is-required)) |
| **Sev-2** | Partial outage or clear degradation | `HighErrorRate`, `ErrorBudgetFastBurn` | On-call owns it, updates every 30 minutes, postmortem required |
| **Sev-3** | Minor, no immediate user impact | One pod down while the other serves, `HighLatency`, `ErrorBudgetSlowBurn` | Fix during working hours, ticket. A postmortem only if a [trigger](#when-a-postmortem-is-required) applies |

## Roles (Sev-1 and Sev-2)
- **Incident Commander (IC):** coordinates and decides. Does not debug and does not change the system.
- **Subject-matter experts (the ops role):** investigate and fix. They are the only people who change the system during the incident.
- **Communications lead:** posts the internal updates and the status page.
- **Scribe:** keeps the live incident document (see below). Its timestamps feed the postmortem and the TTD/TTA/TTR numbers.
- **On-call responder:** acknowledges the page and starts triage. In a small team this person is the IC until someone takes over.

Use the alert's Slack thread as the war room, so the timeline and the alert stay in one place.

## Running an incident
These rules follow the Google SRE Book chapter "Managing Incidents", in short form.
1. **Declare early.** Declare an incident if any of these is true: you need a second team to fix it, users can see the problem, or it is still unsolved after an hour of focused work. Opening an incident and closing it quickly costs little. Starting late costs a lot.
2. **One Incident Commander.** Everyone must know who it is. Say it in the thread: "I am the IC."
3. **Only the ops role changes the system.** Everyone else investigates and suggests. Two people changing things at the same time make it hard to tell what helped or hurt. Announce each change in the thread before it is made.
4. **Hand off explicitly.** When the IC changes (for example at the end of a shift), the old IC briefs the new one, then says "You are now the IC, okay?" and waits for "I have it" before leaving.
5. **Keep one live incident document.** In this lab it is the alert's Slack thread plus a timeline that the Scribe keeps: current status at the top, then a time-stamped list of what was seen, what was tried and who did it. The Google book gives this duty to the IC, so the IC checks that it stays current. A real team often uses a shared document that several people can edit at once. Keep it after the incident, because it is the base of the postmortem.

In a real team, also add an on-call schedule, a way to page a second responder, and a fixed place for the incident document. This lab does not need them.

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
1. Within 2 working days, write the postmortem from [`POSTMORTEM-TEMPLATE.md`](POSTMORTEM-TEMPLATE.md) if one is required (see below).
2. Track every action item as a GitHub issue with the `incident` label. Each one has an owner and a due date.
3. Update the runbook if a step was missing or wrong.

### When a postmortem is required
Agree on the triggers before an incident, not during it. Write a postmortem when any of these is true:
- Users saw downtime or degraded service. Every Sev-1 and Sev-2 qualifies.
- Any data was lost.
- Someone had to step in by hand, for example a rollback, a restart or moving traffic, or a rollback failed.
- It took longer than the TTR target (30 minutes) to resolve.
- A person noticed the problem before any alert fired (a monitoring failure).
- A single incident used more than 20% of the 30-day error budget. This number comes from the Workbook's example policy. The lab uses it as a starting point.

Anyone on the team can ask for a postmortem, even if none of these apply. A Sev-3 incident needs one only when a trigger applies.

### Review
- **Who reviews:** at least one engineer who did not write it, and the service owner. A real team adds a senior engineer.
- **By when:** within 5 working days of the incident, before the status changes to Reviewed. An unreviewed postmortem is the same as no postmortem.
- **What the reviewer checks:** the key data was recorded, the impact is complete, the root cause goes deep enough, each action item can be done, and the people affected were told the result.
- **Action items** need an owner and a due date, or they are not accepted. They are prioritised like other work.
