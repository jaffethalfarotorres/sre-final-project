# SRE Academy lab guide

A complete, hands-on SRE course on one working stack, for **students** (follow the parts in order) and **professors** (each module has objectives, timing, self-checks with answers, common problems and instructor notes).

Before Part 1, students install the tools with the [step-by-step guide for Mac and Windows](../GUIDE.md), or let IBM Bob install them and guide the whole lab ([BOB-QUICKSTART.md](../BOB-QUICKSTART.md)).

**The lab is a game.** Each module is a mission in [`lab/missions.json`](../../lab/missions.json) with XP, a short quiz and an automatic check (`python3 scripts/lab.py check <ID>`) that looks for real evidence on the student's cluster or fork. Mission **B00 "Meet your AI partner"** comes first and teaches how to work with IBM Bob (modes, approvals, `AGENTS.md`, slash commands). Students finish with `python3 scripts/lab.py proof --name "<name>"`, which writes a passport, a badge and a hashed evidence file to `lab-proof/`. Professors can grade from that passport plus the evidence listed in each part's instructor notes.

| Part | Modules | Time | Memory |
| --- | --- | --- | --- |
| [1. Foundations](01-foundations.md) | M00 setup · M01 instrumentation · M02 Kubernetes deployment | ~5.5 h | core stack |
| [2. Metrics, dashboards and alerts](02-metrics-dashboards-alerts.md) | M03 Prometheus · M04 Grafana · M05 Alertmanager and Grafana alerting | ~4 h | core stack |
| [3. SLOs, synthetic checks and incidents](03-slos-and-incidents.md) | M06 SLOs · M08 synthetic and container signals · M09 incident response, ORR, GitHub | ~5.5 h | core stack |
| [4. Logs, traces and LLM observability](04-logs-traces-llm.md) | M07 OpenTelemetry, Jaeger, Loki · M23 GenAI telemetry | ~2.5 h | core stack |
| [5. Automation, IaC and CI/CD](05-automation-iac-cicd.md) | M10 Ansible and AWX · M11 Terraform and Helm · M12 GitHub Actions · M16 DORA · M19 supply chain | ~12 h | AWX: +2.5 GB |
| [6. GitOps, resilience and guardrails](06-delivery-resilience-policy.md) | M13 ArgoCD · M14 rollbacks · M15 chaos · M20 Kyverno · M21 canary | ~12 h | one add-on at a time |
| [7. AI-assisted SRE](07-ai-assisted-sre.md) | M17 Claude Code and IBM Bob · M18 MCP safety · M24 agent telemetry · M27 capstone game day | ~10 h | +0.05 GB |

**Mapping to the 2026 course:** see the [course map](../COURSE-MAP.md) (every topic 0-6 and exercise 1-19, plus the roadmap.sh DevOps areas).

## Laptop profiles
- **8 GB laptop:** Minikube with 4 GB (the deploy script's default). Core stack only. The add-on modules (AWX in M10, and ArgoCD, chaos tools, Kyverno and Argo Rollouts in Part 6) need the 16 GB profile. On 8 GB, watch the instructor demo or pair with a 16 GB machine. For evidence, submit the instructor run's output plus your written self-check answers.
- **16 GB laptop:** create a 6 GB Minikube before `./scripts/deploy.sh`: `minikube delete` (only if a cluster already exists, because `minikube start` cannot change the memory of an existing cluster), then `minikube start --driver=docker --memory=6144` (Part 1, M00 step 4). On a Mac, run `colima stop && colima start --cpu 4 --memory 8` first. Core stack plus any single add-on, AWX included.

## How the verification was done
Every add-on and script in this lab was run end to end on a Minikube cluster on 2026-11-18/19, and the expected results quoted in the parts come from those runs. Versions are pinned in the files; when a pinned image disappears (it happened with the AWX operator's `kube-rbac-proxy`), the fix is documented where it applies.

## Suggested assessment
- **Weekly:** the self-check questions of each part, and the evidence listed in its instructor notes (screenshots, generated reports).
- **Final project:** this repository is the reference solution for the six requirements and three bonuses (see the [README](../../README.md#final-project-requirements)), so a clone alone earns no credit. Each student, working in their fork, adds one new endpoint to `app/app.py` with a unit test in `tests/`, an SLI recording rule and an SLO alert with `runbook_url` in `k8s/config/prometheus/slo.yml`, one Grafana panel for it, a runbook in `docs/runbooks/`, and a one-page ORR for the change. CI (`ci.yml`) must pass on the pull request in their fork. Pass criteria: the alert fires in Alertmanager during a provoked failure (screenshot), and `pytest tests -q` and `flake8` pass.
- **Capstone:** the AI-assisted game day (Part 7, M27), graded on the postmortem, the TTD/TTA/TTR numbers and the "what the AI got wrong" log.
- **Suggested weighting:** weekly self-checks and evidence 40%, final project 30%, capstone 30%. Each item is pass/fail against the evidence listed for it.
