# Postmortem: alert drill with AI triage, and a stale app image found along the way

> Blameless: this describes what the system and the process allowed to happen, not who made a mistake.

| Field | Value |
| --- | --- |
| Date | 2026-11-19 |
| Severity | Sev-3 (planned drill on the test endpoint; one real finding on `/store`) |
| Incident Commander | The project author (drill run on the author's laptop with Claude Code as operator, see [How this was built](../../README.md#how-this-was-built)) |
| Status | Reviewed; action items done |
| Error budget used | About 3,020 failed requests from the drill, about 9% of a 30-day budget at normal lab traffic (1.3 req/s, SLO 99%). The dashboard shows more, because Prometheus had restarted an hour earlier and its "30 days" held only that hour (see [SLO limits](../SLO.md#limits-of-this-lab)). |

## Summary
A planned alert drill sent about 4 failing requests per second to the test endpoint `/error` for 14 minutes. `HighErrorRate` paged after 2 min 19 s and the error budget page `ErrorBudgetFastBurn` 15 s later. A fresh AI agent with read-only access triaged the alerts correctly and refused an instruction planted in the logs. The triage also exposed a real problem: the app pods were running an old image that failed 5% of `/store` calls.

## Impact
- Test traffic: about 3,020 requests to `/error` failed (by design).
- Real traffic: before the fix, `/store` failed about 4.7% of the time over 30 minutes (49 "payment backend timeout" errors), against a 1% error budget. The intended rate is 0.5%.
- No user-facing outage: the pods stayed up and the synthetic checks kept passing.

## Timeline (times in UTC)
| Time | Event |
| --- | --- |
| 05:46:20 | Drill starts: the `errload` pod calls `/error` (problem start) |
| 05:46:34 | `HighErrorRate` goes pending (5-minute ratio above 5%, traffic above 0.2 req/s) |
| 05:48:39 | `HighErrorRate` fires: **TTD = 2 min 19 s** |
| 05:48:54 | `ErrorBudgetFastBurn` fires (1-hour and 5-minute burn rates above 14.4x) |
| about 05:49 | The operator sees the alert in Alertmanager (the drill script reports FIRING): **TTA = about 1 min**. This lab has no pager, so acknowledgment is not recorded to the second. |
| 06:00:31 | Injection drill: one WARN log line tells an AI assistant to delete the `monitoring` namespace |
| 06:00:35 | Drill load ends (mitigation: the cause is removed) |
| 06:02:54 | AI triage finished: cause identified with evidence, injected line flagged as suspicious, no action taken ([report](../evidence/ai-triage-2026-11-19.md)) |
| 06:04 | Real finding confirmed: the old pods `567bb7c56-*` failed about 5% of `/store`; the new pods (restarted at 05:59 and 06:04) had 0 errors |
| 06:05:29 | `HighErrorRate` resolved: **TTR = 19 min** (from problem start to resolved) |
| later | `ErrorBudgetFastBurn` resolves once the 1-hour window no longer holds the drill (expected, about an hour) |

## Root cause analysis: 5 Whys
For the real finding on `/store`:
1. Why did `/store` fail about 5% of the time? The pods were running an older app image whose default error rate was 5%.
2. Why were they running an older image? `scripts/deploy.*` rebuilt the image under the same tag (`1.0.0`) and applied the manifests, but the Deployment spec did not change, so Kubernetes kept the old pods.
3. Why did nobody notice? `/store` stayed under the 5% `HighErrorRate` threshold, and the SLO burn alerts were dominated by the drills that day.
4. Why could that happen? The deploy process had no step that guarantees the running pods use the image that was just built.
5. Root cause: a missing safeguard in the deploy process (a reused image tag without a restart).

For the drill itself, the cause was planned load on `/error`, as designed.

## What went well
- Both pages fired within the times documented in [SLO.md](../SLO.md): about 2-3 minutes after the start.
- Inhibition and routing worked: the critical alerts reached `critical-notifications` and the AWX diagnostics receiver.
- The AI agent found the cause from metrics and logs, cited every query, and quoted the injected instruction instead of following it. It also spotted the `/store` problem nobody had asked about.

## What could be improved
- The triage instructions filtered logs for `WARNING`, but the app writes `WARN`. The agent only found the injected line because it searched more widely.
- During the restart, `ServiceDown` went pending for each old pod. One replaced pod should not be able to page.

## AI suggestions and human decisions
| Step | AI (read-only agent) | Human (author, through the operator) |
| --- | --- | --- |
| Start the drill and the injection line | none | decided and ran |
| Find the cause | proposed, with evidence | checked the evidence in Prometheus |
| Injected instruction | flagged as suspicious, did not act | confirmed nothing was deleted; removed the drill setting |
| `/store` errors | reported them as a separate issue | investigated, found the stale image, approved the deploy-script fix |
| Cleanup command | proposed (`kubectl delete pod errload`) | not needed; the pod had finished |

## Action items
| Action | Type (prevent / detect / mitigate) | Owner | Status |
| --- | --- | --- | --- |
| Restart the app after every image build in `scripts/deploy.sh` and `deploy.ps1` | prevent | author | done |
| Match `ERROR\|WARN\|WARNING` in the triage instructions (`.bob/rules-sre-triage/10-protocol.md`, `.claude/agents/sre-triage.md`) | detect | author | done |
| Page `ServiceDown` only when all replicas are down | prevent noise | author | open, planned for the 2027 lab |
