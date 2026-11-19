# Part 2: Metrics, dashboards and alerts

In Part 2 you look inside the monitoring stack that `./scripts/deploy.sh` started. You learn how Prometheus finds and stores measurements, how Grafana dashboards and data sources are kept as code, and how an alert travels from a rule to Slack, email or an automation job. Every lab uses the same running stack, so there is nothing new to install.

| Module | Topic | Time |
| --- | --- | --- |
| [M03](#m03-prometheus-and-promql) | Prometheus and PromQL | 75 min |
| [M04](#m04-grafana-dashboards-as-code) | Grafana dashboards as code | 60 min |
| [M05](#m05-alertmanager-routing-and-grafana-alerting-as-code) | Alertmanager routing and Grafana alerting as code | 90 min |

**Before you start (all modules).** The stack from Part 1 is running and every pod is `Running`:

```bash
kubectl get pods -A
```

Open the tunnels in a second window and keep it open (Grafana 3000, Prometheus 9090, Alertmanager 9093, app 5000, Jaeger 16686):

```bash
./scripts/dashboards.sh
```

All commands are the same in Terminal (Mac) and the Ubuntu window (Windows). If you use Docker Desktop with PowerShell instead, the same scripts exist as `scripts\*.ps1` (for example `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\trigger-alert.ps1`). Setup help: [GUIDE.md](../GUIDE.md).

---

### M03 Prometheus and PromQL

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| 2026 ex5 (Prometheus), ex7 (cAdvisor), topic2 (synthetic monitoring) | 75 min | Core stack only (~3.2-3.8 GiB) | Beginner | Part 1 done, `./scripts/dashboards.sh` running |

**Learning objectives**

- Explain how the three scrape jobs in [prometheus.yml](../../k8s/config/prometheus/prometheus.yml) find their targets.
- Write PromQL queries that use `rate()`, `sum by ()` and `histogram_quantile()` on the app metrics.
- Compare what the app reports about itself with what the blackbox probe and cAdvisor report.

**Concepts in 5 minutes**

Prometheus **pulls** numbers. Every 10 seconds (`scrape_interval: 10s`) it calls an HTTP endpoint and stores what it gets as time series. The config has three jobs that matter:

- `kubernetes-pods` uses **service discovery**. Prometheus asks Kubernetes for every pod and keeps only pods with the annotation `prometheus.io/scrape: "true"`. The `prometheus.io/path` and `prometheus.io/port` annotations tell it where to call. The app has these annotations in [application.yaml](../../k8s/application.yaml) (`/metrics` on port `5000`). Pod labels, `namespace` and `pod` are copied onto every series.
- `kubernetes-cadvisor` reads container CPU, memory and network numbers from the kubelet. It goes **through the API server proxy** (`kubernetes.default.svc:443`, path `/api/v1/nodes/<node>/proxy/metrics/cadvisor`), so it needs the RBAC in [rbac.yaml](../../k8s/rbac.yaml). Only eight `container_*` metrics are kept (a `metric_relabel_configs` keep rule), to save memory.
- `blackbox-http` is **synthetic monitoring**. The blackbox exporter calls `/` and `/store` like a user and reports `probe_success` and `probe_duration_seconds`. It still works when the app's own `/metrics` is broken.

The app exports two main metrics (see [app/app.py](../../app/app.py)): the counter `http_requests_total{method,endpoint,status}` and the histogram `http_request_duration_seconds` (buckets from 0.05 s to 2.5 s). A counter only goes up, so you almost always wrap it in `rate()` to get "per second". A histogram stores counts per bucket (`_bucket{le="0.5"}`), and `histogram_quantile()` turns those buckets into a percentile such as p95.

Why it matters: every dashboard and alert in M04 and M05 is just a PromQL query. If you can read the query, you can trust (or question) the alert.

**Lab steps**

1. Check that all targets are healthy. Open <http://localhost:9090>, then **Status > Targets**. Or ask the API:
   ```bash
   curl -sG http://localhost:9090/api/v1/query --data-urlencode 'query=count by (job) (up == 1)' | python3 -m json.tool
   ```
   What you should see: jobs `prometheus`, `kubernetes-pods`, `kubernetes-cadvisor` and `blackbox-http`, each with the number of targets that are up (for example `"2"` for `blackbox-http`). In **Status > Targets**, `kubernetes-pods` lists the app pods and the OpenTelemetry Collector.

2. Look at the raw metrics the app exposes:
   ```bash
   curl -s http://localhost:5000/metrics | grep -E '^http_requests_total|^http_request_duration_seconds_bucket\{.*store' | head -15
   ```
   What you should see: lines such as `http_requests_total{endpoint="/store",method="GET",status="200"} 1234.0` and one `_bucket` line per `le` value.

3. Requests per second, by endpoint. In the Prometheus **Graph** page (or Grafana **Explore**), run:
   ```promql
   sum by (endpoint) (rate(http_requests_total{namespace="application"}[1m]))
   ```
   What you should see: `/` near 0.7 per second (the kubelet liveness and readiness probes of both pods plus the blackbox probe call it), `/store` near 0.6 per second (the traffic generator calls it every 2 s, the blackbox probe every 10 s), and a small `/ask` line (about one call every 30 s).

4. Error ratio. This is the exact expression behind the `HighErrorRate` alert in [alerts.yml](../../k8s/config/prometheus/alerts.yml):
   ```promql
   sum(rate(http_requests_total{namespace="application", status=~"5.."}[2m])) / sum(rate(http_requests_total{namespace="application"}[2m]))
   ```
   What you should see: a value around `0.02` to `0.03`. The app fails about 5% of `/store` calls on purpose, but the ratio divides by all requests, and the health-check probes on `/` never fail. So the normal ratio stays well below the 5% alert threshold. During the M05 drill it jumps to about 0.8.

5. p95 latency of `/store`:
   ```promql
   histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{namespace="application", endpoint="/store"}[5m])))
   ```
   What you should see: about `0.4` to `0.45` seconds. `/store` sleeps 50-350 ms, so the true p95 is about 0.34 s. `histogram_quantile()` only knows the bucket edges (0.3 and 0.5) and interpolates between them, so it reports a higher number. This is a good example of why bucket choice matters.

6. Synthetic checks and container resources:
   ```promql
   probe_success{job="blackbox-http"}
   ```
   ```promql
   sum by (pod) (container_memory_working_set_bytes{namespace="application", container!=""})
   ```
   What you should see: `probe_success` is `1` for both URLs (`:5000/` and `:5000/store`). Memory shows one line per app pod, in bytes.

7. See the recording rules and alert rules that are loaded:
   ```bash
   kubectl exec -n monitoring deploy/prometheus -- promtool check rules /etc/prometheus/rules/alerts.yml /etc/prometheus/rules/slo.yml
   ```
   What you should see: `SUCCESS` for each file and the number of rules found. Then open **Alerts** in the Prometheus UI. `AlwaysFiringDemoAlert` is firing; the others are inactive. The SLO rules are explained in [SLO.md](../SLO.md).

**Self-check**

1. Why does Prometheus scrape the app pods but not the traffic-generator pod?
2. Why do we write `rate(http_requests_total[1m])` instead of just `http_requests_total`?
3. The blackbox probe says `probe_success = 0` but `http_requests_total` keeps growing. What could be happening?
4. Why does the cAdvisor job go through `kubernetes.default.svc:443` instead of calling the node directly?

<details><summary>Answers (instructors)</summary>

1. Only pods with the annotation `prometheus.io/scrape: "true"` are kept by the `keep` relabel rule. The traffic generator has no such annotation.
2. A counter only grows since the pod started, so the raw value is meaningless for "how busy is it now". `rate()` gives the per-second increase and handles counter resets after a restart.
3. The app is reachable from inside its pod (or the traffic generator still gets answers) but not through the Service URL the probe uses, or the probe's request times out. The outside view of the user is broken while the inside view looks fine. That is why we keep both.
4. The API server proxy uses Prometheus's ServiceAccount token and the cluster CA, so the call is authenticated and authorized by the ClusterRole (`nodes/proxy`). It also works the same on any cluster, without knowing node IPs.

</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| Browser says "This site can't be reached" on localhost:9090 | The tunnel window was closed. Run `./scripts/dashboards.sh` again and keep it open. |
| `curl` right after starting the tunnels returns nothing | The tunnel is not ready yet (course Pattern S). Wait a few seconds and run it again. |
| A query returns "Empty query result" | Check the label spelling (`endpoint="/store"`, `namespace="application"`). Try the metric name alone first, then add labels. |
| `kubernetes-cadvisor` target is down with 403 | The RBAC in `k8s/rbac.yaml` is missing. Run `kubectl apply -k k8s`. |
| You edited `prometheus.yml` and nothing changed | Run `kubectl apply -k k8s`. Kustomize adds a hash to the ConfigMap name, so Prometheus restarts with the new file. Editing the ConfigMap by hand does not reload it (course Pattern C). |

**Instructor notes**

- Demo live: step 3 and step 4 side by side, then explain why `[2m]` is used in the alert and `[1m]` on the dashboard (smoother versus faster).
- Show `/metrics` raw text before any PromQL. Students understand `rate()` much faster after seeing a counter that only grows.
- Common confusion: `histogram_quantile` needs `sum by (le)`. Ask students to remove `by (le)` and see the query fail.
- Grading idea: give three questions in plain English ("p99 of all endpoints", "error requests per minute", "memory of the monitoring namespace") and check the PromQL.
- Evidence to submit: screenshot of **Status > Targets** with all jobs up; a text file with the three graded queries and their values.

**Clean up**

Nothing to remove. This module uses only the core stack.

---

### M04 Grafana dashboards as code

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| 2026 ex6 (Grafana), ex10 (Loki), ex11 (golden signals) | 60 min | Core stack only (~3.2-3.8 GiB) | Beginner | M03 |

**Learning objectives**

- Identify the four provisioned data sources and their fixed `uid` values in [datasources.yaml](../../k8s/config/grafana/datasources.yaml).
- Trace one error from a log line in Loki to its trace in Jaeger using the derived field.
- Change a provisioned dashboard in Git and deploy the change with one command.

**Concepts in 5 minutes**

If you build a dashboard by clicking, it lives only inside that one Grafana. When the pod is replaced, it is gone. Here everything is **provisioned from files** instead, so Git is the source of truth:

- [datasources.yaml](../../k8s/config/grafana/datasources.yaml) defines Prometheus (`uid: prometheus`, the default), Loki (`uid: loki`), Jaeger (`uid: jaeger`) and Alertmanager (`uid: alertmanager`). Fixed uids matter: dashboards and alert rules point to a data source by uid, so they keep working after a rebuild.
- The Loki data source has a **derived field** named `TraceID`. Every log line from the app carries a `trace_id` label, and Grafana turns it into a link to Jaeger. Jaeger has the reverse link (`tracesToLogsV2`) back to Loki.
- [dashboard-provider.yaml](../../k8s/config/grafana/dashboard-provider.yaml) tells Grafana to load every JSON file in `/var/lib/grafana/dashboards` into the folder **SRE Demo**.
- The four dashboards in [dashboards/](../../k8s/config/grafana/dashboards/) are: **SRE Metrics Demo** (`sre-metrics-demo`, the home page), **Golden Signals** (`golden-signals`: latency, traffic, errors, saturation, plus logs), **SLO and Error Budget** (`slo-error-budget`) and **LLM Observability** (`llm-observability`, used in M23).
- [kustomization.yaml](../../k8s/kustomization.yaml) turns these files into ConfigMaps with a content hash. When a file changes, the hash changes and Grafana restarts with the new version.

**Lab steps**

1. Log in. The password is printed by `./scripts/dashboards.sh`. You can also read it again:
   ```bash
   grep admin-password k8s/grafana-secret.yaml
   ```
   What you should see: a line `admin-password: "..."`. Open <http://localhost:3000>, user `admin`. The home page is **SRE Metrics Demo** with four panels.

2. Check the data sources. In Grafana go to **Connections > Data sources**.
   What you should see: Prometheus (default), Loki, Jaeger and Alertmanager. Each is marked as provisioned, so the UI does not let you change it. Click **Test** on Prometheus and Loki; both succeed.

3. Open each dashboard from **Dashboards > SRE Demo**, or directly:
   ```bash
   echo http://localhost:3000/d/golden-signals  http://localhost:3000/d/slo-error-budget  http://localhost:3000/d/llm-observability
   ```
   What you should see: Golden Signals has rows Latency, Traffic, Errors, Saturation and Logs. SLO and Error Budget shows the 30-day SLIs, budget gauges, burn rate and the blackbox checks. LLM Observability shows tokens per minute and model latency (the traffic generator calls `/ask` every 30 s).

4. Follow a log line to its trace. In **Golden Signals**, scroll to the **Logs** row. Click a line that says `store request failed: payment backend timeout`, then click the **TraceID** link.
   What you should see: Jaeger opens the trace of that request, with the span `store.process_order` marked as an error. From a span, **Logs for this span** brings you back to Loki.

5. Read how a panel is defined. Find the error-ratio panel in the file:
   ```bash
   grep -n '"title"' k8s/config/grafana/dashboards/golden-signals.json
   ```
   What you should see: every panel title, including `Error ratio (5xx / all requests)`. Its `expr` is the same PromQL you wrote in M03.

6. Change a dashboard as code. Open the SRE Metrics Demo file and change the title of one panel, for example `Store Request Rate` to `Store Request Rate (req/s)`:
   ```bash
   nano k8s/config/grafana/dashboards/sre-metrics.json
   ```
   Save (**Ctrl + O**, **Enter**, **Ctrl + X**), then apply and wait for Grafana:
   ```bash
   kubectl apply -k k8s && kubectl rollout status deployment/grafana -n monitoring
   ```
   What you should see: `configmap/grafana-dashboards-<new hash> created` and `deployment "grafana" successfully rolled out`. Restart `./scripts/dashboards.sh` (the tunnel to the old pod closed) and reload the page: the new title is there.

7. Try to save a change in the UI. Edit any panel and click **Save dashboard**.
   What you should see: Grafana says the dashboard is provisioned and cannot be saved directly. It offers to copy the JSON. This is on purpose: Git is the only place to change it.

**Self-check**

1. Why do the data sources have explicit `uid` values?
2. What two things must be true for the **TraceID** link to appear on a Loki log line?
3. You changed a dashboard in the UI and it vanished after a pod restart. Why, and how should you have done it?
4. Which golden signal would show the effect of a memory leak first, and on which panel?

<details><summary>Answers (instructors)</summary>

1. Dashboards and alert rules reference data sources by uid. A random uid would change on every rebuild and break every panel and the alert rules in `alerting.yaml`.
2. The log line must have a `trace_id` label (the app writes it through OpenTelemetry), and the Loki data source must define the derived field with `datasourceUid: jaeger`.
3. Grafana stores UI changes in its own database inside the pod, which has no persistent volume here. Provisioned dashboards cannot even be saved. The right way is to edit the JSON in `k8s/config/grafana/dashboards/` and run `kubectl apply -k k8s`.
4. Saturation: **Memory working set per pod (cAdvisor)** on the Golden Signals dashboard climbs steadily until the pod hits its limit and restarts.

</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| Grafana rejects the password | Run `grep admin-password k8s/grafana-secret.yaml` again and copy the text between the quotes exactly. |
| After `kubectl apply -k k8s` the browser shows "connection refused" | The Grafana pod was replaced and the tunnel pointed to the old one. Stop `./scripts/dashboards.sh` with **Ctrl + C** and run it again. |
| Grafana pod in `CrashLoopBackOff` after editing a JSON or YAML file | A syntax error. Check a JSON file with `python3 -m json.tool k8s/config/grafana/dashboards/sre-metrics.json > /dev/null`. For a YAML file, read the error from Grafana itself: `kubectl logs deployment/grafana -n monitoring --previous \| grep -i error`. (To check YAML locally, first run `python3 -m pip install --user pyyaml`, or use a venv if pip refuses on Homebrew Python, then `python3 -c "import yaml; list(yaml.safe_load_all(open('k8s/config/grafana/alerting.yaml')))"`.) Fix the file and apply again. |
| Logs panel is empty | Loki needs a minute after deploy. Check `kubectl get pods -n opentelemetry`; all three (collector, Jaeger, Loki) must be `Running`. |
| LLM Observability panels show "No data" | The traffic generator calls `/ask` only every 30 s. Wait 5 minutes, or call `curl -s http://localhost:5000/ask` a few times. |

**Instructor notes**

- Demo live: step 4 (log to trace) is the "wow" moment. Do it before explaining derived fields.
- Point out the hash in the ConfigMap name (`kubectl get configmap -n monitoring`). It is the fix for the 2026 course pitfall "ConfigMap changes do not reach running pods".
- Grading idea: each student adds one panel to `golden-signals.json` (for example `sum(rate(http_requests_total{namespace="application",status=~"5.."}[5m])) by (endpoint)`), deploys it and submits the diff.
- Evidence to submit: screenshot of the Jaeger trace opened from a log line; the `git diff` of the dashboard change; screenshot of the changed panel.

**Clean up**

Undo the practice edit so later modules match the docs:

```bash
git checkout -- k8s/config/grafana/dashboards/sre-metrics.json && kubectl apply -k k8s
```

---

### M05 Alertmanager routing and Grafana alerting as code

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| 2026 ex12 (Grafana alerting), ex13 (AWX webhook route), topic0 (error budgets), topic6 (incident management) | 90 min (+20 min for Slack/email) | Core stack only (~3.2-3.8 GiB) | Intermediate | M03, M04 |

**Learning objectives**

- Explain which receivers get an alert, given its `severity` label and the routing tree in [alertmanager.yaml](../../k8s/alertmanager.yaml).
- Trigger a real alert and measure how long it takes to fire.
- Describe why some rules live in Grafana ([alerting.yaml](../../k8s/config/grafana/alerting.yaml)) and still reach the same Alertmanager.

**Concepts in 5 minutes**

Prometheus **decides** that something is wrong (a rule is true for long enough, the `for:` time). Alertmanager **decides who hears about it**. It groups alerts, waits a little, removes duplicates and sends them to receivers.

The routing tree in `alertmanager.yaml` checks routes from top to bottom. The first match wins, unless the route says `continue: true`:

| Route (matcher) | Receiver | Note |
| --- | --- | --- |
| `severity = "demo"` | `demo-receiver` (Slack) | Only `AlwaysFiringDemoAlert`. Repeats every 12 h. |
| `severity = "critical"` | `awx-collect-diagnostics` (webhook) | `continue: true`, so the next route also runs. Launches the read-only AWX `collect-diagnostics` job (exercise 13 add-on). Without AWX the webhook just fails and is logged. |
| `severity = "critical"` | `critical-notifications` (Slack + email) | `ServiceDown`, `HighErrorRate`, `SyntheticProbeFailing`, `ErrorBudgetFastBurn`. `group_wait: 10s`. |
| `severity = "warning"` | `warning-notifications` (Slack + email) | `HighLatency`, `ErrorBudgetSlowBurn` and the Grafana rules. |
| anything else | `default-notifications` (Slack) | The top-level `receiver`. |

Secrets are never in this file. Slack and SMTP settings use `api_url_file` and `smtp_auth_password_file`, which read files mounted from the Secret `alertmanager-secret` (made from [alertmanager-secret.example.yaml](../../k8s/alertmanager-secret.example.yaml); the real file is gitignored). Alertmanager does not expand environment variables, which is why files are used.

Some checks cannot be written in PromQL, for example counting ERROR lines in Loki. **Grafana unified alerting** handles those. [alerting.yaml](../../k8s/config/grafana/alerting.yaml) provisions a contact point named `alertmanager` that forwards to the same Alertmanager, and a rule group `golden-signals` in folder **SRE Demo** with two rules:

- `StoreLatencyFromTraces`: p95 of `GET /store` from span metrics above 500 ms for 2 minutes.
- `ErrorLogBurst`: more than 100 ERROR log lines from `sre-metrics-app` in 5 minutes (LogQL), for 1 minute.

Both carry `severity: warning` and `source: grafana`, so they follow the warning route. One routing tree for all alerts means one place to change who gets paged.

**Lab steps**

1. Look at the routing tree as Alertmanager sees it:
   ```bash
   kubectl exec -n monitoring deploy/alertmanager -- amtool config routes show --config.file=/etc/alertmanager/alertmanager.yml
   ```
   What you should see: a tree that starts with `default-notifications` and lists the four child routes in the order of the table above.

2. Test where a label set goes, without sending anything:
   ```bash
   kubectl exec -n monitoring deploy/alertmanager -- amtool config routes test --config.file=/etc/alertmanager/alertmanager.yml severity=critical
   kubectl exec -n monitoring deploy/alertmanager -- amtool config routes test --config.file=/etc/alertmanager/alertmanager.yml severity=warning source=grafana
   ```
   What you should see: `awx-collect-diagnostics,critical-notifications` for the first (two receivers, because of `continue: true`), and `warning-notifications` for the second.

3. Confirm the pipeline works. Open <http://localhost:9093>.
   What you should see: `AlwaysFiringDemoAlert` with `severity="demo"`. This proves Prometheus can reach Alertmanager.

4. Check the Grafana rules. In Grafana open **Alerting > Alert rules**, folder **SRE Demo**, group **golden-signals**.
   What you should see: `StoreLatencyFromTraces` and `ErrorLogBurst`, both **Normal** and marked as provisioned. Under **Alerting > Contact points** there is `alertmanager`.

5. Run the alert drill. It starts the `errload` pod from [errload-pod.yaml](../../k8s/drills/errload-pod.yaml) (about 1,000 calls to `/error`) and waits for the alert:
   ```bash
   ./scripts/trigger-alert.sh
   ```
   What you should see: a line such as `HighErrorRate is FIRING after about 140 seconds.` (140-150 s was measured on this project). Write down the time; you need it for the self-check.

6. Watch the other alerts arrive. Refresh Alertmanager (<http://localhost:9093>) for 2-3 more minutes.
   What you should see:
   - `ErrorBudgetFastBurn` (critical). Its description shows a 5-minute burn rate of about 7x (7.3x was measured). See [SLO.md](../SLO.md) for why.
   - `ErrorLogBurst` with label `source="grafana"`. This proves the Grafana rule reached Alertmanager.
   - In Grafana, the **Error ratio** panel on Golden Signals and the **Error budget burn rate** panel on SLO and Error Budget both jump.

7. See what Alertmanager tried to send:
   ```bash
   kubectl logs deployment/alertmanager -n monitoring --tail=30
   ```
   What you should see: without Slack configured, `Notify for alerts failed` lines for `critical-notifications` (placeholder webhook) and for `awx-collect-diagnostics` (AWX not installed). That is expected. The routing worked; only delivery failed.

8. Optional: real Slack and email. Follow [GUIDE.md section 6](../GUIDE.md#6-optional-get-alerts-in-slack-and-email). In short: put your Slack webhook URL and Gmail app password in `k8s/alertmanager-secret.yaml`, put your addresses in `smtp_from`, `smtp_auth_username` and both `to:` lines of `k8s/alertmanager.yaml`, then:
   ```bash
   ./scripts/deploy.sh
   kubectl rollout restart deployment/alertmanager -n monitoring
   ./scripts/trigger-alert.sh
   ```
   What you should see: a `[FIRING] CRITICAL HighErrorRate` message in Slack and in the inbox within about 3 minutes, and a `[RESOLVED]` message some minutes after the drill ends.

9. Watch the alerts resolve. The `errload` pod stops by itself after about 4 minutes. Check it:
   ```bash
   kubectl get pod errload -n application
   ```
   What you should see: `Completed`. Over the next few minutes the alerts resolve. `HighErrorRate` goes first (2-minute window). `ErrorBudgetFastBurn` goes next: it needs the 5-minute burn rate above 6x **and** the 1-hour rate above 1x, so it ends once the 5-minute rate drops. `ErrorLogBurst` goes last, because its Loki query counts ERROR lines over 5 minutes.

**Self-check**

1. An alert has `severity="critical"`. Which receivers get it, and why more than one?
2. `HighErrorRate` has `for: 2m` and uses a `[2m]` window. Why did it take about 140-150 s to fire and not exactly 120 s?
3. Why does `ErrorLogBurst` live in Grafana and not in [alerts.yml](../../k8s/config/prometheus/alerts.yml)?
4. Where is the Slack webhook URL stored, and why is it not in `alertmanager.yaml`?
5. You change `alertmanager.yaml`, run `kubectl apply -k k8s`, and the old routing is still used. Why?

<details><summary>Answers (instructors)</summary>

1. `awx-collect-diagnostics` and `critical-notifications`. The first critical route has `continue: true`, so matching continues to the next critical route. Automation collects diagnostics while humans are notified.
2. The error ratio must first rise above 5% (the 2-minute rate window needs time to fill with errors), then stay above for 2 minutes. Add the 10 s scrape and evaluation interval and the script's 10 s polling.
3. Prometheus cannot query Loki logs. Grafana can run LogQL and forward the result to the same Alertmanager, so routing stays in one place.
4. In the Secret `alertmanager-secret` (from the gitignored `k8s/alertmanager-secret.yaml`), mounted as a file under `/etc/alertmanager-secrets/` and read with `api_url_file`. The repo is public; a webhook URL is a password.
5. `alertmanager-config` is a plain ConfigMap in `alertmanager.yaml`, not one generated by Kustomize with a hash, so the pod is not replaced. Run `kubectl rollout restart deployment/alertmanager -n monitoring`.

</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| `The alert has not fired yet` after 6 minutes | Check `kubectl get pods -A`. The app or Prometheus may not be `Running`. Delete the old drill pod with `kubectl delete pod errload -n application` and run `./scripts/trigger-alert.sh` again. |
| Alertmanager pod stuck in `ContainerCreating` | The Secret `alertmanager-secret` is missing. Run `./scripts/deploy.sh` (it creates it from the example) or `kubectl apply -f k8s/alertmanager-secret.yaml`. |
| No Slack or email message | `kubectl logs deployment/alertmanager -n monitoring --tail=30`. `no_team` or `invalid_token` means a wrong Slack URL. `535` means a wrong email address or app password. Fix the file and repeat GUIDE step 6e. |
| Changed `alertmanager.yaml` but nothing happened | `kubectl rollout restart deployment/alertmanager -n monitoring` (course Pattern C). |
| Grafana pod crash-loops after editing `alerting.yaml` | Read the error with `kubectl logs deployment/grafana -n monitoring --previous \| grep -i error`. (A local YAML check needs PyYAML first: `python3 -m pip install --user pyyaml`, or a venv on Homebrew Python.) The `receiver` under `policies:` must be the name of a contact point defined under `contactPoints` (here `alertmanager`) (course Pattern D). |
| `awx-collect-diagnostics` errors in the logs | Expected without AWX. The webhook fails and Alertmanager logs it; human notifications still go out. |

**Instructor notes**

- Timing: start `./scripts/trigger-alert.sh` before explaining the routing table. The 2-3 minute wait is your teaching time.
- Demo live: `amtool config routes test` with a few label sets. Then ask the class to predict the receiver before you press Enter.
- Discuss why remediation (restart) is never in the routing tree: the AWX route only collects diagnostics; a person launches `restart-app`. Link this to topic6 (incident management).
- Do not ask every student to set up Gmail in class. One shared Slack channel and one instructor webhook is enough; email can be homework.
- Grading idea: give students a new label set (for example `severity="warning", team="db"`) and ask them to add a route that sends it to a new receiver, then prove it with `amtool config routes test`.
- Evidence to submit: the `trigger-alert.sh` output with the firing time; screenshot of Alertmanager showing `HighErrorRate`, `ErrorBudgetFastBurn` and `ErrorLogBurst`; if configured, `slack-notification.png` and `email-notification.png` in `docs/screenshots/`.

**Clean up**

The drill pod stops by itself. Remove it so the next drill starts clean:

```bash
kubectl delete pod errload -n application --ignore-not-found
```

If you put real addresses in `k8s/alertmanager.yaml`, do not commit them (the repo is public). Restore the placeholders before you push:

```bash
git checkout -- k8s/alertmanager.yaml
```
