# Part 4: Logs, traces and LLM observability

Metrics tell you *that* something is wrong. Logs and traces tell you *where* and *why*. In this part you follow one request from a log line to its trace and back, and then you apply the same tools to a simulated generative AI (LLM) call, where tokens mean money and latency is slow and variable.

| Module | Title | Course mapping |
| --- | --- | --- |
| [M07](#m07-logs-and-traces) | Logs and traces | 2026 exercises 8, 9, 10 |
| [M23](#m23-llm-and-genai-observability) | LLM and GenAI observability | New in 2027 |

> **Before you start.** The core stack must be running: `./scripts/deploy.sh` (setup in [GUIDE.md](../GUIDE.md)). Run every command from the project folder, in Terminal (Mac) or the Ubuntu window (Windows). If you use Docker Desktop with PowerShell on Windows, use `scripts\*.ps1` and `python` instead of `./scripts/*.sh` and `python3`. Everything else is the same.

---

### M07 Logs and traces

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| 2026 ex8 (OTel tracing + Jaeger), ex9 (spanmetrics), ex10 (Loki logging) | 75 min | No extra (part of the core stack, ~3.2-3.8 GiB in total) | Beginner to intermediate | Core stack deployed; [Part 2](02-metrics-dashboards-alerts.md) done |

**Learning objectives**

- Trace the path of a span and a log record from [`app/app.py`](../../app/app.py) through the OpenTelemetry Collector to Jaeger and Loki.
- Write a LogQL query that returns only the ERROR lines of `sre-metrics-app`.
- Navigate from a log line to its trace and from a span to its logs in Grafana, and explain how the spanmetrics connector turns spans into Prometheus metrics.

**Concepts in 5 minutes**

- A **trace** is the story of one request. It is made of **spans**. Each span is one step (for example `GET /store`, then its child `store.load_catalog`). Every span in the same request shares one **trace ID**.
- A **log** is a line of text the app writes. Our app writes JSON logs that carry the current `trace_id` and `span_id`. That shared ID is the bridge between logs and traces.
- The app sends traces and logs over **OTLP** (the OpenTelemetry protocol) to the **OpenTelemetry Collector** (`otel/opentelemetry-collector-contrib:0.111.0`). The pipeline is in [`k8s/config/otel-collector.yaml`](../../k8s/config/otel-collector.yaml):
  - `traces`: `otlp` receiver -> `memory_limiter`, `batch` -> `otlp/jaeger` exporter (Jaeger `1.62.0`) and the `spanmetrics` connector.
  - `metrics`: `spanmetrics` -> `prometheus` exporter on port `9464` (Prometheus scrapes it).
  - `logs`: `otlp` receiver -> `otlphttp/loki` exporter to Loki's native OTLP endpoint `http://loki.opentelemetry.svc.cluster.local:3100/otlp` (Loki `3.1.0`, config in [`k8s/config/loki.yaml`](../../k8s/config/loki.yaml)).
- The **spanmetrics connector** counts spans and measures their duration. It produces RED metrics (Rate, Errors, Duration) without changing the app. With the exporter namespace they are called `otel_collector_span_metrics_calls_total` and `otel_collector_span_metrics_duration_milliseconds_bucket`. `metrics_flush_interval: 15s` makes them update every 15 seconds.
- Why three signals? The alert fires on a metric. You open the ERROR logs to see the message. You open the trace to see which step failed and how long each step took.
- All three pieces live in the `opentelemetry` namespace and are defined in [`k8s/observability.yaml`](../../k8s/observability.yaml). Grafana links them through the datasources in [`k8s/config/grafana/datasources.yaml`](../../k8s/config/grafana/datasources.yaml): Loki has a derived field `TraceID` (log -> trace) and Jaeger has `tracesToLogsV2` (span -> logs, plus or minus 5 minutes).

**Lab steps**

1. Check that the Collector, Jaeger and Loki are running.
   ```bash
   kubectl get pods -n opentelemetry
   ```
   What you should see: three pods (`otel-collector-...`, `jaeger-...`, `loki-...`), each `1/1 Running`.

2. Read the Collector pipeline and find the three pipelines and the connector.
   ```bash
   grep -A 14 "pipelines:" k8s/config/otel-collector.yaml
   ```
   What you should see: `traces`, `metrics` and `logs` pipelines. `spanmetrics` appears as an exporter of `traces` and as a receiver of `metrics`. A connector is both. (In the cluster this file becomes a ConfigMap whose name starts with `otel-collector-config-` plus a content hash added by Kustomize, so a config change rolls out the Collector automatically.)

3. Open the tunnels. Keep this window open.
   ```bash
   ./scripts/dashboards.sh
   ```
   What you should see: a list with Grafana `http://localhost:3000`, Prometheus `9090`, Alertmanager `9093`, the app `5000` and Jaeger `16686`. Grafana opens in your browser.

4. In a second window, create a few errors so there is something to find.
   ```bash
   for i in $(seq 1 20); do curl -s -o /dev/null http://localhost:5000/error; done
   ```
   What you should see: no output. The app now has 20 failed requests, 20 ERROR log lines and 20 traces with an error status.

5. Find the error traces in Jaeger. Open <http://localhost:16686>, choose **Service** `sre-metrics-app`, set **Tags** to `error=true`, click **Find Traces**. You can also list services from the command line:
   ```bash
   curl -s http://localhost:16686/api/services
   ```
   What you should see: `sre-metrics-app` in the list. In the UI, red traces named `sre-metrics-app: GET /error`. A normal `/store` trace has two spans: `GET /store` and its child `store.load_catalog`. A failed `/store` trace also has `store.process_order` with the exception `payment backend timeout`.

6. Query the ERROR logs with LogQL. In Grafana, open **Explore**, choose the **Loki** datasource, switch to **Code** mode and run:
   ```bash
   {service_name="sre-metrics-app"} | severity_text="ERROR"
   ```
   What you should see: lines such as `simulated critical failure on /error` and `store request failed: payment backend timeout`. Remove `| severity_text="ERROR"` to see the INFO lines too (`store request served in ...`).

7. Go from a log line to its trace. Expand one ERROR line in Explore. In the fields list, find `trace_id` and click the **TraceID** link next to it.
   What you should see: the matching trace opens in a split view, from the Jaeger datasource. This is the derived field from `datasources.yaml`.

8. Go from a span to its logs. In Explore choose the **Jaeger** datasource, search service `sre-metrics-app`, open a `GET /store` trace, expand a span and click **Logs for this span**.
   What you should see: Grafana runs a Loki query filtered by that trace ID and shows only the log lines of that request.

9. Look at the metrics built from traces. In a third window, port-forward the Collector's metrics port and filter the output:
   ```bash
   kubectl port-forward -n opentelemetry service/otel-collector 9464:9464
   ```
   Then in another window:
   ```bash
   curl -s http://localhost:9464/metrics | grep otel_collector_span_metrics_calls_total | head -5
   ```
   What you should see: counters with labels such as `span_name="GET /store"` and `status_code="STATUS_CODE_ERROR"` or `"STATUS_CODE_UNSET"`. Press Ctrl+C in the port-forward window when done.

10. See the same data in Grafana. Open **Dashboards** -> **Golden Signals**.
    What you should see: **p95 latency per span (from traces, spanmetrics)**, **Failed spans per second (from traces)** and **ERROR log lines per minute (Loki)** all show data. The **Logs** row at the bottom lists app logs; click a line to open its trace.

11. Optional: query Loki from the command line (useful for scripts and AI agents in later parts).
    ```bash
    kubectl port-forward -n opentelemetry service/loki 3100:3100
    ```
    Then in another window:
    ```bash
    curl -sG http://localhost:3100/loki/api/v1/query_range \
      --data-urlencode 'query={service_name="sre-metrics-app"} | severity_text="ERROR"' \
      --data-urlencode 'limit=3' | python3 -m json.tool | head -40
    ```
    What you should see: JSON with `"status": "success"` and up to 3 log lines. Press Ctrl+C in the port-forward window when done.

**Self-check**

1. Why is `spanmetrics` listed as an exporter in one pipeline and as a receiver in another?
2. A log line has `trace_id` but Grafana shows no **TraceID** link. Which file would you check first?
3. Write a LogQL query that counts ERROR lines of `sre-metrics-app` per minute.
4. The **HighErrorRate** alert fired. In what order would you use metrics, logs and traces, and what does each one tell you?
5. Why does a failed `/store` trace have three spans, and a successful one only two?

<details><summary>Answers (instructors)</summary>

1. A connector joins two pipelines. It consumes spans at the end of the `traces` pipeline and produces metrics at the start of the `metrics` pipeline.
2. [`k8s/config/grafana/datasources.yaml`](../../k8s/config/grafana/datasources.yaml): the Loki datasource's `derivedFields` entry (`matcherType: label`, `matcherRegex: trace_id`, `datasourceUid: jaeger`).
3. `sum(count_over_time({service_name="sre-metrics-app"} | severity_text="ERROR" [1m]))`. It is the query of the Golden Signals panel. The Grafana rule **ErrorLogBurst** uses the same filter over `[5m]` with a threshold of 100.
4. Metrics first (is it real, how big, since when). Logs next (what the error message says). Traces last (which step failed and how long each step took).
5. The app opens the `store.process_order` child span only on the failure path, records the exception on it and sets its status to ERROR (see `store()` in [`app/app.py`](../../app/app.py)).

</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| Jaeger has no `sre-metrics-app` service | Check that the app has `OTEL_EXPORTER_OTLP_ENDPOINT` set (`kubectl get deployment sre-metrics-app -n application -o yaml \| grep -A1 OTEL`). Without it the app creates spans but sends nothing. Then check `kubectl logs deployment/otel-collector -n opentelemetry --tail=30`. |
| Logs appear under `service_name="unknown_service"` (seen in 2026 ex10, where the app was set up by hand) | In this repo `app/app.py` sets `service.name` from `OTEL_SERVICE_NAME` and defaults to `sre-metrics-app`, so this only happens if you changed the code or the env var. Check with `kubectl get deployment sre-metrics-app -n application -o yaml \| grep -A1 OTEL_SERVICE_NAME`. |
| Spanmetrics panels are empty right after deploy | The connector flushes every 15 s and Prometheus must scrape port 9464 first. Wait 1-2 minutes and refresh. |
| Spanmetrics stop after you change the connector config | Check the Collector logs (`kubectl logs deployment/otel-collector -n opentelemetry --tail=30`) for config errors, revert your change and re-apply with `./scripts/deploy.sh`. |
| Loki or Jaeger history is gone | Loki keeps data in an `emptyDir` volume (see [ORR.md](../ORR.md)) and Jaeger all-in-one keeps traces in memory (`MEMORY_MAX_TRACES` in [`k8s/observability.yaml`](../../k8s/observability.yaml)). A pod restart clears them. Generate new traffic. |
| `address already in use` on a port-forward | Another tunnel uses the port. Close it, or run `pkill -f "kubectl port-forward"`, then open the tunnels again ([GUIDE.md](../GUIDE.md#troubleshooting)). |

**Instructor notes**

- Timing: 15 min concepts with the pipeline drawn on the board, 45 min lab, 15 min self-check.
- Demo live: steps 7 and 8. The jump log -> trace -> logs is the moment students understand why the trace ID matters.
- Also demo the alert link: run `./scripts/trigger-alert.sh`. Measured on this project, **HighErrorRate** fires after about 140-150 s, and the Grafana rule **ErrorLogBurst** (Loki) also reaches Alertmanager. Then use logs and traces to "investigate".
- Map to the course: ex8 built the Collector and Jaeger by hand, ex9 added spanmetrics, ex10 added Loki with shared log volumes. Here all three are in one pipeline and Loki takes OTLP directly, so no volumes are needed.
- Grading ideas: correct LogQL (2 pts), a trace explained span by span (3 pts), the log -> trace jump shown (3 pts), one self-check answer in their own words (2 pts).
- Evidence to submit: screenshot of the Jaeger error trace; screenshot of the Loki ERROR query; screenshot of the log -> trace split view; the output of step 9 saved as `m07-spanmetrics.txt`.

**Clean up**

No add-ons were installed in this module. Press Ctrl+C in every port-forward window. Keep the core stack running for M23.

---

### M23 LLM and GenAI observability

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| New in 2027 | 60 min | No extra (no model is downloaded; `/ask` simulates the call) | Intermediate | M07 done; SLO basics from 2026 topic0 ([SLO.md](../SLO.md)) |

**Learning objectives**

- Identify the `gen_ai.*` span attributes on a model call in Jaeger and state their stability status.
- Calculate an hourly cost estimate from `genai_tokens_total` with PromQL.
- Justify a separate latency SLO for model calls using `genai_request_duration_seconds`.

**Concepts in 5 minutes**

- An LLM call is a slow, variable, metered dependency. Three things matter: **tokens** (they are the bill), **latency** (users wait), and **what was asked and answered** (debugging and safety).
- The `/ask` endpoint in [`app/app.py`](../../app/app.py) does not call a real model. It sleeps 0.2-1.2 s and invents a token count, but it records the call the way the OpenTelemetry **GenAI semantic conventions** describe. It opens a CLIENT span named `chat demo-model` with:
  - `gen_ai.operation.name` = `chat`, `gen_ai.provider.name` = `demo`
  - `gen_ai.request.model`, `gen_ai.request.max_tokens`, `gen_ai.response.model`
  - `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.response.finish_reasons`
- These conventions are in **Development** status. Names can still change between versions (for example, older libraries used `gen_ai.system` where newer ones use `gen_ai.provider.name`). Pin your instrumentation versions and check dashboards after upgrades.
- The app also exports two Prometheus metrics:
  - `genai_tokens_total{type="input"|"output"}`: a counter of tokens.
  - `genai_request_duration_seconds`: a histogram with buckets `0.25, 0.5, 0.75, 1.0, 1.5, 2.0`.
- The **traffic generator** in [`k8s/application.yaml`](../../k8s/application.yaml) calls `/store` every 2 s and `/ask` every 15th loop, so about one model call every 30 s.
- **Why its own SLO?** `/store` has a measured p95 of about 0.44 s (true value about 0.34 s, see Part 1), and **HighLatency** fires above 0.5 s. Model calls take up to 1.2 s by design. If you mix them, the app SLO either looks broken all the time or becomes so loose it hides real `/store` problems. Give each kind of call its own target.

**Lab steps**

1. Keep `./scripts/dashboards.sh` running in one window. In a second window, call the model endpoint once.
   ```bash
   curl -s http://localhost:5000/ask
   ```
   What you should see: `{"answer":"The store service is within its SLO.","usage":{"input_tokens":46,"output_tokens":...}}`. Input is always 46 (6 words plus a pretend 40-token system prompt). Output is random between 20 and 120.

2. Send ten more calls so the charts have data.
   ```bash
   for i in $(seq 1 10); do curl -s -o /dev/null http://localhost:5000/ask; done
   ```
   What you should see: no output; it takes about 7 seconds because each call waits on the "model".

3. Read the raw metrics from the app.
   ```bash
   curl -s http://localhost:5000/metrics | grep -E "^genai_(tokens_total|request_duration_seconds_count)"
   ```
   What you should see: `genai_tokens_total{type="input"}` and `genai_tokens_total{type="output"}` with growing values, and `genai_request_duration_seconds_count` equal to the number of calls this pod served.

4. Inspect the span attributes. In Jaeger (<http://localhost:16686>) choose service `sre-metrics-app`, operation `GET /ask`, click **Find Traces** and open one.
   What you should see: a parent span `GET /ask` and a child span `chat demo-model` that takes most of the time. Its tags list every `gen_ai.*` attribute from the concepts section.

5. Open the dashboard. In Grafana go to **Dashboards** -> **LLM Observability** (uid `llm-observability`).
   What you should see: six panels: **Tokens per minute (input vs output)**, **Estimated cost per hour (example price)**, **Model calls in the last hour**, **Model call latency p50 / p95**, **p95 of the model span (from traces)** and **GenAI call logs (Loki)**.

6. Check the cost estimate. In Prometheus (<http://localhost:9090>) run the same query as the cost panel:
   ```bash
   (sum(rate(genai_tokens_total{type="input"}[5m])) * 3 + sum(rate(genai_tokens_total{type="output"}[5m])) * 15) * 3600 / 1e6
   ```
   What you should see: a small dollar value, around $0.10-0.20 per hour with only the traffic generator. The panel uses an **example price** of $3 per million input tokens and $15 per million output tokens. Real prices differ by provider and model. Output tokens cost more, so they dominate the bill.

7. Compare latency from metrics and from traces. Run both in Prometheus:
   ```bash
   histogram_quantile(0.95, sum by (le) (rate(genai_request_duration_seconds_bucket[5m])))
   ```
   ```bash
   histogram_quantile(0.95, sum by (le) (rate(otel_collector_span_metrics_duration_milliseconds_bucket{span_name="chat demo-model"}[5m])))
   ```
   What you should see: about 1.3-1.4 (seconds) for the first query and about 1300 (milliseconds) for the second. The true p95 is about 1.15 s, but `histogram_quantile` can only interpolate inside a bucket (1.0-1.5 s for the metric, 1000-1400 ms for spanmetrics), the same accuracy cost you saw for `/store` in Part 1. The two sources agree within their bucket sizes. With only one model call every ~30 s the values are noisy; run step 2 again first.

8. Draft a latency SLI for model calls. Run in Prometheus:
   ```bash
   sum(rate(genai_request_duration_seconds_bucket{le="1.5"}[5m])) / sum(rate(genai_request_duration_seconds_count[5m]))
   ```
   What you should see: `1` (100% of calls under 1.5 s, because the demo never sleeps longer than 1.2 s). Write an SLO in one sentence, for example "95% of model calls finish in under 1.5 s over 28 days", and compare it with the `/store` SLO in [SLO.md](../SLO.md).

9. Run the unit test that covers `/ask` (no cluster needed).
   ```bash
   python3 -m pytest tests/test_app.py -k ask -q
   ```
   What you should see: `1 passed` (the test `test_ask_records_genai_usage`). If pytest is missing, run `pip install -r requirements-dev.txt` first.

**Self-check**

1. Which two `gen_ai.*` attributes would you sum to estimate the tokens of one request, and why might their names change next year?
2. Input tokens are fixed at 46 per call, but the cost panel still moves. Why?
3. With the example price, what costs more per call on average: input or output tokens? Show the math.
4. Give two reasons the model call needs its own latency SLO instead of sharing the `/store` one.
5. Why should a real system avoid putting the full prompt and answer text in span attributes or logs by default?

<details><summary>Answers (instructors)</summary>

1. `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens`. The GenAI conventions are in Development status, so attribute names can be renamed (as `gen_ai.system` became `gen_ai.provider.name`).
2. Output tokens are random (20-120), and the number of calls per minute changes (traffic generator plus manual calls).
3. Output. Input: 46 x $3 / 1,000,000 = about $0.00014. Output: about 70 on average x $15 / 1,000,000 = about $0.00105, roughly 7 times more.
4. Its normal latency (0.2-1.2 s) is above the `/store` HighLatency threshold (0.5 s), so a shared SLO would burn budget all the time or hide `/store` regressions. It also depends on an external provider with its own failure modes, so you want to see its budget separately.
5. Prompts and answers can contain personal or secret data, they make telemetry large and expensive, and they can carry prompt-injection text into tools that read logs (see M18). Capture content only on purpose, with redaction.

</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| LLM Observability panels show "No data" | The traffic generator calls `/ask` only about every 30 s and `rate(...[5m])` needs a few samples. Run step 2, wait 1-2 minutes, refresh. Check the generator runs: `kubectl get pods -n application`. |
| **Model calls in the last hour** differs from the number of calls you made | The panel adds up both app pods, but the newest calls appear only after the next scrape, `increase()` estimates and can show decimals, and a replaced pod takes its history with it. The traffic generator also adds about 2 calls per minute. Wait 30 s and compare roughly, not exactly. |
| `p95 of the model span (from traces)` is empty while the metric panels work | The spanmetrics path is broken, not the app. Go back to M07 step 9 and check `otel_collector_span_metrics_calls_total` has `span_name="chat demo-model"`. |
| `curl http://localhost:5000/ask` fails with "connection refused" | The tunnel is closed. Restart `./scripts/dashboards.sh` and keep that window open. |
| `ModuleNotFoundError` when running pytest | Run `pip install -r requirements-dev.txt` (inside your virtual environment if you use one). |

**Instructor notes**

- Timing: 15 min concepts, 35 min lab, 10 min SLO discussion.
- Demo live: step 4 (the `gen_ai.*` tags on a real span) and step 6 (change the price numbers in the panel query and watch the cost move). Stress that the price is an example.
- Discussion prompt: "Your provider doubles latency at 9 a.m. every day. Which panel shows it first, and who do you page?"
- Link forward: M17 (AI-assisted SRE) uses an AI agent to read these same dashboards through the Grafana MCP server; M18 shows why log content is untrusted input.
- Grading ideas: correct span attributes listed (2 pts), cost math for one call (3 pts), a written model-call SLO with SLI query (3 pts), self-check answer 5 (2 pts).
- Evidence to submit: screenshot of the `chat demo-model` span with its tags; screenshot of the **LLM Observability** dashboard; a short `m23-slo.md` with the SLO sentence, the SLI query from step 8 and the cost estimate.

**Clean up**

No add-ons were installed. Press Ctrl+C in the `./scripts/dashboards.sh` window to close the tunnels. To free memory when you finish for the day, run `minikube stop` (Mac users can also run `colima stop`).
