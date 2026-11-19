# SRE Academy lab guide

A complete, hands-on SRE course on one working stack, for **students** (follow the parts in order) and **professors** (each module has objectives, timing, self-checks, common problems and instructor notes; the self-check answers live in a private instructor answer key).

Before Part 1, students install the tools with the [step-by-step guide for Mac and Windows](../GUIDE.md), or let IBM Bob install them and guide the whole lab ([BOB-QUICKSTART.md](../BOB-QUICKSTART.md)). **On Windows with IBM Bob, use the PowerShell path and skip WSL:** type `python` (never `python3`, which opens the Microsoft Store) and run the `scripts\*.ps1` scripts.

**The lab is a journey: the Road to Junior SRE.** It is written for IBMers from non-technical teams who want to move into a technical role such as junior SRE, DevOps, cloud or operations. You are the new apprentice. Your first assignment is **Nimbus Store** (the demo app), a small online shop that went down for an hour last week and nobody noticed. With **Bob, your AI pair** (fast and helpful, but never allowed to change anything without your OK), you climb camp by camp from **Career Changer** to the summit **On-Call Ready**: the day a team trusts you with the pager.

Each module is a mission in [`lab/missions.json`](../../lab/missions.json) with XP, a short quiz and an automatic check (`python scripts\lab.py check <ID>` on Windows, `python3 scripts/lab.py check <ID>` on Mac/Linux) that looks for real evidence on your cluster or fork. Mission **B00 "Meet your AI partner"** comes first: it teaches how to work with IBM Bob (modes, approvals, `AGENTS.md`, slash commands) and ends with 5 quiz questions, including the "Stay in control" box.

| Camp | Name | What Nimbus gets | SRE principle |
| --- | --- | --- | --- |
| 0 | Orientation Day | You and Bob agree on the rules | Humans stay in control: automation and AI propose, people approve. |
| 1 | The Engine Room | Runs on Kubernetes, updates with zero downtime | Small, safe, repeatable changes. |
| 2 | The Watchtower | Metrics, dashboards and its first alarm | Monitor what users feel; alert only when a human must act. |
| 3 | The War Room | A reliability promise (SLO), an error budget, an incident process | Embrace risk with error budgets; learn from incidents without blame. |
| 4 | The Detective Agency | Logs and traces, even into an AI model | Explain any failure from evidence, not guesses. |
| 5 | The Robot Workshop | Rebuilt from code, tested on every change | Eliminate toil; keep infrastructure in code. |
| 6 | The Proving Grounds | Survives crashes and bad releases, refuses unsafe deployments | Changes are gradual, reversible and tested by breaking things on purpose. |
| 7 | The AI Command Center | Bob goes on call with you; you lead the final game day | Trust, but verify: least privilege and human judgement. |

Ranks by XP: Career Changer (0), Tech Apprentice (500), SRE Intern (1300), Junior SRE Candidate (2300), Interview-Ready Junior SRE (3300). Clearing a camp is a **LEVEL UP**: `lab.py` prints the camp's SRE principle, the skills you can now name on your CV and one interview question to rehearse. The [course map](../COURSE-MAP.md#camps-sre-principles-and-job-skills) lists the skills and questions of every camp.

**Your CV and interview practice.** `lab.py cv` lists the skills you have earned, the principles you practised and the interview questions of the camps you cleared. In Bob, `/my-cv` turns them into plain CV or LinkedIn lines (only what you really did in the lab, never invented experience), and `/interview` plays a friendly interviewer for a junior SRE or DevOps role and gives kind feedback. Mission Control (`lab.py play`) shows the same in its "Your CV so far" and "Interview practice" panels. Parts 2, 3, 5, 6 and 7 end with an **Interview corner**; `/interview` covers every camp you cleared. Be honest with yourself and with recruiters: this lab gives you hands-on evidence for junior roles; it does not make you a senior engineer.

**Optional portfolio projects, open to everyone.** Four extra missions you design yourself, to show in an interview:

| Project | What you build | Where |
| --- | --- | --- |
| P-DASH | Your own Grafana dashboard | [Part 2](02-metrics-dashboards-alerts.md#portfolio-project-p-dash-your-own-dashboard) |
| P-RUNBOOK | A new runbook, linked from an alert's `runbook_url` | [Part 3](03-slos-and-incidents.md#portfolio-project-p-runbook-a-new-runbook) |
| P-ENV | A second `dev` environment with a Terraform workspace | [Part 5](05-automation-iac-cicd.md#portfolio-project-p-env-a-second-environment-from-code) |
| P-POLICY | A new Kyverno ClusterPolicy | [Part 6](06-delivery-resilience-policy.md#portfolio-project-p-policy-a-new-guardrail-policy) |

**For professors.** `python3 scripts/cohort_report.py <folder of the students' evidence.json files>` (Windows: `python scripts\cohort_report.py ...`) gives a class summary: how many students reached On-Call Ready, the missions most skipped (topics to reteach) and a fingerprint check. Students finish with `lab.py proof --name "<name>"`, which writes a **self-generated** passport with a skills section, a badge and an evidence file with an integrity fingerprint (not a signature) to `lab-proof/`. The passport is a record, not a certificate or proof: professors confirm cluster-side missions in a short live check-off with `lab.py verify`.

| Part | Modules | Time | Memory |
| --- | --- | --- | --- |
| [1. Foundations](01-foundations.md) | M00 setup · M01 instrumentation · M02 Kubernetes deployment | ~5.5 h | core stack |
| [2. Metrics, dashboards and alerts](02-metrics-dashboards-alerts.md) | M03 Prometheus · M04 Grafana · M05 Alertmanager and Grafana alerting | ~4 h | core stack |
| [3. SLOs, synthetic checks and incidents](03-slos-and-incidents.md) | M06 SLOs · M08 synthetic and container signals · M09 incident response, ORR, GitHub | ~5.5 h | core stack |
| [4. Logs, traces and LLM observability](04-logs-traces-llm.md) | M07 OpenTelemetry, Jaeger, Loki · M23 GenAI telemetry | ~2.5 h | core stack |
| [5. Automation, IaC and CI/CD](05-automation-iac-cicd.md) | M10 Ansible and AWX · M11 Terraform and Helm · M09b join the guild (fork the repo; steps in [Part 3](03-slos-and-incidents.md#m09b-github-issues-pull-requests-and-projects-for-sre-work)) · M12 GitHub Actions · M16 DORA · M19 supply chain | ~12 h | AWX: +2.5 GB |
| [6. GitOps, resilience and guardrails](06-delivery-resilience-policy.md) | M13 ArgoCD · M14 rollbacks · M15 chaos · M20 Kyverno · M21 canary | ~12 h | one add-on at a time |
| [7. AI-assisted SRE](07-ai-assisted-sre.md) | M17 AI on call with IBM Bob (Claude Code optional) · M18 MCP safety · optional instructor demo: observing the agents (not a graded mission) · M27 capstone game day | ~10 h | +0.05 GB |

**Mapping to the 2026 course:** see the [course map](../COURSE-MAP.md) (every topic 0-6 and exercise 1-19, plus the roadmap.sh DevOps areas).

## Laptop profiles
- **8 GB laptop:** Minikube with 4 GB (the deploy script's default). Core stack only. The add-on modules (AWX in M10, and ArgoCD, chaos tools, Kyverno and Argo Rollouts in Part 6) need the 16 GB profile. On 8 GB, watch the instructor demo or pair with a 16 GB machine. For evidence, submit the instructor run's output plus your written self-check answers.
- **16 GB laptop:** create a 6 GB Minikube before `./scripts/deploy.sh`: `minikube delete` (only if a cluster already exists, because `minikube start` cannot change the memory of an existing cluster), then `minikube start --driver=docker --memory=6144` (Part 1, M00 step 4). On a Mac, run `colima stop && colima start --cpu 4 --memory 8` first. Core stack plus any single add-on, AWX included.

## How the verification was done
The author ran the add-ons and scripts of this lab end to end on a local Minikube cluster in November 2026. The expected results quoted in the parts come from those runs. The run logs are not stored in this repository. Delivery of alerts to Slack or email is not checked yet, because it needs the author's own webhook or SMTP account. Versions are pinned in the files; when a pinned image disappears (it happened with the AWX operator's `kube-rbac-proxy`), the fix is documented where it applies.

## Suggested assessment
- **Quizzes and self-checks are formative.** They help students learn and **never count toward a grade**. The XP they give is for motivation only. The answer keys are not in this repository: see [docs/instructor/README.md](../instructor/README.md).
- **Weekly:** the evidence listed in each part's instructor notes (screenshots, generated reports), confirmed in a short live check-off with `lab.py verify`.
- **Final project:** this repository is the reference solution for the six requirements and three bonuses (see the [README](../../README.md#final-project-requirements)), so a clone alone earns no credit. Each student, working in their fork, adds one new endpoint to `app/app.py` with a unit test in `tests/`, an SLI recording rule and an SLO alert with `runbook_url` in `k8s/config/prometheus/slo.yml`, one Grafana panel for it, a runbook in `docs/runbooks/`, and a one-page ORR for the change. CI (`ci.yml`) must pass on the pull request in their fork. Pass criteria: the alert fires in Alertmanager during a provoked failure (screenshot), and `pytest tests -q` and `flake8` pass.
- **Capstone:** the AI-assisted game day (Part 7, M27), graded on the postmortem, the TTD/TTA/TTR numbers and the "what the AI got wrong" log.
- **Suggested weighting:** weekly evidence 40%, final project 30%, capstone 30%. Each item is pass/fail against the evidence listed for it. Quiz scores and XP are not part of the grade.
