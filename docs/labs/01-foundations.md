# Part 1: Foundations

Part 1 gets every student to the same starting point. You set up a laptop cluster, read how the demo service creates metrics, traces and logs, and see how Kubernetes runs it safely. Every later part of the mega lab builds on this stack, so do not skip ahead until the self-checks pass.

| Module | Title | Time |
| --- | --- | --- |
| [M00](#m00-laptop-and-cluster-setup) | Laptop and cluster setup | 60-90 min |
| [M01](#m01-instrumenting-a-service) | Instrumenting a service | 60 min |
| [M02](#m02-kubernetes-deployment) | Kubernetes deployment (and the Docker image) | 75 min |

Lab time is about 3.5-4 h. Total with lecture and breaks: about 5.5 h.

All commands are the same in **Terminal** (Mac) and the **Ubuntu** window (Windows with WSL2). Run them from the project folder (`cd ~/sre-final-project`). If you use **Windows PowerShell** instead (IBM Bob, with Docker Desktop or Rancher Desktop), the same scripts exist as `scripts\*.ps1`, you type `python` instead of `python3`, and the lab script is `python scripts\lab.py` (Mac and Ubuntu: `python3 scripts/lab.py`). In M00 and M01, steps that use `curl`, `source`, `grep` or `pkill` have a **Windows PowerShell** line or block right under them.

---

### M00 Laptop and cluster setup

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| ex4 (Minikube), topic4 (clone a GitHub repo) | 60-90 min (first run downloads images) | ~3.2-3.8 GiB used by the core stack; 8 GB laptop minimum, 16 GB better | Beginner | Admin rights on the laptop, internet |

**Learning objectives**
- Install the container and Kubernetes tools on macOS (Homebrew + Colima) or Windows (WSL2 + Ubuntu).
- Deploy the full stack with one command and confirm every pod is `Running`.
- Open Grafana, Prometheus, Alertmanager, the app and Jaeger in a browser.

**Concepts in 5 minutes**

An SRE needs a place to break things safely. Minikube is a one-machine Kubernetes cluster. It needs a container engine underneath: Colima on a Mac, Docker Engine inside Ubuntu on Windows. The deploy script builds the app image, creates two private Secrets (Grafana login and Alertmanager settings), applies all manifests and waits until each Deployment is healthy.

The services run inside the cluster, so your browser cannot reach them directly. A *port-forward* is a tunnel from `localhost` on your laptop to a Service in the cluster. [`scripts/dashboards.sh`](../../scripts/dashboards.sh) opens all the tunnels in one window.

Memory is the most common blocker. The core stack uses about 3.2-3.8 GiB. Later parts add one tool at a time (ArgoCD, chaos, AWX, Kyverno, Argo Rollouts). Those were measured in a 6 GiB Minikube. Run one add-on at a time and delete it afterwards.

**Lab steps**

0. Before class: run the read-only preflight, `python scripts\preflight.py` (Mac: `python3 scripts/preflight.py`). It needs no admin rights and prints PASS, WARN, TODO or FAIL with a fix for each line. On an IBM-managed laptop, send [IT-REQUEST.md](../IT-REQUEST.md) to IT at least two weeks before class.
   What you should see: no FAIL line. TODO lines are the tools step 1 installs.

1. Install the tools. Follow [docs/GUIDE.md step 2](../GUIDE.md#2-install-the-tools-one-time) exactly (Mac or Windows section). Then check:
   ```bash
   docker version
   minikube version
   kubectl version --client
   git --version
   gh --version
   ```
   What you should see: each line prints a version. No `command not found`. (`gh` is needed for the fork in step 3.)

2. Mac only: start the container engine.
   ```bash
   colima start --cpu 4 --memory 6 --disk 60
   ```
   What you should see: Colima reports it is running (or that it already is). If you have 16 GB of RAM and plan to do step 4, you can start with `--memory 8` right away instead. On an **8 GB Mac** use `colima start --cpu 2 --memory 4 --disk 60`, skip step 4 and run no add-ons. Do not skip this step on an 8 GB Mac: if Colima is not running, `deploy.sh` (step 5) starts it with 6 GB.

3. Get the project: make your own **fork** and download it. Your work and your lab proof live in your fork (mission M09b checks this). Log in once first with `gh auth login` (see [GUIDE step 2](../GUIDE.md#2-install-the-tools-one-time)).
   ```bash
   cd ~
   gh repo fork jaffethalfarotorres/sre-final-project --clone
   cd sre-final-project
   ```
   What you should see: a folder with `app/`, `k8s/`, `scripts/` and `docs/`. A plain `git clone https://github.com/jaffethalfarotorres/sre-final-project.git` also works to look around, but then the fork mission does not pass (see [GUIDE step 3](../GUIDE.md#3-download-and-start-the-project)).

4. Optional, only if you plan to do the add-on modules in later parts and have 16 GB of RAM. [`deploy.sh`](../../scripts/deploy.sh) starts Minikube with 4096 MB only when no cluster is running, so create a bigger one first. If a Minikube cluster already exists, run `minikube delete` first: `minikube start` cannot change the memory of an existing cluster.
   ```bash
   # Mac only: give Colima more memory than Minikube will use
   # (stop it first; a running Colima ignores a new size)
   # Skip these two lines if you already used --memory 8 in step 2.
   colima stop
   colima start --cpu 4 --memory 8 --disk 60
   # all platforms
   minikube start --driver=docker --memory=6144
   ```
   What you should see: `Done! kubectl is now configured to use "minikube"`.

5. Deploy everything.
   ```bash
   ./scripts/deploy.sh
   ```
   What you should see: about 5-10 minutes of output on the first run, ending with `Deployment complete.` and a line about the Grafana login.

6. Check the pods.
   ```bash
   kubectl get pods -A
   ```
   What you should see: pods in the `application` namespace (two `sre-metrics-app` pods, one `traffic-generator`), `monitoring` (prometheus, alertmanager, grafana, blackbox-exporter) and `opentelemetry` (otel-collector, jaeger, loki). All `Running`, all containers ready (`1/1`).

7. Open the dashboards. Keep this window open.
   ```bash
   ./scripts/dashboards.sh
   ```
   Windows PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dashboards.ps1 -Background` (stop it later with `-Stop`).
   What you should see: a list of addresses: Grafana `http://localhost:3000` (user `admin`; the script copies the password to your clipboard and never prints it; if it cannot use the clipboard, it tells you where to find the password. Paste it into the login and never into a chat), Prometheus `:9090`, Alertmanager `:9093`, the app `:5000`, Jaeger `:16686`. An `MCP (AI)` line on `:8000` appears only after `scripts/ai_setup.py` has run (Part 7, M17). Grafana opens in your browser.

8. Look around. In Grafana open **Dashboards > SRE Metrics Demo**. In Prometheus open **Status > Targets**. In Alertmanager wait about a minute.
   What you should see: live charts in Grafana, the app target **UP** in Prometheus, and `AlwaysFiringDemoAlert` in Alertmanager. That alert is always on; it proves the alert pipeline works.

**Self-check**
1. Why does Minikube need Colima (Mac) or Docker Engine in Ubuntu (Windows)?
2. What does a port-forward do, and why must its window stay open?
3. Where is the Grafana admin password stored, and why is that file not in Git?
4. Why is `AlwaysFiringDemoAlert` useful even though it is "fake"?

<details><summary>Answers (try first)</summary>

1. Minikube with `--driver=docker` runs the cluster inside a container, so it needs a running container engine. Mac has no Linux kernel, so Colima provides a small Linux VM. WSL2 provides one on Windows.
2. It tunnels a port on `localhost` to a Service inside the cluster. It is a running process; closing the window stops the tunnel.
3. In `k8s/grafana-secret.yaml` (created by `deploy.sh` with a random value) and in the cluster Secret `grafana-admin-credentials`. The file is gitignored so credentials never reach the public repo.
4. It tests the whole path (Prometheus rule, Alertmanager, routing) without breaking anything. If it does not show up, the problem is the pipeline, not the app.
</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| Mac: `Cannot connect to the Docker daemon` | Run `colima start`, wait, try again. |
| Windows: `permission denied ... docker.sock` | Close and reopen the Ubuntu window. If it persists: `sudo systemctl start docker`. Check systemd was turned on ([GUIDE WSL step 4](../GUIDE.md#windows-by-hand-wsl2-and-ubuntu)). |
| `permission denied: ./scripts/deploy.sh` | `chmod +x scripts/*.sh` once. |
| `No such file or directory` for `scripts/...` | You are not in the project folder: `cd ~/sre-final-project`. |
| Pods stuck in `Pending` or `ContainerCreating` for more than 5 minutes | Short on memory. Close other apps. Mac with 16 GB: `colima stop`, then `colima start --cpu 4 --memory 8`. Then `minikube delete`, `minikube start --driver=docker --memory=6144` (step 4) and `./scripts/deploy.sh`. On an 8 GB laptop keep the 4096 MB default and run no add-ons. |
| Browser says "This site can't be reached" on localhost | The `dashboards.sh` window was closed. Run it again and keep it open. |
| `address already in use` when opening tunnels | Another tunnel uses the port: `pkill -f "kubectl port-forward"`, then rerun `./scripts/dashboards.sh`. Windows PowerShell: run `dashboards.ps1 -Stop`, then `-Background` again. |

**Instructor notes**
- Send the [GUIDE](../GUIDE.md) install steps one week before class. The first `deploy.sh` downloads several images; on shared Wi-Fi this is the slowest part of the day.
- Pair a Mac student with a Windows student. Most problems are memory or "wrong folder".
- Demo live: `kubectl get pods -A -w` while `deploy.sh` runs, so students see pods move from `ContainerCreating` to `Running`.
- Evidence to submit: screenshot of `kubectl get pods -A` with all pods `Running`; screenshot of the **SRE Metrics Demo** dashboard with data; screenshot of Alertmanager showing `AlwaysFiringDemoAlert`.
- Grading idea: pass/fail. All three screenshots, taken on the student's own laptop.

**Clean up**

Nothing to remove; later parts need this stack. To pause between classes:
```bash
minikube stop
colima stop        # Mac only, frees memory
```
To start again: `colima start` (Mac), `minikube start`, then `./scripts/dashboards.sh`.

---

### M01 Instrumenting a service

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| ex1 (Flask app), ex5 (Prometheus), ex8 (OTel tracing + Jaeger), ex10 (Loki logging) | 60 min | No extra (unit tests run on the laptop) | Beginner | M00; Python 3.10+ (`python3 --version`) |

**Learning objectives**
- Identify the three telemetry signals in [`app/app.py`](../../app/app.py) and the code that produces each one.
- Query the app's metrics in Prometheus, find one request in Jaeger and find its log line in Loki.
- Run the unit tests and explain what each telemetry test proves.

**Concepts in 5 minutes**

You cannot fix what you cannot see. The demo service is a small Flask "store". `/store` sleeps 50-350 ms and fails about 5% of the time on purpose, so there is always something to measure. It produces three signals:

- **Metrics** (numbers over time). `prometheus_client` defines a Counter `http_requests_total` with labels `method`, `endpoint`, `status`, and a Histogram `http_request_duration_seconds`. Prometheus scrapes them from `/metrics`. Counters answer "how many and how many failed". Histograms answer "how slow, for most users".
- **Traces** (the path of one request). `FlaskInstrumentor` creates one server span per request (for example `GET /store`). The code adds child spans: `store.load_catalog` (simulated database call) and `store.process_order` (only on failure, marked as ERROR). Spans go over OTLP to the OpenTelemetry Collector, then to Jaeger.
- **Logs** (what happened, in words). `JsonFormatter` writes one JSON line per event with `time`, `level`, `service`, `message`, and `trace_id` and `span_id`. The trace ID is the link: from a log line in Loki you can jump to its trace in Jaeger.

If `OTEL_EXPORTER_OTLP_ENDPOINT` is not set (tests, local runs), spans and logs are still created but nothing is sent. That is why the tests need no cluster.

**Lab steps**

1. Read the code. Open [`app/app.py`](../../app/app.py) and find `REQUESTS`, `REQUEST_DURATION`, `load_catalog()`, `JsonFormatter` and `FlaskInstrumentor().instrument_app(...)`.
   What you should see: the metric definitions near the top, and every endpoint calling `REQUESTS.labels(...).inc()`.

2. Create a virtual environment and install the dependencies.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements-dev.txt
   ```
   Windows PowerShell: do not activate the environment (`Activate.ps1` is a script, and script policy often blocks it). Call the Python inside it directly instead:
   ```powershell
   python -m venv .venv
   .venv\Scripts\python -m pip install -r requirements-dev.txt
   ```
   What you should see: `Successfully installed ... flask ... prometheus-client ... opentelemetry-sdk ... pytest ...`. On Ubuntu, if `venv` is missing: `sudo apt-get install -y python3-venv`. On a Mac, `python3 --version` must show 3.10 or newer; if it shows 3.9, use `python3.12 -m venv .venv` (see [GUIDE Mac step 4](../GUIDE.md#mac)).

3. Run the tests and the linter (the same checks CI runs in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)).
   ```bash
   pytest tests -q
   flake8 app tests scripts .claude/hooks --max-line-length=120
   ```
   Windows PowerShell:
   ```powershell
   .venv\Scripts\python -m pytest tests -q
   .venv\Scripts\python -m flake8 app tests scripts .claude/hooks --max-line-length=120
   ```
   What you should see: all tests pass (`passed`, no `failed`); flake8 prints nothing. Open [`tests/test_app.py`](../../tests/test_app.py) and read `test_store_creates_trace_spans`, `test_logs_are_json_with_trace_id` and `test_metrics_exposes_counters_and_histogram`.

4. Look at raw metrics from the running app. Keep `./scripts/dashboards.sh` open in another window. Reading `/metrics` is allowed in this lab: it only reads the numbers and changes nothing.
   ```bash
   curl -s http://localhost:5000/store
   curl -s http://localhost:5000/metrics | grep 'http_requests_total{'
   ```
   Windows PowerShell: type `curl.exe`, not `curl` (in PowerShell `curl` is a different command). The second line filters the output without a pipe:
   ```powershell
   curl.exe -s http://localhost:5000/store
   (curl.exe -s http://localhost:5000/metrics) -like 'http_requests_total{*'
   ```
   What you should see: a JSON body with `stores` (or the 5% error), then lines such as `http_requests_total{endpoint="/store",method="GET",status="200"} 1234.0` and some with `status="500"`.

5. Query the metrics in Prometheus (<http://localhost:9090>, **Query** tab). Paste each query and press **Execute**:
   ```bash
   sum by (status) (rate(http_requests_total{endpoint="/store"}[5m]))
   histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{endpoint="/store"}[5m])))
   sum(rate(http_requests_total{endpoint="/store",status="500"}[5m])) / sum(rate(http_requests_total{endpoint="/store"}[5m]))
   ```
   What you should see: the first query gives two series, about 0.5 req/s for `200` and a small value for `500` (the traffic generator calls `/store` every 2 s). The second gives the p95 latency, about 0.44 s. The real p95 is about 0.34 s, but `histogram_quantile` can only interpolate inside a bucket, and the nearest bucket edges are 0.3 and 0.5 (see `buckets=` in `app.py`). This is the normal accuracy cost of histogram buckets. The third gives the `/store` error ratio, about 0.05 (5%). It moves up and down because errors are random.

6. Find a failed request in Jaeger (<http://localhost:16686>). Choose service **sre-metrics-app**, set **Tags** to `error=true`, click **Find Traces**, open one trace.
   What you should see: a `GET /store` span with two children, `store.load_catalog` and `store.process_order`. The second is red and has the exception `payment backend timeout`. Copy the trace ID.

7. Find the matching log line. In Grafana open **Explore**, choose the **Loki** data source, switch to **Code** and run:
   ```bash
   {service_name="sre-metrics-app"} | severity_text="ERROR"
   ```
   What you should see: lines such as `store request failed: payment backend timeout`. Expand one: it has a trace ID field and a link to Jaeger. Follow it.

8. Compare with the pod's stdout.
   ```bash
   kubectl logs deployment/sre-metrics-app -n application --tail=5
   ```
   What you should see: JSON lines with `"trace_id"` and `"span_id"`, mixed with Gunicorn access-log lines (those are plain text, not JSON).

9. Record the mission: `python scripts\lab.py check M01` (Mac/Linux: `python3 scripts/lab.py check M01`).

> **Be honest about this check.** `lab.py check M01` looks for the app's metric series in Prometheus and for the service `sre-metrics-app` in Jaeger. The traffic generator creates both a few minutes after M00, so **the check can pass before you do steps 1-8**. A green check here only proves the stack sends signals. Your own work in M01 is the evidence below (the test output, your PromQL graph, and one trace ID found in both Jaeger and Loki). That is what a professor asks for.

**Self-check**
1. Why is `http_requests_total` a Counter and `http_request_duration_seconds` a Histogram?
2. What links a log line in Loki to a trace in Jaeger?
3. Why do the unit tests pass without a cluster or a Collector?
4. Why does the app run Gunicorn with one worker (see [`Dockerfile`](../../Dockerfile))?
5. `/metrics` requests do not create traces. Which line causes that, and why is it a good idea?
6. Step 5 shows a p95 of about 0.44 s, but `/store` never sleeps longer than 0.35 s. Why?

<details><summary>Answers (try first)</summary>

1. A request count only goes up; `rate()` turns it into requests per second and error ratio. Latency needs a distribution (buckets) so you can compute percentiles such as p95 with `histogram_quantile`.
2. The `trace_id` (and `span_id`) that `JsonFormatter` adds from the current span context. Grafana's Loki data source has a `TraceID` derived field that links to Jaeger.
3. Without `OTEL_EXPORTER_OTLP_ENDPOINT` no exporter is added. Spans and logs are created in memory; the tests attach an `InMemorySpanExporter` or a log handler to inspect them. `time.sleep` is patched to keep tests fast.
4. `prometheus_client` keeps counters in process memory. One worker means every scrape sees the same, consistent values. Threads (`--threads 4`) give concurrency.
5. `FlaskInstrumentor().instrument_app(app, excluded_urls="metrics")`. Prometheus scrapes every few seconds; tracing those calls would add noise and cost without telling you anything about users.
6. `histogram_quantile` only knows how many requests fell in each bucket. About 83% of requests are at or below 0.3 s; the rest are in the 0.3-0.5 s bucket. To find the 95th percentile it assumes requests are spread evenly inside that bucket: 0.3 + 0.2 x (0.95 - 0.833) / 0.167 = about 0.44 s. The true p95 is about 0.34 s. Finer buckets would give a closer answer.
</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| `curl: (7) Failed to connect to localhost port 5000` | The tunnel is not open. Run `./scripts/dashboards.sh` in another window and keep it open (Windows PowerShell: `scripts\dashboards.ps1 -Background`, with the full `powershell -NoProfile -ExecutionPolicy Bypass -File` form). |
| Windows PowerShell: `curl` asks for parameters or prints a table instead of text | You typed `curl`, which PowerShell maps to a different command. Type `curl.exe`. |
| `address already in use` for port 5000 | Another process or tunnel uses it. `pkill -f "kubectl port-forward"` and rerun `./scripts/dashboards.sh`. Windows PowerShell: run `dashboards.ps1 -Stop`, then `-Background` again. |
| `ModuleNotFoundError: No module named 'flask'` in pytest | The virtual environment is not active. Run `source .venv/bin/activate` and install again. Windows PowerShell: run the tests with `.venv\Scripts\python -m pytest`, not plain `pytest`. |
| Prometheus query returns `Empty query result` | Wait 1-2 minutes after deploy; `rate(...[5m])` needs a few scrapes. Check **Status > Targets** shows the app **UP**. |
| No traces in Jaeger | Check the Collector is running: `kubectl get pods -n opentelemetry`. Traces arrive in batches, so wait 10-20 s and search again. |

**Instructor notes**
- Spend 10 minutes walking through `app.py` on the projector before the lab. Students new to Python only need to recognise the three signal blocks.
- Demo live: open one red trace in Jaeger, copy its ID, find the same ID in Loki. This "click from log to trace" moment is the point of the module.
- Grading idea: give each student a different PromQL question (error ratio of `/store`, p99 latency, requests per second per endpoint) and grade the query and the number.
- `lab.py check M01` passes on any healthy stack, even without the student's work (see the note before the self-check). Grade M01 only on the evidence below, never on the check alone.
- Evidence to submit: terminal output of `pytest tests -q`; screenshot of the PromQL error-ratio graph (the third query in step 5); screenshot of a red Jaeger trace and of the matching Loki log line showing the same trace ID.
- Link forward: the metrics here feed the SLO recording rules in [`k8s/config/prometheus/slo.yml`](../../k8s/config/prometheus/slo.yml), explained in [`docs/SLO.md`](../SLO.md) (Part 3, M06).

**Clean up**

No add-ons. Leave the virtual environment when you are done:
```bash
deactivate
```
Windows PowerShell: nothing to do, because you never activated it.

---

### M02 Kubernetes deployment

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| ex2 (Docker image), ex3 (Docker Hub push), ex4 (Kubernetes on Minikube), ex18 (rolling update strategy) | 75 min | No extra (one surge pod of up to 256 Mi during updates) | Beginner to intermediate | M00, M01 |

**Learning objectives**
- Build the app image inside Minikube and explain why `imagePullPolicy: Never` is used.
- Explain each safety setting in [`k8s/application.yaml`](../../k8s/application.yaml): replicas, probes, requests and limits, securityContext and the RollingUpdate strategy.
- Demonstrate how Kustomize's `configMapGenerator` makes a config change roll out pods automatically.

**Concepts in 5 minutes**

*The image.* The [`Dockerfile`](../../Dockerfile) installs dependencies first (better layer caching), copies the app, creates user `appuser` (UID 1000) and runs Gunicorn. `deploy.sh` runs `minikube image build`, which builds the image *inside* the cluster. No registry is needed, which is why the Deployment says `imagePullPolicy: Never`. Building on your own machine also means it works on Apple Silicon and Intel. For publishing, CI builds `linux/amd64` and `linux/arm64` together with Docker Buildx, and CD pushes to GitHub Container Registry and, if secrets are set, Docker Hub (course ex3).

*The Deployment.* Each setting answers a "what if":
- `replicas: 2`: one pod can die (chaos test, node trouble, update) and the other still serves.
- `readinessProbe` on `/`: a pod gets traffic only when it answers. `livenessProbe`: a pod that stops answering for 6 checks in a row is restarted. Timeouts are generous because a busy Minikube can be slow.
- `requests` (50m CPU, 96Mi) tell the scheduler what to reserve. `limits` (300m CPU, 256Mi) stop one pod from starving the others.
- `securityContext`: non-root (UID 1000), no privilege escalation, all Linux capabilities dropped, default seccomp profile. Part 6 (M20) enforces these with Kyverno.
- `RollingUpdate` with `maxSurge: 1` and `maxUnavailable: 0`: start one new pod before stopping an old one, and never go below 2 ready pods. A broken release gets stuck in the new pod while old pods keep serving.

*The ConfigMap pitfall.* A pod reads its config file at start-up. If you change a ConfigMap with the same name, running pods keep the old config until someone restarts them. [`k8s/kustomization.yaml`](../../k8s/kustomization.yaml) uses `configMapGenerator`: Kustomize adds a hash of the file content to the ConfigMap name (for example `prometheus-rules-<hash>`) and updates every Deployment that uses it. New content means a new name, the pod template changes, and Kubernetes rolls out new pods by itself.

**Lab steps**

1. Build and run the image with plain Docker (course ex2).
   ```bash
   docker build -t sre-metrics-app:dev .
   docker run --rm -p 5001:5000 sre-metrics-app:dev
   ```
   What you should see: Gunicorn starts and listens on `0.0.0.0:5000`. In a second window `curl -s http://localhost:5001/` prints `SRE metrics demo is running...`. Press Ctrl+C to stop. (Port 5001 avoids a clash with the `dashboards.sh` tunnel on 5000.)

2. Check the image that the cluster uses.
   ```bash
   minikube image ls | grep sre-metrics-app
   ```
   What you should see: `docker.io/library/sre-metrics-app:1.0.0`. `deploy.sh` built it with `minikube image build -t sre-metrics-app:1.0.0 .`.

3. Publishing (course ex3), read only. Open [`.github/workflows/cd.yml`](../../.github/workflows/cd.yml) and find `platforms: linux/amd64,linux/arm64`. To publish from your own fork, follow [GUIDE step 7](../GUIDE.md#7-optional-publish-the-app-image-to-docker-hub). The manual course way is:
   ```bash
   docker tag sre-metrics-app:dev <your-dockerhub-user>/sre-metrics-app:dev
   docker login
   docker push <your-dockerhub-user>/sre-metrics-app:dev
   ```
   What you should see: the image under your Docker Hub account. Replace `<your-dockerhub-user>`; this step is optional.

4. Read the running Deployment.
   ```bash
   kubectl get deployment sre-metrics-app -n application
   kubectl describe deployment sre-metrics-app -n application
   ```
   What you should see: `READY 2/2`, `StrategyType: RollingUpdate`, `RollingUpdateStrategy: 0 max unavailable, 1 max surge`, and the liveness and readiness probes on `http-get http://:5000/`.

5. Prove the pod is not root.
   ```bash
   kubectl exec -n application deploy/sre-metrics-app -- id
   ```
   What you should see: `uid=1000(appuser) gid=1000(appuser) ...`.

6. Kill a pod and watch Kubernetes replace it. Open a watch first, then delete one pod in a second window:
   ```bash
   kubectl get pods -n application -l app=sre-metrics-app -w
   ```
   ```bash
   kubectl delete pod -n application "$(kubectl get pods -n application -l app=sre-metrics-app -o name | head -n 1 | cut -d/ -f2)"
   ```
   What you should see: one pod goes `Terminating`, a new one appears, goes `Running` and becomes `1/1` after the readiness probe passes. The Grafana error rate does not jump, because the other pod kept serving. Press Ctrl+C to stop the watch. If the pod you deleted was the one behind the `dashboards.sh` tunnel, <http://localhost:5000> stops answering. Press Ctrl+C in the dashboards window and run `./scripts/dashboards.sh` again.

7. Do a rolling update and roll it back.
   ```bash
   kubectl set env deployment/sre-metrics-app -n application APP_VERSION=1.0.1
   kubectl rollout status deployment/sre-metrics-app -n application
   kubectl rollout history deployment/sre-metrics-app -n application
   kubectl rollout undo deployment/sre-metrics-app -n application
   ```
   What you should see: pods are replaced one at a time (3 pods exist for a moment, never fewer than 2 ready), `successfully rolled out`, a history with two revisions (1 = original, 2 = `APP_VERSION=1.0.1`), then `rolled back`. Run `kubectl rollout history` again: the original is now revision 3. The app tunnel on port 5000 also follows one pod, so rerun `./scripts/dashboards.sh` if it stops answering.

8. See the ConfigMap hash. This only renders YAML on your laptop; it changes nothing in the cluster.
   ```bash
   kubectl kustomize k8s | grep -E "name: prometheus-rules-"
   ```
   What you should see: lines like `name: prometheus-rules-<hash>`, one for the ConfigMap and one in the Prometheus Deployment volume. Now add a comment line such as `# test` to the end of `k8s/config/prometheus/alerts.yml` and run the same command again: the hash changes.

9. Apply the change and watch the automatic rollout, then undo your edit.
   ```bash
   kubectl apply -k k8s
   kubectl rollout status deployment/prometheus -n monitoring
   git checkout k8s/config/prometheus/alerts.yml
   kubectl apply -k k8s
   ```
   What you should see: `configmap/prometheus-rules-<new hash> created`, `deployment.apps/prometheus configured`, and a new Prometheus pod, with no manual restart. Old ConfigMaps stay in the cluster; they are harmless. The new Prometheus pod starts with empty storage (the `data` volume is an `emptyDir`), so graphs show a gap and 30-day SLO numbers restart. Do this step at the end of a session, not right before an SLO or alert lab. The Prometheus tunnel on port 9090 also breaks; rerun `./scripts/dashboards.sh`.

**Self-check**
1. What would happen if you removed `imagePullPolicy: Never` and the image only existed inside Minikube?
2. With `replicas: 2`, `maxSurge: 1` and `maxUnavailable: 0`, how many pods can exist during an update, and what is the minimum number of ready pods?
3. What is the difference between a readiness probe and a liveness probe? What does each one do on failure?
4. Why does editing a normal ConfigMap not change a running Prometheus, and how does `configMapGenerator` fix it?
5. Why does CI build for both `linux/amd64` and `linux/arm64`?

<details><summary>Answers (try first)</summary>

1. For a tag that is not `latest` the default is `IfNotPresent`, so it would still start while the image is in Minikube. If the image is missing (for example after `minikube delete`), Kubernetes would try Docker Hub, find no `sre-metrics-app:1.0.0` and show `ErrImagePull`. `Never` states the "local image only" intent and fails fast with `ErrImageNeverPull` instead.
2. Up to 3 pods (2 + 1 surge). Never fewer than 2 ready.
3. Readiness failure removes the pod from the Service (no traffic) but does not restart it. Liveness failure (6 in a row here) makes the kubelet restart the container.
4. Prometheus reads its files at start-up and the pod template does not change, so Kubernetes has no reason to restart it. The generator puts a content hash in the name; the Deployment's volume reference changes, the pod template changes, and a rollout starts.
5. Students and servers use both Intel/AMD (amd64) and Apple Silicon or ARM servers (arm64). A multi-arch image runs natively on both.
</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| App pod shows `ErrImageNeverPull` | The image is not inside Minikube (for example after `minikube delete`). Run `minikube image build -t sre-metrics-app:1.0.0 .` or rerun `./scripts/deploy.sh`. |
| You changed a setting and nothing happened | Settings are read at start-up. Use `kubectl apply -k k8s` (the hash triggers a rollout), or `kubectl rollout restart deployment/<name> -n monitoring`. |
| A pod shows `CrashLoopBackOff` | Wait a minute; Kubernetes retries. If it stays, `kubectl logs <pod> -n <namespace> --previous`, then rerun `./scripts/deploy.sh`. |
| New pod stuck in `Pending` during an update | Not enough free memory for the surge pod. Remove any add-on from a later part, or free memory as in M00. |
| `localhost:5000` or `:9090` stops working after a pod was deleted or rolled out | A port-forward follows one pod. Ctrl+C the `dashboards.sh` window and rerun `./scripts/dashboards.sh`. |
| `docker run` fails with `address already in use` | Port 5001 is taken. Use another left-hand port, for example `-p 5002:5000`. |

**Instructor notes**
- Draw the rolling update on the board (old pods, one surge pod, readiness gate) before step 7. Students understand `maxUnavailable: 0` faster on paper.
- Demo live: step 6 with Grafana visible next to the terminal. The error-rate line stays flat while a pod dies.
- The ConfigMap pitfall cost real time in the 2026 course. Spend 5 minutes on steps 8-9; Part 2 depends on alert rule changes reaching Prometheus.
- Grading idea: ask students to explain in 3-4 sentences what happens, second by second, when the new image is broken (`maxUnavailable: 0` keeps the old pods serving). Part 6 (M14 rollbacks and M21 Argo Rollouts) then tests it.
- Evidence to submit: output of `kubectl describe deployment sre-metrics-app -n application` (strategy and probes visible); output of `kubectl exec ... -- id`; screenshot of the pod watch during step 6; the two `kubectl kustomize` outputs with different hashes.

**Clean up**

Make sure the rollback and the config edit are undone, then remove the local test image:
```bash
kubectl rollout status deployment/sre-metrics-app -n application
git status k8s/config
docker rmi sre-metrics-app:dev
```
`git status` should show no changes under `k8s/config`. No add-ons were installed in this module.
