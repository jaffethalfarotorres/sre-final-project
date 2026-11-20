# Explore the lab: a map of what good looks like

This page is for the time after setup. The one command `python scripts/lab_up.py` (Mac and Linux: `python3`) has already installed the tools, started Kubernetes on your laptop, deployed the shop and its monitoring, and opened the pages. You now have a running system. This page tells you what to look at, why it is built that way, and what to try.

Think of the lab as a reference architecture. Each tool is set up the way a careful team would set it up. Your job is to find those choices, test them and ask questions. You do not need to know how to code.

**The five local pages** (opened by `lab_up.py`):

| Page | Address | What it is |
| --- | --- | --- |
| Nimbus Store | http://localhost:5000 | The small online shop (the app being watched) |
| Prometheus | http://localhost:9090 | Stores measurements and checks alert rules |
| Alertmanager | http://localhost:9093 | Decides who is told about an alert, and how |
| Grafana | http://localhost:3000 | Charts, logs and traces in one place |
| Jaeger | http://localhost:16686 | Shows the path of one request through the app |

**Grafana login.** You can look at everything without logging in (view-only). To change something, sign in with `admin` / `admin`. This is safe only because the page is reachable from your laptop alone.

**Words used on this page.** A *pod* is one running copy of a program. A *namespace* is a labelled box that groups related things in Kubernetes. A *manifest* is a text file that describes what Kubernetes should run. A *metric* is a number measured over time. A *query* is a question you type to a tool. *PromQL* is the question language of Prometheus, and *LogQL* is the one of Loki.

**Three kinds of safe.** "Read-only" means you only look. "In your clone" means you change a file on your laptop copy and nothing in the cluster changes. "Changes the cluster" means it alters the running lab: you run it yourself (or your AI agent runs it with your OK), and the step says how to undo it.

## Contents
1. [The shop and its Kubernetes setup](#1-the-shop-and-its-kubernetes-setup)
2. [Metrics with Prometheus](#2-metrics-with-prometheus)
3. [Alerts with Alertmanager](#3-alerts-with-alertmanager)
4. [Dashboards with Grafana](#4-dashboards-with-grafana)
5. [Logs with Loki](#5-logs-with-loki)
6. [Traces with Jaeger and OpenTelemetry](#6-traces-with-jaeger-and-opentelemetry)
7. [SLOs and error budgets](#7-slos-and-error-budgets)
8. [Infrastructure as Code](#8-infrastructure-as-code-kustomize-helm-terraform-ansible)
9. [CI/CD and supply chain](#9-cicd-and-supply-chain)
10. [Working safely with AI](#10-working-safely-with-ai)
11. [Where next](#where-next)

## 1. The shop and its Kubernetes setup

Kubernetes is a mini data center that keeps programs running. Here it runs on your laptop through Minikube. The shop runs in two copies, so one can fail while the other keeps serving.

### What good looks like
- Two replicas with a rolling update (`maxUnavailable: 0`), so a new version never drops below the wanted count.
- Both a liveness probe (restart if stuck) and a readiness probe (send traffic only when ready) on the app.
- CPU and memory requests and limits on every workload, so one program cannot starve the others.
- The app pod runs as a non-root user, drops all Linux capabilities and blocks privilege escalation.
- Three namespaces keep things apart: `application`, `monitoring`, `opentelemetry`.
- Prometheus gets read-only access only (`get`, `list`, `watch`) through its own ServiceAccount and a ClusterRole.
- One command deploys everything: `kubectl apply -k k8s` (Kustomize).

### Where to look
- [k8s/application.yaml](../k8s/application.yaml): the shop, its Service and the traffic generator (replicas, strategy, probes, securityContext, resources).
- [k8s/kustomization.yaml](../k8s/kustomization.yaml): the list of files that make up the lab.
- [k8s/rbac.yaml](../k8s/rbac.yaml): the read-only permissions for Prometheus.
- [k8s/prometheus.yaml](../k8s/prometheus.yaml), [k8s/observability.yaml](../k8s/observability.yaml): the other two namespaces.
- [app/app.py](../app/app.py) and [Dockerfile](../Dockerfile): the program and how it is packaged (non-root user, one Gunicorn worker).

### Try this
1. Read-only: `kubectl get pods -n application`. You should see two `sre-metrics-app` pods and one `traffic-generator`.
2. Read-only: `kubectl get deployment sre-metrics-app -n application -o jsonpath="{.spec.strategy}"`. It prints the rolling update settings from the file.
3. Changes the cluster: remove one pod and watch Kubernetes replace it. Run `kubectl delete pod <pod-name> -n application` (take the name from step 1), then `kubectl get pods -n application -w`. A person runs this, or the agent with your OK. Undo: nothing to undo, Kubernetes starts a new pod by itself. Meanwhile http://localhost:5000/store keeps answering from the other pod.

### Ask your agent
- "Why does the shop run in two copies, and what happens to users if one pod dies?"
- "Which settings in application.yaml make this pod safer than the default?"

### Not in this lab (on purpose)
The lab already follows the Kubernetes [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/) "restricted" profile (non-root, seccomp RuntimeDefault, no privilege escalation, all capabilities dropped; the namespaces carry warn and audit labels) and has a [PodDisruptionBudget](https://kubernetes.io/docs/tasks/run-application/configure-pdb/) for the shop. A production system would also add network policies, a read-only root filesystem, resource quotas, autoscaling and persistent volumes. Those are left out on purpose, to keep the lab small. The Kyverno policy in [policy/workload-baseline.yaml](../policy/workload-baseline.yaml) is an optional add-on that checks requests, limits, probes, non-root and pinned image tags.

## 2. Metrics with Prometheus

Prometheus pulls (scrapes) numbers from each program every 10 seconds, stores them, and checks rules against them.

### What good looks like
- Automatic discovery: any pod annotated `prometheus.io/scrape: "true"` is scraped, with no list to maintain.
- The labels `namespace`, `pod` and the pod labels are copied onto every series, so you can slice by them.
- The app measures requests (`http_requests_total`, labels `method`, `endpoint`, `status`) and latency (`http_request_duration_seconds`, a histogram).
- Recording rules in `slo.yml` precompute the ratios and burn rates once, instead of in every chart and alert.
- Alert rules carry a severity, a service label and a `runbook_url`, and use a `for:` delay to avoid noise.
- `HighErrorRate` needs at least 0.2 requests per second, so one failure out of three requests does not page anyone.
- Rules are unit tested with `promtool` without a cluster, and CI runs those tests.
- An outside view too: the blackbox exporter calls the shop like a user (`probe_success`).

### Where to look
- [k8s/config/prometheus/prometheus.yml](../k8s/config/prometheus/prometheus.yml): scrape jobs `kubernetes-pods`, `kubernetes-cadvisor`, `blackbox-http`.
- [k8s/config/prometheus/alerts.yml](../k8s/config/prometheus/alerts.yml): `ServiceDown`, `ReplicaDown`, `HighErrorRate`, `HighLatency`, `SyntheticProbeFailing`, and a demo alert.
- [k8s/config/prometheus/slo.yml](../k8s/config/prometheus/slo.yml): recording rules and the four budget alerts.
- [tests/rules/alerts.test.yml](../tests/rules/alerts.test.yml), [tests/rules/slo.test.yml](../tests/rules/slo.test.yml): the promtool tests.
- [app/app.py](../app/app.py#L105): where the metrics are defined.

### Try this
1. Read-only: open http://localhost:9090/targets, where every target should be UP. Then http://localhost:9090/rules to see the recording and alert rules.
2. Read-only, in the query box at http://localhost:9090/graph, run `sum by (endpoint, status) (rate(http_requests_total{namespace="application"}[5m]))`. Then run `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{namespace="application", endpoint="/store"}[5m])))`. It gives the 95th percentile latency: 95 of 100 requests are faster than this.
3. In your clone: run the rule tests with Docker (Mac and Linux): `docker run --rm -v "$PWD:/w" -w /w --entrypoint sh prom/prometheus:v2.54.1 -c 'promtool check rules k8s/config/prometheus/alerts.yml k8s/config/prometheus/slo.yml && promtool test rules tests/rules/*.test.yml'`. In PowerShell use `"${PWD}:/w"` and double quotes around the `-c` text. Then change `> 14.4` to `> 10` on the `ErrorBudgetFastBurn` lines of `slo.yml` and run it again: a test should now fail. Undo by changing it back.

### Ask your agent
- "Show me the three scrape jobs in prometheus.yml and tell me what each one measures."
- "Why does HighErrorRate have a minimum traffic condition?"

### Not in this lab (on purpose)
Prometheus data sits on an `emptyDir` volume, so history is lost when the pod restarts. A production system uses persistent storage and long-term storage. See [SLO.md](SLO.md#limits-of-this-lab).

## 3. Alerts with Alertmanager

Prometheus decides that something is wrong. Alertmanager decides who hears about it, once, and in what form.

### What good looks like
- Routing by severity: `critical`, `warning` and `demo` each go to their own receiver, with their own repeat interval.
- Grouping by `alertname`, `namespace` and `severity`, so many similar alerts arrive as one message.
- Inhibition: when `ServiceDown` fires, its symptoms (errors, latency, probes, budget burn) are muted. Muted alerts still show as "inhibited".
- Inhibition never hides a different failure: `ReplicaDown` is not a source, so one lost pod cannot mute errors on the pod still serving.
- Critical alerts also call a read-only diagnostics job (`continue: true`) when the optional AWX add-on is installed. A person still decides on any fix.
- Passwords and webhook URLs are read from files of a Secret, never written in the config. Only an `*.example.yaml` is in Git.
- Every alert has a `runbook_url` that points to a runbook in `docs/runbooks/`.
- The config is validated in CI with `amtool check-config`.

### Where to look
- [k8s/alertmanager.yaml](../k8s/alertmanager.yaml): `route`, `inhibit_rules`, `receivers`.
- [k8s/alertmanager-secret.example.yaml](../k8s/alertmanager-secret.example.yaml): the shape of the secret (no real values).
- [docs/runbooks/](runbooks/): one page per alert family.
- [.github/workflows/ci.yml](../.github/workflows/ci.yml): the step "Check Alertmanager config".

### Try this
1. Read-only: open http://localhost:9093 and http://localhost:9090/alerts. `AlwaysFiringDemoAlert` should be there: it exists to prove the path from Prometheus to Alertmanager works.
2. Read-only: open the `runbook_url` of one rule in `alerts.yml`, then compare it with the matching file in `docs/runbooks/`.
3. Changes the cluster, for about 12 to 14 minutes: run `python scripts/lab_up.py --drill` (a person, or the agent with your OK). It starts a pod that sends failing requests. Watch `HighErrorRate` go pending, then firing, then arrive in Alertmanager. Undo: it stops by itself, or run `kubectl delete pod errload -n application`.

### Ask your agent
- "Walk me through the route tree: where does a critical alert go, and why does it go to more than one place?"
- "If ServiceDown and HighErrorRate fire together, which one reaches my phone and why?"

### Not in this lab (on purpose)
One Alertmanager copy (no cluster of three), no on-call schedule tool and no silences as code. The Slack and email receivers need your own accounts. The phone push through ntfy is the account-free option (`python scripts/notify_setup.py`).

## 4. Dashboards with Grafana

Grafana draws the charts. Here, nobody clicked to build them: everything is files in Git.

### What good looks like
- Dashboards as code: four JSON files, loaded at startup, so a clone gives the same dashboards.
- Data sources as code, with fixed IDs (`prometheus`, `loki`, `jaeger`, `alertmanager`), so charts do not break when rebuilt.
- Provisioning puts the dashboards in a folder called "SRE Demo" with `disableDeletion: true`.
- The Golden Signals dashboard is laid out in rows: Latency, Traffic, Errors, Saturation, then logs.
- A CI step checks that every dashboard is valid JSON and has a unique `uid`.
- The admin login comes from a Secret, not from the manifest, and anonymous visitors are Viewers.
- Grafana-managed alert rules are also code, and they send to the same Alertmanager.

### Where to look
- [k8s/config/grafana/dashboards/](../k8s/config/grafana/dashboards/): `sre-metrics.json`, `golden-signals.json`, `slo.json`, `llm-observability.json`.
- [k8s/config/grafana/datasources.yaml](../k8s/config/grafana/datasources.yaml), [dashboard-provider.yaml](../k8s/config/grafana/dashboard-provider.yaml), [alerting.yaml](../k8s/config/grafana/alerting.yaml).
- [k8s/grafana.yaml](../k8s/grafana.yaml): how the files are mounted and how login is set.

### Try this
1. Read-only: open http://localhost:3000/d/golden-signals, then http://localhost:3000/d/slo-error-budget and http://localhost:3000/d/sre-metrics-demo.
2. Read-only: on a panel, open the menu, choose Explore, and read the query behind it. Compare it with the same query in the file under `dashboards/`.
3. In your clone: change a panel `title` in `golden-signals.json`, then run `kubectl kustomize k8s` to render the result (nothing changes in the cluster). Applying it with `kubectl apply -k k8s` changes the cluster: a person runs it, Kustomize gives the ConfigMap a new name and Grafana restarts with the new title. Undo: restore the file and apply again.

### Ask your agent
- "Which queries feed the Errors row of the Golden Signals dashboard?"
- "What would happen to my dashboard edits if the Grafana pod restarted?"

### Not in this lab (on purpose)
Grafana keeps its own database on the pod, with no persistent volume. Dashboards are rebuilt from the files at every start, so edits made in the browser are lost unless you copy them back into the JSON file.

## 5. Logs with Loki

Loki stores log lines and lets you search them. It answers "what did the program say".

### What good looks like
- Structured logs: the app writes one JSON line per event with `time`, `level`, `service` and `message`.
- Each line carries `trace_id` and `span_id` when a request is active, so a log can be tied to a trace.
- Logs travel through OpenTelemetry (OTLP) to the Collector, then to Loki. The app does not know Loki.
- The Collector has a `memory_limiter` and batches data, so a log burst does not crash it.
- Loki keeps logs for 72 hours (`retention_period: 72h`), and its config is checked in CI.
- A log-based alert rule exists too: `ErrorLogBurst` (more than 100 ERROR lines in 5 minutes).

### Where to look
- [app/app.py](../app/app.py#L60): `JsonFormatter`, the code that writes the log line.
- [k8s/config/loki.yaml](../k8s/config/loki.yaml) and [k8s/config/otel-collector.yaml](../k8s/config/otel-collector.yaml).
- [k8s/config/grafana/alerting.yaml](../k8s/config/grafana/alerting.yaml): `ErrorLogBurst`.

### Try this
1. Read-only: in Grafana open Explore (http://localhost:3000/explore), pick the Loki data source and run `{service_name="sre-metrics-app"}`.
2. Read-only: run `{service_name="sre-metrics-app"} | severity_text="ERROR"`. You see the simulated store failures (about 1 in 200 calls).
3. Read-only: run `sum(count_over_time({service_name="sre-metrics-app"} | severity_text="ERROR" [5m]))`. It is the same query that `ErrorLogBurst` uses.

### Ask your agent
- "Find the latest ERROR line from the shop and explain it in plain words."
- "What would we lose if the app wrote plain text instead of JSON?"

### Not in this lab (on purpose)
Loki runs as one copy on an `emptyDir` volume with no authentication (`auth_enabled: false`). A production Loki uses object storage, several copies and access control. There is no step that hides sensitive data in logs either.

## 6. Traces with Jaeger and OpenTelemetry

A trace is the story of one request: which steps it passed through and how long each took. OpenTelemetry is the open standard that the app and the Collector use to produce and move it.

### What good looks like
- The app creates a span for every web request automatically, plus its own child spans (`store.load_catalog`, `store.process_order`).
- Failures are recorded on the span (`record_exception`, status ERROR), not only in a log.
- Tracing is optional: without `OTEL_EXPORTER_OTLP_ENDPOINT` the app still serves traffic, and CD tests exactly that.
- The Collector turns spans into metrics (spanmetrics connector), so latency from traces is also charted through Prometheus.
- Logs and traces connect through `trace_id`: Loki lines link to Jaeger, and Jaeger spans link back to logs (a 5 minute window before and after).
- The `/metrics` path is excluded from tracing, so scraping does not fill Jaeger with noise.

### Where to look
- [app/app.py](../app/app.py#L141): the `/store` handler and its spans.
- [k8s/config/otel-collector.yaml](../k8s/config/otel-collector.yaml): receivers, processors, connector, exporters, pipelines.
- [k8s/config/grafana/datasources.yaml](../k8s/config/grafana/datasources.yaml): `derivedFields` (log to trace) and `tracesToLogsV2` (trace to log).
- [k8s/observability.yaml](../k8s/observability.yaml): the Collector, Jaeger and Loki deployments.

### Try this
1. Read-only: open http://localhost:16686, choose the service `sre-metrics-app`, click Find Traces, open one trace and read its spans.
2. Read-only: in Grafana Explore with Loki, run `{service_name="sre-metrics-app"} | severity_text="ERROR"`, open one line and click the `TraceID` link. It opens the failing request in Jaeger.
3. Read-only: in Explore with Prometheus, run `histogram_quantile(0.95, sum by (le, span_name) (rate(otel_collector_span_metrics_duration_milliseconds_bucket[5m])))`. This is latency computed from traces.

### Ask your agent
- "Take one failed /store request and show me its log line and its trace side by side."
- "Why does the Collector sit between the app and Jaeger instead of the app calling Jaeger directly?"

### Not in this lab (on purpose)
Jaeger keeps at most 5000 traces in memory (`MEMORY_MAX_TRACES`). Every request is traced, with no sampling. A production system samples, and stores traces in a database.

## 7. SLOs and error budgets

An SLO (service level objective) is a promise to users, in numbers. The error budget is how much failure the promise allows. [SLO.md](SLO.md) explains the full reasoning.

### What good looks like
- Two SLOs with plain definitions: availability 99%, and `/store` latency under 500 ms for 95% of requests, both over 30 days.
- Burn-rate alerts with two windows (the long one proves it is real, the short one proves it is still happening), at 14.4x, 6x and 1x.
- Each alert has a different action: page now, look today, open a ticket.
- Request-count guards (100,000 and 500,000) stop a young cluster from firing the long-window alerts by accident.
- A written error budget policy says what happens at each budget level.
- The SLO page states the limits of the lab honestly.

### Where to look
- [docs/SLO.md](SLO.md): definitions, table of alerts, policy, worked example.
- [k8s/config/prometheus/slo.yml](../k8s/config/prometheus/slo.yml): the recording rules and alerts.
- [k8s/config/grafana/dashboards/slo.json](../k8s/config/grafana/dashboards/slo.json): the dashboard "SLO and Error Budget".
- [docs/runbooks/error-budget-burn.md](runbooks/error-budget-burn.md): what to do when a budget alert fires.

### Try this
1. Read-only, in Prometheus: `slo:availability:error_budget_remaining` (1 means full budget, 0 means spent).
2. Read-only: `slo:availability:burn_rate5m` and `slo:availability:burn_rate1h`. On normal traffic both stay well under 1.
3. Changes the cluster: run the drill from section 3 and watch both burn rates rise on http://localhost:3000/d/slo-error-budget. Undo: the drill ends by itself. The budget it spent stays visible until Prometheus restarts.

### Ask your agent
- "Explain the 14.4x number as if I had never heard of it."
- "If the budget reaches zero, what does our policy say we must stop doing?"

## 8. Infrastructure as Code (Kustomize, Helm, Terraform, Ansible)

Infrastructure as Code means the setup is written in files, kept in Git and repeatable. This lab shows four tools for the same idea, each used for a different job.

### What good looks like
- Kustomize turns config files into ConfigMaps with a content hash in the name, so a config change rolls out new pods by itself.
- Helm: one chart with its settings in `values.yaml` (replicas, image, probes, resources), checked by `helm lint` and `helm template` in CI.
- The Helm chart can also create a ServiceMonitor or PodMonitor, and CD packages it with the version of the Git tag.
- Terraform: variables with descriptions and types, a validation rule (`replicas` from 1 to 5), outputs, and one namespace per workspace.
- Terraform state files are in `.gitignore`, and the provider lock file is committed.
- Ansible `site.yml` is written to be repeatable: it checks Minikube status and does not overwrite existing secret files.
- The Ansible runbooks use the `kubernetes.core` collection, and CI checks them with `ansible-lint --profile production`.

### Where to look
- [k8s/kustomization.yaml](../k8s/kustomization.yaml): the `configMapGenerator`.
- [helm/sre-metrics-app/values.yaml](../helm/sre-metrics-app/values.yaml), [helm/sre-metrics-app/templates/](../helm/sre-metrics-app/templates/), [helm/README.md](../helm/README.md).
- [terraform/main.tf](../terraform/main.tf), [terraform/variables.tf](../terraform/variables.tf), [terraform/outputs.tf](../terraform/outputs.tf).
- [ansible/site.yml](../ansible/site.yml), [ansible/runbooks/](../ansible/runbooks/).

### Try this
1. Read-only: `kubectl kustomize k8s | grep "name: prometheus-config"`. The name ends in a hash. Change one character in `prometheus.yml` in your clone and run it again: the hash changes. Undo by changing it back.
2. Read-only: `helm template sre helm/sre-metrics-app --namespace application` prints the manifests the chart would create. Add `--set replicaCount=3` and compare.
3. Read-only: `cd terraform`, `terraform init -backend=false`, `terraform validate`. Do not run `terraform apply` unless you want a second copy of the app in a new namespace: it changes the cluster, a person runs it, and `terraform destroy` undoes it.

### Ask your agent
- "Why does the lab deploy the monitoring stack with Kustomize but also ship a Helm chart and Terraform for the app?"
- "What does a Terraform workspace change about the namespace name?"

### Not in this lab (on purpose)
Terraform state is a local file, not a shared remote backend with locking. The Helm chart does not ship the PodDisruptionBudget that the Kustomize manifests have, and its `readOnlyRootFilesystem` is `false`. The optional add-on in `gitops/` (ArgoCD) shows the next step: Git as the only way to deploy.

## 9. CI/CD and supply chain

CI (continuous integration) checks every change automatically. CD (continuous delivery) builds and publishes a release. Supply chain security proves what is inside the image and who built it.

### What good looks like
- CI runs on every push and pull request, with read-only repository permission and one run per branch (`concurrency`).
- CI checks the code (flake8, pytest with coverage), security (bandit, and pip-audit that fails on known vulnerabilities), and every config in the repo.
- Config checks: Helm lint, Kustomize render with kubeconform, `promtool` check and tests, `amtool`, Grafana JSON, Collector and Loki validation, Terraform fmt and validate, Ansible lint.
- The image is built for Intel and Apple Silicon (amd64 and arm64) in CI.
- CD gives each job only the permissions it needs, and its scanner, signing and release actions are pinned to a full commit SHA.
- CD makes a parts list (SBOM, with Syft), blocks fixable CRITICAL vulnerabilities (Trivy), signs the image without keys (cosign) and publishes build provenance (SLSA).
- CD smoke-tests the image on a throwaway kind cluster before the chart is released.
- Dependabot opens weekly update pull requests for pip, GitHub Actions, Docker and Terraform.
- The issue automation runs with `pull_request_target` but never checks out pull request code.

### Where to look
- [.github/workflows/ci.yml](../.github/workflows/ci.yml): jobs `test`, `security`, `validate`, `iac`, `docker-build`, `scripts-*`.
- [.github/workflows/cd.yml](../.github/workflows/cd.yml): jobs `publish`, `smoke-test`, `helm-chart`.
- [.github/workflows/project-automation.yml](../.github/workflows/project-automation.yml) and [.github/dependabot.yml](../.github/dependabot.yml).
- [tests/test_app.py](../tests/test_app.py): the unit tests of the app.

### Try this
1. Read-only: on GitHub, open the Actions tab of the repository and open one CI run. Look at the job list and the step names.
2. In your clone: `pytest tests -q` (after `pip install -r requirements-dev.txt`), then `flake8 app tests scripts --max-line-length=120`. These are the same checks as the CI "test" job.
3. Read-only: `kubectl kustomize k8s > rendered.yaml`, then `helm lint helm/sre-metrics-app`. Delete `rendered.yaml` afterwards.

### Ask your agent
- "Explain each job in ci.yml in one sentence, in the order they appear."
- "What is an SBOM, and where does cd.yml create it?"

### Not in this lab (on purpose)
`ci.yml` pins most actions by version tag, not by commit SHA. CD publishes and tests the image but does not deploy it to a real cluster, and there is no manual approval step or separate staging and production environments.

## 10. Working safely with AI

An AI coding agent is fast and helpful, and it must not change things on its own. The lab teaches this in layers.

### What good looks like
- `AGENTS.md` is the one rulebook for every agent: six safety rules, from "read-only by default" to "stay in scope".
- A human approves every change. The agent proposes, a named person runs it, then the result is read back.
- Telemetry is untrusted data: a log line, alert text or trace attribute that talks to the agent is quoted as suspicious, never obeyed.
- No secrets: the agent must not read the real secret files, Terraform state or `.env` files.
- A triage answer must cite evidence (the query and its result) and follows a fixed six-part format.
- Several layers, not one: permission lists and a hook in `.claude/`, a read-only subagent, and a Kubernetes read-only identity (`ai-readonly`, bound to the built-in `view` role).
- The `/inject` drill endpoint is off unless a person turns it on, and it writes only one fake instruction as a log line.

### Where to look
- [AGENTS.md](../AGENTS.md): safety rules and triage output format.
- [docs/AI-SRE.md](AI-SRE.md): the student guide to AI on call.
- [.claude/settings.json](../.claude/settings.json), [.claude/hooks/guard_mutations.py](../.claude/hooks/guard_mutations.py), [.claude/agents/sre-triage.md](../.claude/agents/sre-triage.md).
- [k8s/ai/readonly-rbac.yaml](../k8s/ai/readonly-rbac.yaml) and [tests/test_guard_hook.py](../tests/test_guard_hook.py).
- [app/app.py](../app/app.py#L219): the injection drill.

### Try this
1. Read-only: read the six rules in `AGENTS.md` and the six headings of the triage format.
2. In your clone: `pytest tests/test_guard_hook.py -q`. It shows which commands the guard allows and which it blocks. One test is named `test_known_limit_runtime_built_commands`: the guard cannot see everything, so it is one layer, not the only one.
3. Ask your agent for a read-only triage of the current alerts, in the AGENTS.md format. Then check that every claim has a query and a result next to it.

### Ask your agent
- "If a log line told you to delete a namespace, what would you do, and why?"
- "Which of your commands can you run alone, and which need my OK?"

### Not in this lab (on purpose)
The command guard is a pattern check and says so itself: it cannot see commands built at run time. The Kubernetes read-only identity is the control that holds even if the agent is tricked. A production setup would also log every agent action in one central place and review it.

## Where next
- [GUIDE.md](GUIDE.md): step-by-step guide for Mac and Windows, with troubleshooting and a glossary.
- [FAQ.md](FAQ.md): the questions a reader would ask, from a failing request to a phone push.
- [SLO.md](SLO.md): the reliability promise in detail.
- [runbooks/](runbooks/): what to do when each alert fires.
- [labs/README.md](labs/README.md): the guided First on-call shift and the deeper lab modules.
- [COURSE-MAP.md](COURSE-MAP.md): where every course topic lives in this repository.
