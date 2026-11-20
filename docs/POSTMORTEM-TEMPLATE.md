# Postmortem: <short title>

> Blameless: describe what the system and the process allowed to happen, not who made a mistake (SRE Academy topic 6).

**Write one when** there was user-visible downtime or degradation, data loss, a rollback or other manual step (or a rollback failed), resolution took more than 30 minutes, or a person noticed before the alert did. Anyone can ask for one. The full list is in [INCIDENT-RESPONSE.md](INCIDENT-RESPONSE.md#when-a-postmortem-is-required).

| Field | Value |
| --- | --- |
| Date | YYYY-MM-DD |
| Severity | Sev-1 / Sev-2 / Sev-3 |
| Incident Commander | |
| Detected by | alert / person / user |
| Reviewer | A second engineer and the service owner, within 5 working days |
| Status | Draft / Reviewed / Action items done |
| Error budget used | x% of the 30-day availability budget (from the SLO dashboard) |

## Summary
Two or three sentences: what users experienced, for how long, and how it was fixed.

## Impact
- Users and requests affected (for example: 12% of `/store` requests failed for 18 minutes)
- SLOs affected and budget spent

## Timeline (times in UTC)
| Time | Event |
| --- | --- |
| 10:00 | Problem starts (for example: release v1.2 rolled out) |
| 10:05 | Alert `HighErrorRate` fires: **TTD = 5 min** |
| 10:08 | On-call acknowledges in Slack: **TTA = 3 min** |
| 10:15 | Cause identified with Loki logs and the Jaeger trace |
| 10:20 | `kubectl rollout undo` |
| 10:30 | Alert resolved: **TTR = 22 min** |

## Root cause analysis: 5 Whys
1. Why did users get errors? ...
2. Why did that happen? ...
3. Why ...?
4. Why ...?
5. Why ...? (root cause, usually a missing process or safeguard)

## What went well
-

## What could be improved
-

## Action items
Every action item needs one named owner and a due date. An item without both is not accepted at review.

| Action | Type (prevent / detect / mitigate) | Owner | Issue | Due |
| --- | --- | --- | --- | --- |
| | | | #  | |
