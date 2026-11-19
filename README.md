# SRE Academy Mega Lab

[![CI](https://github.com/jaffethalfarotorres/sre-final-project/actions/workflows/ci.yml/badge.svg)](https://github.com/jaffethalfarotorres/sre-final-project/actions/workflows/ci.yml)
[![CD](https://github.com/jaffethalfarotorres/sre-final-project/actions/workflows/cd.yml/badge.svg)](https://github.com/jaffethalfarotorres/sre-final-project/actions/workflows/cd.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE.md)
[![Python 3.10](https://img.shields.io/badge/Python-3.10-3776AB.svg?logo=python&logoColor=white)](app/app.py)
[![Runs on Mac and Windows](https://img.shields.io/badge/runs%20on-macOS%20%7C%20Windows%20(WSL2)-informational)](docs/GUIDE.md)

**In plain words:** this project runs a small pretend online shop on your laptop, measures how healthy it is, shows the measurements as live charts, raises an alarm in Slack or email when something goes wrong, and lets you practise what Site Reliability Engineers do next: investigate, roll back, automate the fix and learn from the incident, now including AI assistants that help without being allowed to break anything.

It started as my SRE Academy 2026 final project and grew into a **complete, reusable lab**. It covers every topic and exercise of the 2026 course on one working stack, adds the topics a 2027 class needs (AI-assisted operations with Claude Code and IBM Bob, MCP safety, supply chain security, policy as code, canary releases, DORA metrics, LLM observability), and comes with a lab guide that professors can teach from.

> **New to this?** Start with the [step-by-step guide for Mac and Windows](docs/GUIDE.md). No Kubernetes experience needed.
> **Teaching it?** Go to the [lab guide](docs/labs/README.md) and the [course map](docs/COURSE-MAP.md).

## What you get

```mermaid
flowchart LR
    TG[Traffic generator] -->|/store, /ask| APP[Python Flask app<br/>metrics · traces · JSON logs]
    BB[Blackbox exporter<br/>synthetic checks] --> APP
    APP -->|OTLP| OTEL[OpenTelemetry Collector]
    OTEL --> JAEGER[Jaeger<br/>traces]
    OTEL --> LOKI[Loki<br/>logs]
    OTEL -->|span metrics| PROM
    PROM[Prometheus<br/>alerts + SLO rules] -->|scrape| APP
    PROM -->|scrape| CADV[cAdvisor]
    PROM --> AM[Alertmanager]
    GRAF[Grafana<br/>4 dashboards + alert rules] --> PROM & LOKI & JAEGER
    GRAF --> AM
    AM --> SLACK[Slack / email]
    AM -->|critical| AWX[AWX runbook:<br/>collect diagnostics]
    AI[Claude Code / IBM Bob] -->|read-only MCP| MCP[Grafana MCP server] --> GRAF
```

| Area | What is in the repository |
| --- | --- |
| **App** | Flask service with Prometheus metrics, OpenTelemetry traces, JSON logs with trace IDs, a GenAI demo endpoint and a prompt-injection drill ([`app/app.py`](app/app.py)) |
| **Observability** | Prometheus, Grafana, Alertmanager, Loki, Jaeger, OpenTelemetry Collector, blackbox exporter, cAdvisor; all config as code under [`k8s/`](k8s/) |
| **Reliability** | SLOs with multi-window burn-rate alerts, runbooks, incident process, postmortem template, ORR ([`docs/`](docs/)) |
| **Automation** | Ansible playbooks and AWX, Terraform, Helm, Kustomize |
| **Delivery** | GitHub Actions CI/CD, ArgoCD GitOps, rolling updates and rollback, Argo Rollouts canary gated by the SLO |
| **Resilience and guardrails** | LitmusChaos experiments, Kyverno policies, SBOM, image scanning and signing |
| **AI-assisted SRE** | Shared [`AGENTS.md`](AGENTS.md) for Claude Code and IBM Bob, read-only MCP access, guard hooks, injection drill ([`docs/AI-SRE.md`](docs/AI-SRE.md)) |

## Quick start

On a **Mac** (Homebrew + Colima) or **Windows** (WSL2 + Ubuntu), with Docker, Minikube and kubectl installed ([guide, step 2](docs/GUIDE.md#2-install-the-tools-one-time)):

```bash
git clone https://github.com/jaffethalfarotorres/sre-final-project.git
cd sre-final-project
./scripts/deploy.sh          # builds the app and deploys the whole stack (5-10 minutes the first time)
./scripts/dashboards.sh      # opens Grafana, Prometheus, Alertmanager, Jaeger and the app
./scripts/trigger-alert.sh   # in another window: makes a real alert fire in about 2.5 minutes
```

No accounts or credentials are needed. Using Docker Desktop with PowerShell on Windows? Every script also exists as `scripts\*.ps1` (run them with `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\deploy.ps1`).

## The lab path

| Part | Modules | Course coverage |
| --- | --- | --- |
| [1. Foundations](docs/labs/01-foundations.md) | Setup, instrumentation, Docker, Kubernetes | Ex 1-4 |
| [2. Metrics, dashboards and alerts](docs/labs/02-metrics-dashboards-alerts.md) | Prometheus, Grafana, Alertmanager, Grafana alerting, golden signals | Ex 5-7, 11, 12 |
| [3. SLOs and incidents](docs/labs/03-slos-and-incidents.md) | SLOs and error budgets, synthetic checks, incident response, ORR, GitHub | Topics 0-6 |
| [4. Logs, traces and LLM observability](docs/labs/04-logs-traces-llm.md) | OpenTelemetry, Jaeger, Loki, GenAI telemetry | Ex 8-10 + new |
| [5. Automation, IaC and CI/CD](docs/labs/05-automation-iac-cicd.md) | Ansible, AWX, Terraform, Helm, GitHub Actions, DORA, supply chain | Ex 4.1, 13-16 + new |
| [6. GitOps, resilience and guardrails](docs/labs/06-delivery-resilience-policy.md) | ArgoCD, rollbacks, chaos, Kyverno, canary | Ex 17-19 + new |
| [7. AI-assisted SRE](docs/labs/07-ai-assisted-sre.md) | Claude Code and IBM Bob, MCP safety, injection drill, game day | New in 2027 |

Every 2026 topic and exercise, and the roadmap.sh DevOps areas, are mapped to files in the [course map](docs/COURSE-MAP.md).

## Optional add-ons (one at a time)
The core stack uses about 3.5 GB. `./scripts/deploy.sh` creates a 4 GB Minikube, which is enough for the core stack only. For the add-ons (16 GB laptop), first create a 6 GB cluster with `minikube start --driver=docker --memory=6144` (run `minikube delete` first if a cluster already exists, because `minikube start` cannot change the memory of an existing cluster; on a Mac, run `colima stop && colima start --cpu 4 --memory 8` first), then run `./scripts/deploy.sh`. Run one add-on, then remove it before the next. On an 8 GB laptop, stay with the core stack.

| Add-on | Command | Extra memory | What it proves (verified) |
| --- | --- | --- | --- |
| ArgoCD | `python3 scripts/gitops_setup.py` | ~0.8 GB | Synced from GitHub; a manual change is reverted in ~5 s |
| Chaos | `python3 scripts/chaos_test.py` | ~0.5 GB | Pods killed for 30 s, the app kept answering, verdict Pass |
| Canary | `python3 scripts/canary_demo.py` | ~0.4 GB | Good release promoted; bad release stopped at 25% and rolled back |
| Kyverno | `python3 scripts/policy_setup.py` | ~0.5 GB | A non-compliant pod is rejected with 3 policy messages |
| AWX | `python3 scripts/awx_setup.py` | ~2.5 GB | A critical alert launches the diagnostics runbook ~14 s later |
| AI access | `python3 scripts/ai_setup.py` | ~0.05 GB | MCP server (about 60 tools, Grafana writes refused by a Viewer token) and a kubeconfig that cannot delete |
| Bad release | `python3 scripts/rollout_demo.py` | none | Users kept being served; rollback in ~1 s |
| Terraform | `cd terraform && terraform init && terraform apply` | ~0.2 GB | A staging copy of the app created and destroyed from code |

## Final project requirements

| Requirement | Implementation |
| --- | --- |
| 1. Application | Python Flask app emitting metrics, traces and logs ([`app/app.py`](app/app.py)); 61 automated tests for the app and the AI guard hook |
| 2. Kubernetes | Minikube, Kustomize, 2 replicas, probes, limits, non-root, rolling updates |
| 3. Prometheus | Pod discovery by annotation, cAdvisor, blackbox and span-metric jobs; 5 alert rules + 16 SLO rules |
| 4. Grafana | 4 provisioned dashboards: overview, golden signals, SLO and error budget, LLM observability |
| 5. Alertmanager | Severity routing to Slack, email and AWX; Grafana alerts flow through the same routes |
| 6. Documentation | This README, a beginner guide, 7 lab parts, runbooks, SLO/ORR/incident docs, [`LICENSE.md`](LICENSE.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), screenshots |
| Bonus: notifications | Slack and email receivers ([`k8s/alertmanager.yaml`](k8s/alertmanager.yaml)); setup in [guide section 6](docs/GUIDE.md#6-optional-get-alerts-in-slack-and-email) |
| Bonus: IaC | Helm, Terraform, Ansible, Kustomize |
| Bonus: CI/CD | CI: tests, security scans, config validation, multi-arch build, scripts checked on Linux, macOS and Windows. CD: GHCR, SBOM, vulnerability gate, signing, provenance, Helm chart release |

## Evidence

Screenshots of the working deployment are in [`docs/screenshots/`](docs/screenshots/).

**All pods running** · **Prometheus target UP** · **Grafana dashboard with live data**

![All pods running](docs/screenshots/pods.png)
![Prometheus targets](docs/screenshots/prometheus-targets.png)
![Grafana dashboard](docs/screenshots/grafana-dashboard.png)

**Prometheus alerts** · **Alertmanager with a firing `HighErrorRate`** · **Helm deployment**

![Prometheus alerts](docs/screenshots/prometheus-alerts.png)
![Alertmanager alerts](docs/screenshots/alertmanager-alert.png)
![Helm deployment](docs/screenshots/helm-deployment.png)

## Repository layout

```
app/            Flask service (metrics, traces, logs, /ask GenAI demo, /inject drill)
k8s/            Kustomize stack: manifests + config/ (Prometheus, Grafana, Collector, Loki), ai/, drills/
helm/           App chart + kube-prometheus-stack values (alternative install: ./scripts/deploy.sh --helm)
ansible/        Deploy playbook and incident runbooks      awx/        AWX operator, instance, RBAC
terraform/      Staging environment as code                 gitops/     ArgoCD project and application
chaos/          LitmusChaos experiment as an Argo Workflow  policy/     Kyverno policies
progressive/    Argo Rollouts canary + SLO analysis         scripts/    One-command tools (bash, PowerShell, Python)
docs/           Guide, lab parts, SLO, ORR, incident response, runbooks, course map
.claude/ .bob/  AI assistant configuration (shared rules in AGENTS.md)
```

## CI/CD
- **CI** on every push and pull request: flake8 and pytest, bandit and pip-audit, Kustomize/Helm/kubeconform, promtool, amtool, Collector and Loki config checks, Terraform and Ansible (production lint profile), a multi-arch image build, and the scripts checked on Linux, macOS (bash 3.2) and Windows (PowerShell).
- **CD** on a version tag (`v1.0.0`): image pushed to GHCR (and Docker Hub if its secrets exist), SBOM, Trivy gate, cosign signature, SLSA provenance, a kind smoke test and the Helm chart attached to the GitHub Release.

## Clean up

```bash
kubectl delete namespace application monitoring opentelemetry
minikube stop        # or: minikube delete
```

## Notes
A teaching lab: data is not persisted, and every credential is local and short-lived. Keep real webhook URLs and passwords out of Git; only `*.example.yaml` Secret files are tracked.

## License
MIT, see [`LICENSE.md`](LICENSE.md). Contributions are welcome, see [`CONTRIBUTING.md`](CONTRIBUTING.md).
