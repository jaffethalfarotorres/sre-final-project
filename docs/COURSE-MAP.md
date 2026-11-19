# Course map

Where every SRE Academy topic, every new 2027 topic and every roadmap.sh DevOps area is implemented in this repository. ✅ = implemented and verified live on Minikube; 📘 = documented or covered by an exercise; ➖ = out of scope for a laptop lab (with the reason).

## SRE Academy 2026: topics and exercises

| # | Topic | Where in this project | Lab | Status |
| --- | --- | --- | --- | --- |
| Topic 0 | SLI, SLO, SLA, error budgets | [`docs/SLO.md`](SLO.md), [`slo.yml`](../k8s/config/prometheus/slo.yml) (recording rules, multi-window burn-rate alerts), *SLO and Error Budget* dashboard | [Part 3](labs/03-slos-and-incidents.md) | ✅ |
| Topic 1 | TTD, TTA, TTR | [`docs/INCIDENT-RESPONSE.md`](INCIDENT-RESPONSE.md), postmortem timeline, incident issue form | [Part 3](labs/03-slos-and-incidents.md) | ✅ |
| Topic 2 | Synthetic monitoring | Blackbox exporter [`k8s/blackbox.yaml`](../k8s/blackbox.yaml), `SyntheticProbeFailing` alert | [Part 3](labs/03-slos-and-incidents.md) | ✅ |
| Topic 3 | Operational Readiness Review | [`docs/ORR.md`](ORR.md) with evidence per item | [Part 3](labs/03-slos-and-incidents.md) | ✅ |
| Topic 4 | GitHub fundamentals | Issue forms, PR template, Dependabot, [`CONTRIBUTING.md`](../CONTRIBUTING.md) | [Part 3](labs/03-slos-and-incidents.md) | ✅ |
| Topic 5 | GitHub Projects | [`project-automation.yml`](../.github/workflows/project-automation.yml) (triage label, merged-PR summary) | [Part 3](labs/03-slos-and-incidents.md) | ✅ |
| Topic 6 | Incident management | Severities, roles, war room, [`runbooks/`](runbooks/), [`POSTMORTEM-TEMPLATE.md`](POSTMORTEM-TEMPLATE.md) | [Part 3](labs/03-slos-and-incidents.md) | ✅ |
| Ex 1 | Flask app | [`app/app.py`](../app/app.py) (`/`, `/store`, `/error`, `/ask`, `/inject`, `/metrics`) | [Part 1](labs/01-foundations.md) | ✅ |
| Ex 2 | Docker image | [`Dockerfile`](../Dockerfile) (non-root, Gunicorn), multi-arch build in CI | [Part 1](labs/01-foundations.md) | ✅ |
| Ex 3 | Push to a registry | [`cd.yml`](../.github/workflows/cd.yml): GHCR always, Docker Hub when its secrets exist | [Part 5](labs/05-automation-iac-cicd.md) | ✅ |
| Ex 4 | Kubernetes on Minikube | [`k8s/application.yaml`](../k8s/application.yaml), [`kustomization.yaml`](../k8s/kustomization.yaml) | [Part 1](labs/01-foundations.md) | ✅ |
| Ex 4.1 | Ansible IaC | [`ansible/site.yml`](../ansible/site.yml) | [Part 5](labs/05-automation-iac-cicd.md) | ✅ |
| Ex 5 | Prometheus | [`prometheus.yml`](../k8s/config/prometheus/prometheus.yml), [`alerts.yml`](../k8s/config/prometheus/alerts.yml) | [Part 2](labs/02-metrics-dashboards-alerts.md) | ✅ |
| Ex 6 | Grafana | [`k8s/config/grafana/`](../k8s/config/grafana/) (datasources, 4 dashboards as code) | [Part 2](labs/02-metrics-dashboards-alerts.md) | ✅ |
| Ex 7 | cAdvisor | `kubernetes-cadvisor` scrape job through the API server proxy | [Part 2](labs/02-metrics-dashboards-alerts.md) | ✅ |
| Ex 8 | OpenTelemetry tracing + Jaeger | App spans, [`otel-collector.yaml`](../k8s/config/otel-collector.yaml), Jaeger in [`observability.yaml`](../k8s/observability.yaml) | [Part 4](labs/04-logs-traces-llm.md) | ✅ |
| Ex 9 | Trace-based metrics | spanmetrics connector → Prometheus | [Part 4](labs/04-logs-traces-llm.md) | ✅ |
| Ex 10 | Logs with Loki | JSON logs with `trace_id`, OTLP → Loki | [Part 4](labs/04-logs-traces-llm.md) | ✅ |
| Ex 11 | Golden signals | *Golden Signals* dashboard (latency, traffic, errors, saturation, logs) | [Part 2](labs/02-metrics-dashboards-alerts.md) | ✅ |
| Ex 12 | Grafana alerting | [`alerting.yaml`](../k8s/config/grafana/alerting.yaml) (rules on traces and Loki, sent to Alertmanager) | [Part 2](labs/02-metrics-dashboards-alerts.md) | ✅ |
| Ex 13 | AWX incident automation | [`awx/`](../awx/), [`awx_setup.py`](../scripts/awx_setup.py): an alert launches read-only diagnostics | [Part 5](labs/05-automation-iac-cicd.md) | ✅ |
| Ex 14 | Helm | [`helm/sre-metrics-app`](../helm/sre-metrics-app/), kube-prometheus-stack values | [Part 5](labs/05-automation-iac-cicd.md) | ✅ |
| Ex 15 | Terraform | [`terraform/`](../terraform/) (workspaces → environments) | [Part 5](labs/05-automation-iac-cicd.md) | ✅ |
| Ex 16 | GitHub Actions CI/CD | [`ci.yml`](../.github/workflows/ci.yml), [`cd.yml`](../.github/workflows/cd.yml) | [Part 5](labs/05-automation-iac-cicd.md) | ✅ |
| Ex 17 | ArgoCD GitOps | [`gitops/`](../gitops/), [`gitops_setup.py`](../scripts/gitops_setup.py) | [Part 6](labs/06-delivery-resilience-policy.md) | ✅ |
| Ex 18 | Rolling updates and rollbacks | `RollingUpdate` strategy, [`rollout_demo.py`](../scripts/rollout_demo.py) | [Part 6](labs/06-delivery-resilience-policy.md) | ✅ |
| Ex 19 | Chaos engineering | [`chaos/`](../chaos/) (LitmusChaos + Argo Workflows), [`chaos_test.py`](../scripts/chaos_test.py) | [Part 6](labs/06-delivery-resilience-policy.md) | ✅ |

## New for 2027

| Module | Topic | Where | Lab | Status |
| --- | --- | --- | --- | --- |
| M16 | DORA metrics (all five, including deployment rework rate) | [`dora_metrics.py`](../scripts/dora_metrics.py) | [Part 5](labs/05-automation-iac-cicd.md) | ✅ |
| M17 | AI-assisted SRE with Claude Code and IBM Bob | [`AGENTS.md`](../AGENTS.md), [`CLAUDE.md`](../CLAUDE.md), [`.claude/`](../.claude/), [`.bob/`](../.bob/), [`AI-SRE.md`](AI-SRE.md) | [Part 7](labs/07-ai-assisted-sre.md) | ✅ |
| M18 | MCP safety and prompt injection | In-cluster Grafana MCP server ([`k8s/ai/`](../k8s/ai/)), Viewer token, `view` RBAC, guard hook, `/inject` drill | [Part 7](labs/07-ai-assisted-sre.md) | ✅ |
| M19 | Software supply chain security | SBOM (Syft), Trivy gate, cosign keyless signing, SLSA provenance in `cd.yml`; pip-audit and bandit in `ci.yml` | [Part 5](labs/05-automation-iac-cicd.md) | ✅ (pip-audit found real CVEs; app upgraded) |
| M20 | Policy as code | [`policy/`](../policy/) (Kyverno), [`policy_setup.py`](../scripts/policy_setup.py) | [Part 6](labs/06-delivery-resilience-policy.md) | ✅ |
| M21 | Progressive delivery gated by an SLO | [`progressive/`](../progressive/) (Argo Rollouts + Prometheus analysis), [`canary_demo.py`](../scripts/canary_demo.py) | [Part 6](labs/06-delivery-resilience-policy.md) | ✅ |
| M23 | LLM / GenAI observability | `/ask` with `gen_ai.*` span attributes, token metrics, *LLM Observability* dashboard | [Part 4](labs/04-logs-traces-llm.md) | ✅ |
| M27 | Capstone: AI-assisted game day | Combines chaos, canary, AI triage and a postmortem | [Part 7](labs/07-ai-assisted-sre.md) | 📘 |

## roadmap.sh DevOps roadmap coverage
Source: roadmap.sh's official DevOps roadmap data (last updated 2026-10-27).

| Roadmap area | Covered by | Status |
| --- | --- | --- |
| Programming language | Python (app, tests, every automation script) | ✅ |
| Operating system | Linux containers; macOS and Windows (WSL2) workstations | ✅ |
| Terminal (Bash, PowerShell, process and performance monitoring) | `scripts/*.sh` and `*.ps1`, `kubectl top`, cAdvisor | ✅ |
| Version control and VCS hosting | Git, GitHub (issues, PRs, Actions, Dependabot, Releases, GHCR) | ✅ |
| Containers | Docker, multi-arch images, non-root | ✅ |
| Proxies, load balancers, web servers | Kubernetes Services, Gunicorn | 📘 (no ingress controller, to save memory) |
| Networking and protocols (HTTP, TLS, DNS, SMTP) | Service DNS, HTTP probes, SMTP alerts, TLS via the API proxy | ✅ |
| Cloud providers / serverless | — | ➖ the lab runs fully on a laptop; Terraform and Helm port to EKS/AKS/GKE |
| Provisioning | Terraform | ✅ |
| Configuration management | Ansible, AWX | ✅ |
| CI/CD | GitHub Actions | ✅ |
| Secret management | Kubernetes Secrets from gitignored files, short-lived tokens, push protection | 📘 (Vault/Sealed Secrets suggested as an extension) |
| Infrastructure monitoring | Prometheus, Grafana, cAdvisor | ✅ |
| Logs management | Loki | ✅ |
| Container orchestration | Kubernetes (Minikube) | ✅ |
| Observability | OpenTelemetry, Jaeger, Prometheus | ✅ |
| Artifact management | GHCR, Docker Hub, Helm chart as a release asset | ✅ |
| GitOps | ArgoCD | ✅ |
| Service mesh | — | ➖ too heavy for an 8-16 GB laptop next to the stack; canary uses replica weights instead |
| Cloud design patterns (availability, management and monitoring) | Replicas, probes, rolling updates, canary, chaos, SLOs | ✅ |
