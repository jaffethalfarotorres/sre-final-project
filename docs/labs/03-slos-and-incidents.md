# Part 3: SLOs, synthetic checks and incident response

In this part you decide what "reliable enough" means for the demo app, and you check it from the outside like a user would. Then you practise what happens when an alert fires: who does what, which runbook to follow, how to measure the response and how to write it up without blame. Everything runs on the core stack from [`../GUIDE.md`](../GUIDE.md). No extra add-ons are needed.

> **Road to Junior SRE, camp 3: The War Room.** Nimbus Store gets a reliability promise (an SLO), an error budget and an incident process. **SRE principle:** embrace risk with SLOs and error budgets, and learn from every incident without blame. **Skills for your CV:** SLIs, SLOs and error budgets, synthetic monitoring, incident response and blameless postmortems. M09b, "Join the guild (fork the repo)", has its steps on this page but counts toward camp 5, The Robot Workshop: do it before M12.

| Module | Title | Time |
| --- | --- | --- |
| [M06](#m06-slos-error-budgets-and-multi-window-burn-rate-alerts) | SLOs, error budgets and multi-window burn-rate alerts | 90 min |
| [M08](#m08-synthetic-monitoring-and-container-signals) | Synthetic monitoring and container signals | 60 min |
| [M09](#m09-incident-response-runbooks-postmortems-and-orr) | Incident response, runbooks, postmortems and ORR | 120 min |
| [M09b](#m09b-github-issues-pull-requests-and-projects-for-sre-work) | GitHub issues, pull requests and Projects for SRE work | 60 min |

**Before you start (every module).** Commands are the same in Terminal (Mac) and in the Ubuntu window (Windows WSL2). Run them from the project folder. If you use Docker Desktop with PowerShell on Windows instead, use `scripts\*.ps1` and `python` in place of `./scripts/*.sh` and `python3`.

```bash
cd ~/sre-final-project
kubectl get pods -A          # the core stack is running
./scripts/dashboards.sh --background   # opens the tunnels and gives the window back to you
```

On Windows PowerShell (and from IBM Bob) the same step is `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dashboards.ps1 -Background`.

The tunnels open Grafana (<http://localhost:3000>), Prometheus (<http://localhost:9090>), Alertmanager (<http://localhost:9093>), the app (<http://localhost:5000>) and Jaeger (<http://localhost:16686>). The Grafana password is copied to your clipboard (it is not printed, so it never lands in a chat): paste it with Ctrl+V or Cmd+V. To close the tunnels later, run the same command with `--stop` (PowerShell: `-Stop`).

---

### M06 SLOs, error budgets and multi-window burn-rate alerts

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| Topic 0 (SLO/SLI/SLA, error budgets); burn-rate alerts are new in 2027 | 90 min | No extra (core stack ~3.2-3.8 GiB) | Beginner to intermediate | Core stack deployed with [`../../scripts/deploy.sh`](../../scripts/deploy.sh); Part 2 (Prometheus, Grafana) |

**Learning objectives**
- Calculate an error budget and a burn rate from an SLO target and an observed error ratio.
- Explain why `ErrorBudgetFastBurn` uses two windows (5 m and 1 h) and why `ErrorBudgetExhausted` needs more than 100,000 requests of history.
- Trigger a fast burn on purpose and read it on the **SLO and Error Budget** dashboard.

**Concepts in 5 minutes**

An **SLI** is a measurement of what users feel, for example "the share of requests that did not return 5xx". An **SLO** is the target for that SLI over a window: here 99% availability over 30 days. An **SLA** is a promise to customers with a penalty; this project has none on purpose. The **error budget** is `1 - SLO`: 1% of requests may fail.

Why 99% and not 99.9%? The app fails about 0.5% of `/store` calls on purpose (1 in 200), so there is always a little real data. Counted over all requests that is about 0.2%, which is already more than a 99.9% budget (0.1%): that target would always be broken and would teach nothing. With 99%, normal traffic uses about one fifth of the budget. Read the full reasoning in [`../SLO.md`](../SLO.md).

The **burn rate** says how fast you spend the budget. At 1x the budget lasts exactly 30 days. At 6x it lasts 5 days. At 14.4x it lasts about 2 days. The highest possible burn rate is `1 / (1 - SLO)`: with 99% that is 100x, when every request fails. The rule file [`slo.yml`](../../k8s/config/prometheus/slo.yml) computes `slo:availability:burn_rate5m`, `burn_rate30m`, `burn_rate1h`, `burn_rate6h` and `burn_rate3d` as `(1 - SLI) / (1 - 0.99)`.

A burn-rate alert uses two windows. The long window (1 h) proves the problem is real and not a 10-second blip. The short window (5 m) proves it is still happening, so the alert also clears quickly after the fix. Both must be above the threshold at the same time. The thresholds are the standard ones from the Google SRE Workbook. Where 14.4 comes from: 30 days are 720 hours, and spending 2% of the budget in 1 hour is `0.02 × 720 = 14.4` times faster than "exactly on budget".

| Alert | Condition | Severity |
| --- | --- | --- |
| `ErrorBudgetFastBurn` | 1 h burn > 14.4x **and** 5 m burn > 14.4x, for 2 m (2% of the budget in 1 hour) | critical (page) |
| `ErrorBudgetSlowBurn` | 6 h burn > 6x **and** 30 m burn > 6x, for 15 m (5% of the budget in 6 hours) | warning (today) |
| `ErrorBudgetTicket` | 3 d burn > 1x **and** 6 h burn > 1x, for 30 m, and more than 100,000 requests in 3 days | warning (ticket) |
| `ErrorBudgetExhausted` | budget left < 0 **and** more than 100,000 requests in 30 days, for 5 m | critical |

Why the 100,000-request guard? Prometheus calls the window "30 days", but on a fresh cluster it only holds a few hours of data. One drill of ~3,000 failing requests would then look like a whole month of failures, and the alert would demand a feature freeze for nothing. `http_requests_total` counts every request to the app, not only the traffic generator. The traffic generator (one `/store` call about every 2 seconds, plus `/ask` now and then), the synthetic probes (two every 10 seconds) and the Kubernetes liveness and readiness probes on `/` (both pods) together send roughly 1.3 requests per second, or about 110,000 a day. So 100,000 requests is about 1 day of history.

**Lab steps**

1. Read the SLO table and the error budget policy.
   ```bash
   sed -n '/## Our SLOs/,/## Worked example/p' docs/SLO.md
   ```
   What you should see: availability 99%, latency 95% (`/store` under 500 ms), and the three budget bands (above 50%, 0-50%, spent).

2. Check that the rule files are valid. This uses Docker only, not the cluster.
   ```bash
   docker run --rm -v "$PWD/k8s/config/prometheus:/rules" --entrypoint promtool \
     prom/prometheus:v2.54.1 check rules /rules/alerts.yml /rules/slo.yml
   ```
   What you should see: `SUCCESS: 5 rules found` for `alerts.yml` and `SUCCESS: 21 rules found` for `slo.yml`. CI runs the same check in [`ci.yml`](../../.github/workflows/ci.yml).
   Then run the unit tests of the alerts. They feed made-up traffic into Prometheus and check which alerts fire, still without a cluster:
   ```bash
   docker run --rm -v "$PWD:/repo" -w /repo --entrypoint promtool \
     prom/prometheus:v2.54.1 test rules tests/rules/slo.test.yml tests/rules/alerts.test.yml
   ```
   What you should see: `SUCCESS` for both files. Open [`tests/rules/slo.test.yml`](../../tests/rules/slo.test.yml): one test shows the page firing at 15x and staying silent at 14x.

3. Query the SLO recording rules in Prometheus. Open <http://localhost:9090>, choose **Graph**, and run each query:
   ```promql
   sli:availability:ratio_rate30d
   slo:availability:error_budget_remaining
   slo:availability:burn_rate5m
   ```
   What you should see: availability around 0.998, budget left around 0.8, and a 5 m burn rate around 0.2x. Only `/store` fails (0.5% of its calls). The SLI also counts `/`, `/ask` and the probe calls, which always succeed, so it is higher than 0.995. The exact numbers depend on how long the cluster has run and on earlier drills.

4. Open the dashboard. In Grafana go to **Dashboards > SLO and Error Budget**.
   What you should see: the stats *Availability SLI (30 days)* and *Latency SLI (30 days, /store < 500 ms)*, two gauges for budget left, *Error budget burn rate*, *Availability SLI (5 m) vs objective*, and two synthetic-check panels.

5. Burn the budget fast. In the second window run the alert drill:
   ```bash
   ./scripts/trigger-alert.sh
   ```
   What you should see: `HighErrorRate is FIRING after about 180 seconds` (expected 150-200 s; it uses a 5-minute window, then `for: 2m`). The drill pod `errload` calls `/error` 3,000 times, about 4 calls per second, for 12-14 minutes. The script then reminds you that the budget page comes later.

6. Watch the burn. Refresh the *Error budget burn rate* panel and Alertmanager (<http://localhost:9093>).
   What you should see: the 5 m burn rate jumps to about 75x within a minute or two (about 75% of the requests fail; 100x would be every request). The 1 h burn rate climbs more slowly, because the hour still holds a lot of normal traffic. When it passes 14.4x and stays there for 2 minutes, `ErrorBudgetFastBurn` fires next to `HighErrorRate`: about 6-10 minutes after the start (sooner on a cluster younger than 1 hour). `ErrorBudgetExhausted` stays silent on a young cluster because of the 100,000-request guard. Check the guard yourself:
   ```promql
   sum(increase(http_requests_total{namespace="application"}[30d]))
   ```

7. Do the arithmetic. Write down the 5 m and 1 h burn rates from the dashboard, and compute how many days the budget would last at the 5 m rate (`30 / burn rate`).

**Self-check**
1. The SLO is 99%. Over 5 minutes, 2% of requests fail. What is the burn rate, and how long would the budget last?
2. Why does `ErrorBudgetFastBurn` need the 1 h burn rate above 14.4x too, and not only the 5 m one?
3. Why is there no SLA for this service?
4. On a cluster that is 3 hours old, the budget gauge shows a negative value after the drill. Why does `ErrorBudgetExhausted` not fire?
5. Which band of the error budget policy are you in when 30% of the budget is left, and what changes for releases?

<details><summary>Answers (try first)</summary>

1. `(1 - 0.98) / (1 - 0.99) = 0.02 / 0.01 = 2x`. The budget would last `30 / 2 = 15` days.
2. The 1 h window proves the problem is real and lasting: 2% of the monthly budget is gone in one hour. A 5 m spike alone could be noise; requiring both cuts false pages. The 5 m window makes the page clear soon after the fix. This is also why the page comes minutes after `HighErrorRate` in the drill.
3. It is a new internal service. The course says to postpone the SLA until the SLO has been met for a few quarters, and an SLA must be looser than the SLO.
4. The guard `sum(increase(http_requests_total{namespace="application"}[30d])) > 100000` is false. A few hours of data cannot represent 30 days; about 1 day of traffic is needed.
5. Between 0 and 50%: releases need a rollback plan and the reliability backlog is reviewed weekly.
</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| SLO queries return "Empty query result" | The rules evaluate every 30 s and the 1 h / 6 h windows need data. Wait a few minutes after deploy. Check **Status > Rules** in Prometheus for errors. |
| `trigger-alert.sh` prints "The alert has not fired yet" | Run `kubectl get pods -A`. Pods in `Pending` mean low memory: delete other add-ons, see [`../GUIDE.md`](../GUIDE.md#troubleshooting). Then run the script again. |
| `permission denied: ./scripts/trigger-alert.sh` | Run `chmod +x scripts/*.sh` once. |
| Browser says "This site can't be reached" on localhost:9090 | The tunnels are closed (for example after a restart). Run `./scripts/dashboards.sh --background` again (PowerShell: `scripts\dashboards.ps1 -Background`). |
| You edited `slo.yml` and nothing changed | Apply the stack again with `kubectl apply -k k8s` (or `./scripts/deploy.sh`). Kustomize renames the ConfigMap and rolls out Prometheus. |

**Instructor notes**
- Spend the first 20 minutes on the arithmetic on a whiteboard (the 99.9% / 43.2 minutes example in [`../SLO.md`](../SLO.md)). Students who understand `30 / burn rate` follow the rest easily.
- Demo live: start `trigger-alert.sh`, then keep the burn-rate panel on the projector. `ErrorBudgetFastBurn` fires a few minutes after `HighErrorRate` (about 6-10 minutes after the start), because the 1 h burn rate must pass 14.4x and then hold for 2 minutes. Use the wait to show how the 5 m line jumps at once while the 1 h line climbs slowly.
- Discussion: "Should the 0.5% built-in failure count against the SLO?" There is no single right answer; good answers mention what users feel.
- Grading idea: correct burn-rate calculation (40%), screenshot evidence (30%), a written proposal for the right SLO of a real service they know (30%).
- Evidence to submit: screenshot of the **SLO and Error Budget** dashboard during the drill; screenshot of Alertmanager with `ErrorBudgetFastBurn` firing; the promtool output; a short note with the days-to-exhaustion calculation.

**Clean up**

The drill pod stops by itself after about 12-14 minutes. To stop it early:
```bash
kubectl delete pod errload -n application --ignore-not-found
```

---

### M08 Synthetic monitoring and container signals

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| Topic 2 (synthetic monitoring), ex7 (cAdvisor), ex11 (golden signals) | 60 min | No extra (blackbox exporter is part of the core stack, 64 Mi limit) | Beginner | M06 |

**Learning objectives**
- Describe how the blackbox exporter tests the app from outside, and read `probe_success` and `probe_duration_seconds`.
- Explain why `SyntheticProbeFailing` probes `/` and not `/store`.
- Find CPU and memory per pod with cAdvisor metrics and the **Saturation** row of the **Golden Signals** dashboard.

**Concepts in 5 minutes**

The app reports its own metrics. But if the app is down, it reports nothing. **Synthetic monitoring** sends a fake user request on a schedule and records whether it worked. It catches problems that the app cannot see itself: a broken Service, wrong DNS, no ready pods.

In this project the blackbox exporter ([`blackbox.yaml`](../../k8s/blackbox.yaml)) runs in the `monitoring` namespace. Prometheus asks it, every 10 seconds, to call two URLs (job `blackbox-http` in [`prometheus.yml`](../../k8s/config/prometheus/prometheus.yml)): `/` and `/store`. Each probe gives `probe_success` (1 or 0) and `probe_duration_seconds`.

The alert `SyntheticProbeFailing` ([`alerts.yml`](../../k8s/config/prometheus/alerts.yml)) only watches `/` (`instance=~".*:5000/"`). The `/store` probe fails about 1 time in 200 by design (0.5%), so alerting on it would page on normal behaviour. It fires when fewer than 90% of probes succeeded over 2 minutes, for 2 minutes.

**cAdvisor** is built into the kubelet. It measures each container: CPU, memory, network. Prometheus scrapes it with the job `kubernetes-cadvisor` and keeps only the series the dashboards use. Saturation means "how full is the system". Memory close to the limit is the first sign of an OOM kill.

**Lab steps**

1. Check that both probes and cAdvisor are scraped. In Prometheus open **Status > Targets**.
   What you should see: `blackbox-http` with 2 targets UP, and `kubernetes-cadvisor` with 1 target (the Minikube node) UP.

2. Query the probes:
   ```promql
   probe_success{job="blackbox-http"}
   avg_over_time(probe_success{job="blackbox-http"}[10m])
   probe_duration_seconds{job="blackbox-http"}
   ```
   What you should see: `/` is always 1. `/store` is 1 almost all the time (it fails about 1 call in 200); its 10-minute average is usually 1, sometimes a little lower (for example 0.98) when one probe hit a built-in failure. Durations are between about 0.05 and 0.4 s for `/store` (the simulated backend delay).

3. See the probes in Grafana: **SLO and Error Budget** dashboard, panels *Synthetic checks: success (blackbox exporter)* and *Synthetic checks: response time*.

4. Look at container signals:
   ```promql
   sum by (pod) (container_memory_working_set_bytes{namespace="application", container!=""})
   sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="application", container!=""}[5m]))
   ```
   What you should see: one line per pod: the two `sre-metrics-app` pods and `traffic-generator` (plus `errload` while a drill runs).

5. Open **Dashboards > Golden Signals** and scroll to the **Saturation** row.
   What you should see: *CPU used per pod (cores, cAdvisor)* and *Memory working set per pod (cAdvisor)* for the `application`, `monitoring` and `opentelemetry` namespaces. Prometheus and Loki are usually the largest users of memory.

6. (Instructor demo, optional) Make the synthetic check fail. This stops the app for about 5 minutes. The instructor shows it on the instructor's cluster; students may repeat it on their own cluster, never on a shared one.
   ```bash
   kubectl scale deployment sre-metrics-app -n application --replicas=0
   ```
   What you should see: within about 10 seconds `probe_success` for `/` drops to 0, and after about 3 minutes `SyntheticProbeFailing` fires (the 2-minute average must fall below 0.9, then stay there for 2 minutes). Note that `ServiceDown` does **not** fire: with no pods there is no scrape target, so `up == 0` never becomes true. This is exactly the gap synthetic checks close. Restore the app:
   ```bash
   kubectl scale deployment sre-metrics-app -n application --replicas=2
   kubectl rollout status deployment/sre-metrics-app -n application
   ```

**Self-check**
1. What does a `probe_success` value of 0 mean, and who measured it?
2. Why is `/store` probed but not used by the `SyntheticProbeFailing` alert?
3. With zero app pods, why does `ServiceDown` stay silent?
4. Which cAdvisor metric shows how close a container is to an OOM kill?

<details><summary>Answers (try first)</summary>

1. The blackbox exporter, acting as a user, did not get a 2xx answer (or timed out after 5 s) from that URL.
2. `/store` fails about 0.5% of the time on purpose. An alert on it would fire on normal behaviour. It is still useful on the dashboard to see latency from the user side.
3. `ServiceDown` is `up{namespace="application"} == 0`. Without pods, Kubernetes service discovery finds no target, so there is no `up` series at all, not a 0.
4. `container_memory_working_set_bytes`, compared with `container_spec_memory_limit_bytes`.
</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| `blackbox-http` targets DOWN | Check the exporter pod: `kubectl get pods -n monitoring -l app=blackbox-exporter`. If it is not Ready, `kubectl rollout restart deployment/blackbox-exporter -n monitoring`. |
| cAdvisor panels are empty | Check **Status > Targets** for `kubernetes-cadvisor`. A 403 error means the Prometheus RBAC from [`rbac.yaml`](../../k8s/rbac.yaml) is missing; run `kubectl apply -k k8s` again. |
| Pods stuck in `Pending` after scaling back to 2 | The computer is short on memory. Delete add-ons from other parts, then check again. See [`../GUIDE.md`](../GUIDE.md#troubleshooting). |
| The app does not stay at 0 replicas | Check that you scaled the right namespace: `kubectl get deployment sre-metrics-app -n application`. Re-running `kubectl apply -k k8s` or the deploy script during the drill puts the replica count back to the manifest value, so wait until the drill ends. ArgoCD only manages `gitops-staging`, so it is not the cause. |

**Instructor notes**
- 10 minutes of theory, then let students find the two probes in **Status > Targets** themselves.
- Step 6 is the strongest live demo in this part: students see `ServiceDown` stay green while users get nothing. Demo it on the instructor's cluster; students may repeat it on their own cluster.
- Grading idea: ask for one new synthetic check they would add for a real service (URL, expected status, alert threshold) and why.
- Evidence to submit: screenshot of **Status > Targets** with `blackbox-http` and `kubernetes-cadvisor`; screenshot of the **Saturation** row; one-paragraph answer to self-check question 3.

**Clean up**

Nothing to remove. If you ran step 6, make sure the app is back to 2 replicas:
```bash
kubectl get deployment sre-metrics-app -n application
```

---

### M09 Incident response, runbooks, postmortems and ORR

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| Topic 1 (TTD/TTA/TTR), topic 3 (ORR checklist), topic 6 (incident management) | 120 min | No extra | Beginner to intermediate | M06; teams of 4 |

**Learning objectives**
- Classify an alert as Sev-1, Sev-2 or Sev-3 and assign the incident roles.
- Run a tabletop exercise with `trigger-alert.sh` and measure TTD, TTA and TTR from real timestamps.
- Write a blameless postmortem with a 5 Whys root cause, and review one ORR section with evidence.

**Concepts in 5 minutes**

An incident has a lifecycle: detect, notify, triage, mitigate, resolve, learn. [`../INCIDENT-RESPONSE.md`](../INCIDENT-RESPONSE.md) maps each step to a tool in this project.

**Severity** decides how loud the response is. Sev-1 is a full outage (for example `SyntheticProbeFailing`). Sev-2 is clear degradation (`HighErrorRate`, `ErrorBudgetFastBurn`). Sev-3 is minor (`HighLatency`, `ErrorBudgetSlowBurn`).

**Roles** for Sev-1 and Sev-2: the Incident Commander coordinates and does not debug; subject-matter experts fix; the communications lead posts updates; the scribe keeps the timeline; the on-call responder acknowledges.

**Response metrics** measure the team, not the product:

```
issue starts ──TTD──> alert fires ──TTA──> someone acknowledges ──TTR──> users recovered
```

The arrows show the order of events, not where each clock starts. In this course TTR is measured from the moment the problem starts to the moment the alerts clear, as the incident issue form defines it ("From problem start to alert resolved").

Targets here: TTD < 3 min, TTA < 5 min, TTR < 30 min.

Every alert has a `runbook_url` that points to [`../runbooks/`](../runbooks/). After the incident you write a **blameless postmortem** with [`../POSTMORTEM-TEMPLATE.md`](../POSTMORTEM-TEMPLATE.md): describe what the system allowed, not who made a mistake. The **ORR** ([`../ORR.md`](../ORR.md)) is the checklist you pass before a service goes live.

**Lab steps**

1. Read the playbook and the runbook you will use.
   ```bash
   sed -n '/## Severity levels/,/## After the incident/p' docs/INCIDENT-RESPONSE.md
   cat docs/runbooks/high-error-rate.md
   ```
   What you should see: the severity table, the five roles, the TTD/TTA/TTR targets, and the runbook steps Acknowledge, Diagnose, Mitigate.

2. Form the team. Assign Incident Commander, on-call responder, subject-matter expert and scribe. The scribe opens a timeline file:
   ```bash
   mkdir -p reports && echo "| Time (UTC) | Event |" > reports/tabletop-timeline.md
   ```

3. The instructor (or one student, secretly) starts the incident. The scribe writes the start time.
   ```bash
   date -u +%H:%M:%S && ./scripts/trigger-alert.sh
   ```
   What you should see: the start time, then after about 150-200 s `HighErrorRate is FIRING`. `ErrorBudgetFastBurn` (the error budget page) fires a few minutes later, about 6-10 minutes after the start, and the Grafana rule `ErrorLogBurst` (Loki) also reaches Alertmanager.

4. Read the firing time. The on-call responder runs:
   ```bash
   python3 -c "import json,urllib.request; [print(a['labels']['alertname'], a['labels'].get('severity'), a['startsAt']) for a in json.load(urllib.request.urlopen('http://localhost:9093/api/v2/alerts'))]"
   ```
   What you should see: one line per active alert with its UTC start time, including `HighErrorRate critical`. **TTD = `startsAt` of `HighErrorRate` minus the start time from step 3.**

5. Acknowledge. The on-call responder says "Ack, investigating" (in the Slack thread if Slack is set up, otherwise out loud) and the scribe writes the time. **TTA = acknowledgement time minus `startsAt`.** The IC declares the severity (Sev-2 per the runbook).

6. Diagnose with the runbook. In Grafana **SRE Metrics Demo**, the *Error Rate (5xx, all endpoints)* panel shows a large new `/error` series. Under it is the usual tiny `/store` line: about 0.5% of `/store` calls fail by design, at roughly the same rate as before the drill. The jump is only on `/error`. In **Explore > Loki** run:
   ```logql
   {service_name="sre-metrics-app"} | severity_text="ERROR"
   ```
   What you should see: many lines `simulated critical failure on /error`, plus an occasional `store request failed: payment backend timeout` (the normal 0.5% `/store` failures, which were there before the drill). To show only the drill errors, add `|= "/error"` to the end of the query. Per the runbook, this is the test endpoint, so the mitigation is to stop the load.

7. Mitigate and record the time.
   ```bash
   kubectl delete pod errload -n application && date -u +%H:%M:%S
   ```
   If `kubectl get pod errload -n application` already shows `Completed`, the load stopped by itself; write that in the timeline.
   What you should see: `pod "errload" deleted`. Within a few minutes `HighErrorRate` and `ErrorBudgetFastBurn` leave the Alertmanager list (run the command from step 4 again until they are gone). **TTR = time the alerts cleared minus the start time.** That is how the incident form defines it.

8. Write the postmortem. Copy the template and fill it in with your real timeline, TTD/TTA/TTR, error budget used (from the **SLO and Error Budget** gauge) and a 5 Whys.
   ```bash
   mkdir -p docs/postmortems && cp docs/POSTMORTEM-TEMPLATE.md "docs/postmortems/$(date -u +%Y-%m-%d)-tabletop-high-error-rate.md"
   ```

9. Review one ORR section. Open [`../ORR.md`](../ORR.md) section 5 (disaster recovery). For each row, confirm the evidence exists in the repo and decide if you agree with the result.
   ```bash
   grep -n "replicas\|maxUnavailable\|readinessProbe" k8s/application.yaml
   ```
   What you should see: `replicas: 2`, `maxUnavailable: 0` and a readiness probe, the evidence for "survives the loss of a pod".

**Self-check**
1. `SyntheticProbeFailing` fires. Which severity is it and which roles must be named?
2. The problem starts at 10:00, the alert fires at 10:02:30, someone acknowledges at 10:06 and the alerts clear at 10:20. Compute TTD, TTA and TTR. Which target is missed?
3. Why is the `HighErrorRate` alert `for: 2m` and not `for: 15m`?
4. Rewrite this sentence in blameless form: "Ana deployed a bad config and broke the store."
5. ORR section 5 is "Partial". Name the Medium gap and its fix.

<details><summary>Answers (try first)</summary>

1. Sev-1. Incident Commander, subject-matter experts, communications lead, scribe and on-call. Updates every 15 minutes, postmortem required.
2. TTD = 2.5 min (met, < 3). TTA = 3.5 min (met, < 5). TTR = 20 min (met, < 30). None is missed. Ask students to show the arithmetic.
3. A short `for:` keeps TTD low. It is one of the levers in the TTD row of [`../INCIDENT-RESPONSE.md`](../INCIDENT-RESPONSE.md). The trade-off is more short alerts.
4. Example: "A config change reached production without a validation step, and the store started returning 5xx." The fix is the missing safeguard, not the person.
5. Prometheus and Loki use `emptyDir`, so history is lost on restart. Fix: PersistentVolumeClaims plus a retention or remote-write plan.
</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| `trigger-alert.sh` fails with `pods "errload" already exists` or similar | A previous drill pod is still there. Run `kubectl delete pod errload -n application --ignore-not-found` and start again. |
| The python one-liner in step 4 fails with `Connection refused` | The Alertmanager tunnel is closed. Run `./scripts/dashboards.sh --background` again (PowerShell: `scripts\dashboards.ps1 -Background`). |
| No Slack or email message arrives | Slack and email are optional. Check `kubectl logs deployment/alertmanager -n monitoring --tail=30`: `no_team` or `invalid_token` means a wrong Slack URL, `535` a wrong email password. See [`../GUIDE.md`](../GUIDE.md) section 6. |
| Alerts do not clear after deleting `errload` | Normal for a few minutes: `HighErrorRate` and the fast burn both use a 5-minute window. Wait 5-7 minutes. |
| `ErrorBudgetSlowBurn` (warning) appears 15-30 minutes after the drill | Normal on a young cluster: its 6 h and 30 m windows still remember the drill. While the fast burn fires, Alertmanager mutes it (inhibition); afterwards it can show up on its own. It clears by itself within about 30 minutes. |
| `AlwaysFiringDemoAlert` is in the list | It is a demo alert that always fires to prove the pipeline works. Ignore it in the exercise. |

**Instructor notes**
- Timing: 20 min concepts and roles, 30 min tabletop, 40 min postmortem, 20 min ORR, 10 min debrief.
- The drill load ends by itself about 12-14 minutes after the start (about 10 minutes after `HighErrorRate` fires). If the team has not deleted `errload` by then, record TTR as "self-resolved" and discuss it, or have the scribe pause and treat the next `trigger-alert.sh` run as part two of the drill.
- Run the tabletop twice if time allows: the second run usually has a much lower TTA. That is the point of drills.
- Do not tell the on-call responder when the drill starts. Real TTD/TTA numbers are more interesting than rehearsed ones.
- If AWX was installed (Part on automation), Alertmanager can launch `collect-diagnostics` about 14 s after a critical alert fires; mention it as the next step of automation, not a requirement here.
- Grading idea: timeline accuracy and TTD/TTA/TTR arithmetic (30%), blameless language (20%), 5 Whys reaching a process gap (30%), ORR review (20%).
- Evidence to submit: `reports/tabletop-timeline.md`, the filled postmortem file, a screenshot of Alertmanager with the alerts firing, and a screenshot after they cleared.

**Clean up**
```bash
kubectl delete pod errload -n application --ignore-not-found
```
Keep the postmortem and timeline files. They are used in M09b.

---

### M09b GitHub issues, pull requests and Projects for SRE work

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| Topic 4 (GitHub fundamentals), topic 5 (GitHub Projects) | 60 min | No extra (runs on GitHub, not in the cluster) | Beginner | A GitHub account (step 0 creates your fork); GitHub CLI `gh` installed and `gh auth login` done; M09 postmortem |

**Learning objectives**
- Create the labels that the issue forms, the project automation and Dependabot expect, using `gh label create`.
- Open an incident issue with the form and link it to a pull request with `Fixes #<n>`.
- Track incident action items on a GitHub Projects board.

**Concepts in 5 minutes**

SRE work is tracked work. An incident is not finished when the alert clears; it is finished when its action items are done. GitHub gives you the pieces:

- **Issue forms** in [`.github/ISSUE_TEMPLATE/`](../../.github/ISSUE_TEMPLATE/): `incident.yml` asks for severity, alert name, TTD/TTA/TTR, 5 Whys and action items, and adds the `incident` label. Blank issues are disabled in `config.yml`.
- **PR template** [`pull_request_template.md`](../../.github/pull_request_template.md): a checklist (tests, `promtool check rules`, runbooks updated, no secrets) and an **SLO impact** section.
- **Project automation** [`project-automation.yml`](../../.github/workflows/project-automation.yml): new issues get `needs-triage`; a merged PR gets a comment that lists the issues it closed or referenced.
- **Dependabot** [`dependabot.yml`](../../.github/dependabot.yml): weekly update PRs for pip, GitHub Actions, Docker and Terraform, with labels `dependencies` plus the ecosystem.

Labels must exist before they are used. Dependabot does not create missing labels, so create them once.

**Lab steps**

0. Point the project folder at your fork. This step is the lab mission **M09b "Join the guild"**. When you are done, check it with `python3 scripts/lab.py check M09b` (Windows PowerShell: `python scripts/lab.py check M09b`). [`../GUIDE.md`](../GUIDE.md) section 3 cloned the course repo, so `origin` is the course repo and you cannot push to it.
   ```bash
   gh repo fork --remote
   gh repo set-default <your-user>/sre-final-project
   git remote -v
   gh repo set-default --view
   ```
   `gh repo fork --remote` creates the fork if needed, renames the course repo remote to `upstream` and makes your fork `origin`. `set-default` makes `gh issue` and `gh pr` work on your fork, not on the course repo.
   What you should see: `origin` points to `<your-user>/sre-final-project`, `upstream` to the course repo, and `--view` prints your fork.

   Then turn on two features that are off on a new fork. In your fork on GitHub open **Settings > General > Features** and tick **Issues**. In **Settings > Code security**, turn on **Dependency graph** and **Dependabot version updates**.

1. Create the labels in your fork (`--force` updates a label that already exists).
   ```bash
   gh label create incident --color B60205 --description "Incident follow-up and postmortem" --force
   gh label create needs-triage --color FBCA04 --description "New, not yet triaged" --force
   gh label create dependencies --color 0366D6 --description "Dependency updates" --force
   gh label create python --color 3572A5 --description "Python dependencies" --force
   gh label create github-actions --color 000000 --description "GitHub Actions updates" --force
   gh label create docker --color 0DB7ED --description "Docker image updates" --force
   gh label create terraform --color 7B42BC --description "Terraform provider updates" --force
   gh label list
   ```
   What you should see: the seven labels, plus GitHub's defaults `bug` and `enhancement` used by the other two forms.

2. Open an incident issue from the M09 tabletop. On GitHub click **Issues > New issue > Incident follow-up** and fill in severity, alert `HighErrorRate`, start time and your TTD/TTA/TTR. Or from the terminal:
   ```bash
   gh issue create --title "[Incident]: tabletop HighErrorRate" --label incident \
     --body "Sev-2. TTD/TTA/TTR and postmortem: see docs/postmortems/."
   ```
   What you should see: a new issue URL. Within a minute the **Project automation** workflow adds `needs-triage` (check the **Actions** tab).

3. Create a Project board. On GitHub open your profile > **Projects > New project > Board**. Add columns *Todo*, *In progress*, *Done*, and add the incident issue to *Todo*.

4. Fix one action item in a branch and open a PR. For example, add your postmortem file.
   ```bash
   git switch -c postmortem/tabletop
   git add docs/postmortems/
   git commit -m "docs: tabletop postmortem for HighErrorRate"
   git push -u origin postmortem/tabletop
   gh pr create --fill
   ```
   What you should see: the PR opens with the template. Edit the description: write `Fixes #<issue number>`, tick the relevant checklist items, and write "None" under SLO impact.

5. Merge the PR on GitHub.
   What you should see: the issue closes by itself, and the workflow posts a comment "Merged: linked issues" with the issue under **Closed by this PR**. Move the card to *Done* (or turn on the board's built-in "Item closed" workflow).

6. Look at Dependabot. Open **Insights > Dependency graph > Dependabot** (or **Pull requests**, filter `label:dependencies`).
   What you should see: update PRs appear on the weekly schedule, labelled `dependencies` and `python`, `github-actions`, `docker` or `terraform`.

**Self-check**
1. Why can you not open a blank issue in this repo?
2. What two things does `project-automation.yml` do, and which token does it use?
3. Which words in a PR description close an issue on merge?
4. Why should the labels exist before Dependabot runs?

<details><summary>Answers (try first)</summary>

1. `.github/ISSUE_TEMPLATE/config.yml` sets `blank_issues_enabled: false`, so every issue uses a form with the fields the team needs.
2. It adds `needs-triage` to new issues, and comments the closed/referenced issues on merged PRs. It uses only the built-in `GITHUB_TOKEN`, no extra secrets.
3. `Fixes #N`, `Closes #N` or `Resolves #N` (or linking the issue in the PR sidebar).
4. Dependabot does not create labels. Without them the PRs open unlabelled and the `label:dependencies` filter misses them.
</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| `gh: command not found` or `gh auth status` fails | Install the GitHub CLI as in GUIDE section 2 and run `gh auth login`. Run the commands inside your fork's folder. |
| `needs-triage` is not added | GitHub disables workflows on new forks. Open the **Actions** tab and click **I understand my workflows, go ahead and enable them**. |
| No "Merged: linked issues" comment | The workflow runs only on merged PRs, not closed ones. Check the run in the **Actions** tab. |
| Issue or PR opened on the course repo instead of your fork | Run `gh repo set-default <your-user>/sre-final-project` and create it again. Close the one on the course repo. |
| `git push` fails with `Permission denied` or `403` | `origin` is still the course repo. Run step 0 and check `git remote -v`. |
| No **Issues** tab in your fork | **Settings > General > Features > Issues**. |
| No Dependabot PRs | Turn on **Dependabot version updates** in **Settings > Code security**. The first PRs can take until the next weekly run. |
| Issue did not close on merge | The PR targeted a branch other than the default branch, or the description kept `Fixes #` without a number. |

**Instructor notes**
- Do this module right after M09 so the issue and PR carry real content.
- Demo live: merge a PR with `Fixes #N` and show the issue closing and the bot comment within a minute.
- Grading idea: incident issue complete (40%), PR linked and template filled honestly (40%), board with the item in *Done* (20%).
- Evidence to submit: links to the incident issue and the merged PR, and a screenshot of the Project board.

**Clean up**

Nothing in the cluster. In your fork you may delete the branch. The PR was merged on GitHub, so first get the merge into your local `main`. Use `-D`: a squash merge never counts as merged for `-d`.
```bash
git switch main && git pull origin main && git branch -D postmortem/tabletop
git push origin --delete postmortem/tabletop   # or use the Delete branch button on the merged PR
```

---

### Portfolio project P-RUNBOOK: a new runbook

Optional and open to everyone. It is worth 250 XP. A runbook is the page an on-call engineer opens when an alert wakes them up, so writing one shows you think like an on-call SRE.

**What you build:** a new runbook in `docs/runbooks/`, linked from an alert rule's `runbook_url`.

1. Pick an alert in `k8s/config/prometheus/alerts.yml` or `slo.yml` that has no runbook of its own yet, or one you add yourself. Read the existing runbooks first, for example [`docs/runbooks/high-error-rate.md`](../runbooks/high-error-rate.md), and follow the same shape: what the alert means, how bad it is for users, the first checks (read-only), the fix, and how to confirm it is fixed.
2. Save your runbook under a new name, for example `docs/runbooks/synthetic-probe-failing.md`.
3. In the alert rule, set `runbook_url` to the new file. Use the same form as the other rules, with your fork's address, for example `https://github.com/<your-user>/sre-final-project/blob/main/docs/runbooks/synthetic-probe-failing.md`. Keep the YAML indentation exactly as in the rules around it.
4. Apply and check (Windows: `python scripts/lab.py check P-RUNBOOK`):
   ```bash
   kubectl apply -k k8s
   python3 scripts/lab.py check P-RUNBOOK
   ```
   What you should see: "new runbook ... is linked from an alert rule".

**For the interview:** be ready to walk someone through your runbook in two minutes, as if they were on call for the first time.

> **Interview corner: The War Room.** A question you can expect: *"What is an error budget, and how does it change what the team does?"* Answer with what you did here: the SLO for Nimbus Store and its error budget (M06), the burn-rate alerts that fire when the budget is spent too fast, and the blameless postmortem you wrote after the drill (M09). Explain the trade-off in plain words: while budget is left, the team can ship new features; when it runs out, the team slows down and fixes reliability first. Rehearse it with Bob: type `/interview`.
