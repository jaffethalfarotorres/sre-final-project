# Course map

Where every SRE Academy topic, every new 2027 topic and every roadmap.sh DevOps area is implemented in this repository. ✅ = implemented and verified live on Minikube; 📘 = documented or covered by an exercise; ➖ = out of scope for a laptop lab (with the reason).

**Start with the shift.** For a student, this repository is first an ice-breaker: the **[First on-call shift](labs/README.md#the-first-on-call-shift-one-sitting)**, one sitting of about 2 to 3 hours with IBM Bob, not graded. The table below shows what the shift touches. Everything after it, including the full topic mapping, is optional material to go deeper.

<a id="the-first-on-call-shift"></a>
## The first on-call shift (journey `first-shift`)

| # | Mission | Minutes | Camp | 2026 course items it touches | Skill the student touches |
| --- | --- | --- | --- | --- | --- |
| 1 | B00 Meet your AI partner | 15 | 0 Orientation Day | New for 2027 | Working safely with an AI assistant; approving commands before they run |
| 2 | M00 Boot the lab | 60 | 1 The Engine Room | Ex 1, Ex 2, Ex 4 (the app, its image and Kubernetes on Minikube, deployed by `scripts/deploy.*`) | Running a real stack on a laptop |
| 3 | M01 Instrument a service | 10 | 1 The Engine Room | Ex 1 (metrics, traces, logs from the Flask app) | What a service tells you about itself |
| 4 | M04 Dashboards as code | 10 | 2 The Watchtower | Ex 6, Ex 11 (Grafana, golden signals) | Reading a dashboard |
| 5 | M05 First alert | 15 | 2 The Watchtower | Ex 5, Ex 12 (alert rules, Alertmanager) | Knowing a service is unhealthy before users call |
| 6 | N01 Alerts on your phone | 10 | 2 The Watchtower | Bonus: external notifications (ntfy receiver in Alertmanager) | Getting paged outside the cluster |
| 7 | M07 Follow the trace | 10 | 4 The Detective Agency | Ex 8, Ex 10 (OpenTelemetry, Jaeger, Loki) | Explaining a failure from evidence |
| 8 | M17 AI on call | 20 | 7 The AI Command Center | New for 2027 | AI-assisted triage with read-only access |
| 9 | M18 Injection proof | 15 | 7 The AI Command Center | New for 2027 | Spotting prompt injection; least privilege for AI |
| | **Total** | **about 165** | | | Badge: **First On-Call Shift** |

The minutes are planning estimates, not measurements of a real class.

## Optional: the full climb and the course mapping

The rest of this page is the optional "go deeper" material. The longer student-facing lab is the **Road to Junior SRE** (see the [README](../README.md) and the [lab guide](labs/README.md)). It is written for IBMers from non-technical teams who want to move into technical roles such as junior SRE, DevOps, cloud or operations. Their first assignment as an apprentice is **Nimbus Store**, a small online shop that went down for an hour last week and nobody noticed. With **Bob, their AI pair** (fast and helpful, never allowed to change anything without the student's OK), they climb camp by camp (zones 0-7) from **Career Changer** to the summit **On-Call Ready**. The story is a wrapper only. Every module below keeps its professional name and its course mapping.

Ranks by XP: Career Changer (0), Tech Apprentice (500), SRE Intern (1300), Junior SRE Candidate (2300), Junior SRE Lab Graduate (3300). Everyone follows the same lab, and there is no bonus XP: one lab covers everything.

## Camps, SRE principles and job skills

Each camp gives Nimbus a real capability and teaches one SRE principle. When a student clears a camp, `lab.py` prints a LEVEL UP with the principle, the new CV skills and one interview question. `lab.py cv` lists them all, and Bob's `/my-cv` and `/interview` commands help the student use them. The source of truth is [`lab/missions.json`](../lab/missions.json) (`zones`); the table below is a summary.

| Camp | Name | Missions | SRE principle | Skills for the CV | Interview question |
| --- | --- | --- | --- | --- | --- |
| 0 | Orientation Day | B00 | Humans stay in control: automation and AI propose, people approve. | Working safely with an AI coding assistant (IBM Bob); reviewing and approving commands before they run | How do you make sure an AI assistant does not break production? |
| 1 | The Engine Room | M00, M01, M02 | Reliability starts with how you run software: small, safe, repeatable changes. | Docker containers; Kubernetes basics (pods, deployments, services, probes); zero-downtime rolling updates | What is the difference between a container and a pod? |
| 2 | The Watchtower | M03, M04, M05, N01 | Monitor what users feel, and alert only when a human must act. | Prometheus metrics and PromQL; Grafana dashboards as code; alerting with Alertmanager | How would you know a service is unhealthy before customers call? |
| 3 | The War Room | M06, M08, M09, P-RUNBOOK | Embrace risk with SLOs and error budgets, and learn from every incident without blame. | SLIs, SLOs and error budgets; synthetic monitoring; incident response and blameless postmortems | What is an error budget, and how does it change what the team does? |
| 4 | The Detective Agency | M07, M23, P-DASH | Observability: you can explain any failure from evidence, not guesses. | Centralized logs (Loki, LogQL); distributed tracing (OpenTelemetry, Jaeger); monitoring AI model calls | A request is slow. How do you find which step is slow? |
| 5 | The Robot Workshop | M10, M10X, M11, M09b, M12, M16, M19, P-ENV | Eliminate toil: automate repetitive work and keep infrastructure in code. | Automation with Ansible; infrastructure as code with Terraform; CI/CD with GitHub Actions; DORA delivery metrics | Why should infrastructure be written as code? |
| 6 | The Proving Grounds | M13, M14, M15, M20, M21, P-POLICY | Release engineering: changes are gradual, reversible and tested by breaking things on purpose. | Rollbacks; GitOps with ArgoCD; chaos engineering; canary releases; policy as code (Kyverno) | A release breaks production. What do you do in the first five minutes? |
| 7 | The AI Command Center | M17, M18, M27 | Trust, but verify: AI helps on call only with least privilege and human judgement. | AI-assisted incident triage; prompt-injection awareness; least privilege for AI agents; leading a game day | How would you use AI on call without giving it the keys to production? |

Add-on missions (M10X, M13, M15, M19, M20, M21) need extra memory and are optional. The four portfolio projects (P-DASH, P-ENV, P-RUNBOOK, P-POLICY) are optional for everyone; they are pieces a student can show in an interview. The lab gives hands-on evidence for junior roles. It does not make anyone a senior engineer.

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
| B00 | Working with an AI partner (IBM Bob guided lab, game engine, 5 quiz questions with the "Stay in control" box, self-generated passport confirmed by a live `lab.py verify`) | [`BOB-QUICKSTART.md`](BOB-QUICKSTART.md), [`.bob/`](../.bob/), [`scripts/lab.py`](../scripts/lab.py), [`lab/missions.json`](../lab/missions.json) | [Lab guide](labs/README.md) | ✅ |
| N01 | Alerts on your phone: `scripts/notify_setup.py` sends a real `[firing]` push from Alertmanager to the free ntfy app or a browser (core mission, part of the first on-call shift; check `phone_push`) | [`notify_setup.py`](../scripts/notify_setup.py), [`k8s/alertmanager.yaml`](../k8s/alertmanager.yaml) | [GUIDE 6-0](GUIDE.md#6-0-phone-push-with-ntfy-recommended-on-ibm-laptops-no-account) | 📘 |
| M09b | Join the guild (fork the repo): make your own fork and work in it (core mission, before M12; check `fork_origin`) | GitHub fork, `gh auth login`, [`scripts/lab.py`](../scripts/lab.py) | Steps in [Part 3, M09b](labs/03-slos-and-incidents.md#m09b-github-issues-pull-requests-and-projects-for-sre-work); counted in Part 5 | 📘 |
| M16 | DORA metrics (all five, including deployment rework rate) | [`dora_metrics.py`](../scripts/dora_metrics.py) | [Part 5](labs/05-automation-iac-cicd.md) | ✅ |
| M17 | AI on call with IBM Bob (Claude Code optional), read-only triage saved with `/save-triage` | [`AGENTS.md`](../AGENTS.md), [`CLAUDE.md`](../CLAUDE.md), [`.claude/`](../.claude/), [`.bob/`](../.bob/), [`AI-SRE.md`](AI-SRE.md) | [Part 7](labs/07-ai-assisted-sre.md) | ✅ |
| M18 | MCP safety and prompt injection | In-cluster Grafana MCP server ([`k8s/ai/`](../k8s/ai/)), Viewer token, `view` RBAC, guard hook, `/inject` drill | [Part 7](labs/07-ai-assisted-sre.md) | ✅ |
| M19 | Software supply chain security | SBOM (Syft), Trivy gate, cosign keyless signing, SLSA provenance in `cd.yml`; pip-audit and bandit in `ci.yml` | [Part 5](labs/05-automation-iac-cicd.md) | ✅ (pip-audit found real CVEs; app upgraded) |
| M20 | Policy as code | [`policy/`](../policy/) (Kyverno), [`policy_setup.py`](../scripts/policy_setup.py) | [Part 6](labs/06-delivery-resilience-policy.md) | ✅ |
| M21 | Progressive delivery gated by an SLO | [`progressive/`](../progressive/) (Argo Rollouts + Prometheus analysis), [`canary_demo.py`](../scripts/canary_demo.py) | [Part 6](labs/06-delivery-resilience-policy.md) | ✅ |
| M23 | LLM / GenAI observability | `/ask` with `gen_ai.*` span attributes, token metrics, *LLM Observability* dashboard | [Part 4](labs/04-logs-traces-llm.md) | ✅ |
| M27 | Capstone: AI-assisted game day | Combines chaos, canary, AI triage and a postmortem | [Part 7](labs/07-ai-assisted-sre.md) | 📘 |
| P-DASH | Portfolio project (optional, open to everyone): design and provision your own Grafana dashboard | [`k8s/config/grafana/`](../k8s/config/grafana/) | [Part 2](labs/02-metrics-dashboards-alerts.md) | 📘 |
| P-ENV | Portfolio project (optional, open to everyone): a second `dev` environment with a Terraform workspace | [`terraform/`](../terraform/) | [Part 5](labs/05-automation-iac-cicd.md) | 📘 |
| P-RUNBOOK | Portfolio project (optional, open to everyone): a new runbook, linked from an alert's `runbook_url` | [`docs/runbooks/`](runbooks/), [`alerts.yml`](../k8s/config/prometheus/alerts.yml) | [Part 3](labs/03-slos-and-incidents.md) | 📘 |
| P-POLICY | Portfolio project (optional, open to everyone): a new Kyverno ClusterPolicy with a pod it rejects | [`policy/`](../policy/) | [Part 6](labs/06-delivery-resilience-policy.md) | 📘 |
| CV and interview | `lab.py cv` (skills earned, principles practised, interview questions of cleared camps), Bob's `/my-cv` and `/interview`, the skills section in the passport | [`scripts/lab.py`](../scripts/lab.py), [`.bob/commands/`](../.bob/commands/) | [Lab guide](labs/README.md) | 📘 |
| Cohort report | Class summary for professors: how many students are On-Call Ready, the missions most skipped (topics to reteach), fingerprint check | [`scripts/cohort_report.py`](../scripts/cohort_report.py) (reads a folder of the students' `evidence.json`) | [Lab guide](labs/README.md) | 📘 |

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
