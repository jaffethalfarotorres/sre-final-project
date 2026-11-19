# SRE Academy lab guide

An SRE ice-breaker on one working stack. Students start with **[the First on-call shift](#the-first-on-call-shift-one-sitting)**: one sitting of about 2 to 3 hours, guided by IBM Bob, not graded. Everything after it is optional material to **[go deeper, at your own pace](#go-deeper-at-your-own-pace)**, with objectives, timing, self-checks, common problems and instructor notes in each module. Each self-check has its answers right below it, in a collapsed **Answers** block (labelled "try first" in most parts and "instructors" in Parts 2 and 4). Try the questions first, then open the block. Self-checks are for learning and never count toward a grade, so the answers are not secret: an AI assistant can read them too.

**Before the shift, run the preflight:** `python scripts\preflight.py` (Windows PowerShell) or `python3 scripts/preflight.py` (Mac, Linux, Ubuntu in WSL). It only reads your laptop and prints PASS, WARN, TODO or FAIL with a fix for each line. On an IBM-managed laptop, send [IT-REQUEST.md](../IT-REQUEST.md) to IT two weeks before class. Then students install the tools with the [step-by-step guide for Mac and Windows](../GUIDE.md), or let IBM Bob install them and guide the shift ([BOB-QUICKSTART.md](../BOB-QUICKSTART.md)). **On Windows with IBM Bob, use the PowerShell path and skip WSL:** type `python` (never `python3`, which opens the Microsoft Store) and run the `scripts\*.ps1` scripts.

**The story.** The shift is the first stretch of a longer, optional climb, the **Road to Junior SRE**. It is written for IBMers from non-technical teams who want to move into a technical role such as junior SRE, DevOps, cloud or operations. You are the new apprentice. Your first assignment is **Nimbus Store** (the demo app), a small online shop that went down for an hour last week and nobody noticed. With **Bob, your AI pair** (fast and helpful, but never allowed to change anything without your OK), you climb camp by camp from **Career Changer** to the summit **On-Call Ready**: the day a team trusts you with the pager.

Each module is a mission in [`lab/missions.json`](../../lab/missions.json) with XP, a short quiz and an automatic check (`python scripts\lab.py check <ID>` in Windows PowerShell; `python3 scripts/lab.py check <ID>` on Mac, Linux and in the Ubuntu window of WSL) that looks for real evidence on your cluster or fork. Mission **B00 "Meet your AI partner"** comes first: it teaches how to work with IBM Bob (modes, approvals, `AGENTS.md`, slash commands) and ends with 5 quiz questions, including the "Stay in control" box.

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

Ranks by XP: Career Changer (0), Tech Apprentice (500), SRE Intern (1300), Junior SRE Candidate (2300), Junior SRE Lab Graduate (3300). Clearing a camp is a **LEVEL UP**: `lab.py` prints the camp's SRE principle, the skills you can now name on your CV and one interview question to rehearse. The [course map](../COURSE-MAP.md#camps-sre-principles-and-job-skills) lists the skills and questions of every camp.

**Your CV and interview practice.** `lab.py cv` lists the skills you have earned, the principles you practised and the interview questions of the camps you cleared. In Bob, `/my-cv` turns them into plain CV or LinkedIn lines (only what you really did in the lab, never invented experience), and `/interview` plays a friendly interviewer for a junior SRE or DevOps role and gives kind feedback. Mission Control (`lab.py play`) shows the same in its "Your CV so far" and "Interview practice" panels. Parts 2, 3, 5, 6 and 7 end with an **Interview corner**; `/interview` covers every camp you cleared. Be honest with yourself and with recruiters: this lab gives you hands-on evidence for junior roles; it does not make you a senior engineer.

**Optional portfolio projects, open to everyone.** Four extra missions you design yourself, to show in an interview:

| Project | What you build | Where |
| --- | --- | --- |
| P-DASH | Your own Grafana dashboard | [Part 2](02-metrics-dashboards-alerts.md#portfolio-project-p-dash-your-own-dashboard) |
| P-RUNBOOK | A new runbook, linked from an alert's `runbook_url` | [Part 3](03-slos-and-incidents.md#portfolio-project-p-runbook-a-new-runbook) |
| P-ENV | A second `dev` environment with a Terraform workspace | [Part 5](05-automation-iac-cicd.md#portfolio-project-p-env-a-second-environment-from-code) |
| P-POLICY | A new Kyverno ClusterPolicy | [Part 6](06-delivery-resilience-policy.md#portfolio-project-p-policy-a-new-guardrail-policy) |

**For professors (optional).** How to run the shift as one class session is in the [instructor notes](../instructor/README.md). `python3 scripts/cohort_report.py <folder of the students' evidence.json files>` (Windows: `python scripts\cohort_report.py ...`) gives a class summary: how many students reached On-Call Ready, the missions most skipped (topics to reteach) and a fingerprint check. Students can finish with `lab.py proof --name "<name>"`, which writes a **self-generated** passport with a skills section, a badge and an evidence file with an integrity fingerprint (not a signature) to `lab-proof/`. The passport is a record, not a certificate or proof: a course that grades the optional deeper material confirms cluster-side missions in a short live check-off with `lab.py verify`.

<a id="the-first-on-call-shift-one-sitting"></a>
## The First on-call shift (one sitting)

This is the lab. A non-technical IBMer opens IBM Bob, pastes the link to this repository and, in **one sitting of about 2 to 3 hours** (most of it waiting for installs), Bob sets up the tools and walks them through a first hands-on experience of SRE. Nobody grades it. The journey has the id `first-shift` in [`lab/missions.json`](../../lab/missions.json); `python scripts\lab.py journey` (Mac and Linux: `python3 scripts/lab.py journey`) shows the steps, the done marks and the minutes left.

| # | Mission | What you do | Where it is taught | Minutes |
| --- | --- | --- | --- | --- |
| 1 | B00 Meet your AI partner | How you and Bob work together; the "Stay in control" box is part of it | [BOB-QUICKSTART](../BOB-QUICKSTART.md#stay-in-control-read-before-step-1) | 15 |
| 2 | M00 Boot the lab | Run `scripts/preflight.py` first, then Bob installs the tools and deploys the stack (mostly waiting) | [Part 1, M00](01-foundations.md#m00-laptop-and-cluster-setup) | 60 |
| 3 | M01 Instrument a service | See the metrics, traces and logs the app sends | [Part 1, M01](01-foundations.md#m01-instrumenting-a-service) | 10 |
| 4 | M04 Dashboards as code | Open Grafana and read the live dashboards | [Part 2, M04](02-metrics-dashboards-alerts.md#m04-grafana-dashboards-as-code) | 10 |
| 5 | M05 First alert | `scripts/trigger-alert.*` makes `HighErrorRate` fire | [Part 2, M05](02-metrics-dashboards-alerts.md#m05-alertmanager-routing-and-grafana-alerting-as-code) | 15 |
| 6 | N01 Alerts on your phone | `python scripts\notify_setup.py` (Mac: `python3 scripts/notify_setup.py`), subscribe in the free ntfy app or a browser, and a real `[firing]` push arrives from Alertmanager | [GUIDE 6-0](../GUIDE.md#6-0-phone-push-with-ntfy-recommended-on-ibm-laptops-no-account) | 10 |
| 7 | M07 Follow the trace | Follow one failing request in Jaeger and find it in the logs | [Part 4, M07](04-logs-traces-llm.md#m07-logs-and-traces) | 10 |
| 8 | M17 AI on call | `python scripts\ai_setup.py`, enable the MCP server in Bob, triage in the **SRE Triage** mode, save with `/save-triage` | [Part 7, M17](07-ai-assisted-sre.md#m17-ai-on-call-with-ibm-bob-claude-code-optional) | 20 |
| 9 | M18 Injection proof | Bob flags a planted instruction in the logs instead of following it | [Part 7, M18](07-ai-assisted-sre.md#m18-mcp-safety-and-the-prompt-injection-drill) | 15 |
| | **Total** | | | **about 165 minutes** |

The minutes are planning estimates for the shift version of each mission, not measurements of a real class. The "Where it is taught" pages hold the full module, which is longer: in the shift, Bob does the short version and the student can come back for the rest. When all nine are done, `lab.py` shows **SHIFT COMPLETE**, the **First On-Call Shift** badge, the skills the student touched and suggestions to keep exploring.

**Before the session:** run the preflight and, on an IBM-managed laptop, send [IT-REQUEST.md](../IT-REQUEST.md) to IT early (see above). An 8 GB laptop is enough for the whole shift.

<a id="official-core-path-about-35-hours"></a>
## Go deeper, at your own pace

Everything below is **optional** "keep exploring" material for students who liked the shift, or for a course that wants more. Nothing here is required, and nothing here is graded unless a course chooses to grade it (see [Suggested assessment](#suggested-assessment)). The hour estimates are for planning only.

The catalog [`lab/missions.json`](../../lab/missions.json) also holds the longer **Road to Junior SRE**: the core missions of every camp, **6 add-ons** and **4 portfolio projects**, plus the capstone. Some numbers are not used: M22, M25 and M26 do not exist, and M24 ("Observing the agents" in Part 7) is an instructor demo with no mission check. The table below is the full climb, after the shift; the shift missions are part of it.

| Camp | Core missions of the full climb | Hands-on time (module tables, optional) | Plan with lecture and breaks (optional) |
| --- | --- | --- | --- |
| Before class | Preflight, [IT request](../IT-REQUEST.md), tool install ([GUIDE](../GUIDE.md) step 2) | depends on IT approvals and downloads | pre-course week |
| 0 Orientation Day | B00 | short (5 quiz questions) | ~0.5 h |
| 1 The Engine Room | M00, M01, M02 | 3.25-3.75 h | ~5.5 h |
| 2 The Watchtower | M03, M04, M05, N01 | 3.75 h, plus about 10 min for N01 | ~4 h |
| 3 The War Room | M06, M08, M09 | 4.5 h | ~5.5 h |
| 4 The Detective Agency | M07, M23 | 2.25 h | ~2.5 h |
| 5 The Robot Workshop | M10 (Ansible part), M11, M09b, M12, M16 | 5.25 h | ~6 h |
| 6 The Proving Grounds | M14 | 0.5 h | ~1 h |
| 7 The AI Command Center | M17, M18, capstone M27 | 8.5-9.5 h | ~9.5 h |
| **Total** | **the full climb + capstone** | **about 30 h (optional)** | **about 35 h (optional); plan 40 h with a buffer for laptop problems** |

How the numbers were made: the hands-on time adds up the "Time" column of each module table in the parts. The plan column uses the part totals given in the table below for Parts 1-4, and for Parts 5-7 adds a short lecture to the module times. They are planning estimates, not measurements of a real class.

- **The capstone M27 needs no add-on.** Run both drills with the alert drill (`trigger-alert`), which works on the core stack. Chaos or a canary in M27 is an optional twist.
- **8 GB laptops** can do the shift and the whole climb. Only the add-ons need 16 GB.

**Optional add-ons** (16 GB laptop, one at a time, or an instructor demo):

| Add-on | Mission | Time (module table) |
| --- | --- | --- |
| AWX autopilot (Part 5) | M10X | part of M10's 90 min, plus about 2.5 GB of memory |
| Signed and sealed: supply chain (Part 5) | M19 | 45 min |
| GitOps with ArgoCD (Part 6) | M13 | 45 min |
| Chaos engineering (Part 6) | M15 | 45 min |
| Policy as code with Kyverno (Part 6) | M20 | 40 min |
| Canary with Argo Rollouts (Part 6) | M21 | 45 min |
| Observing the agents (Part 7, instructor demo, no mission) | none | 30 min |

The four portfolio projects (P-DASH, P-RUNBOOK, P-ENV, P-POLICY) are self-paced and optional for everyone.

The seven lab parts below list **every** module, core and add-on together, so their optional times add up to more (about 52 h).

| Part | Modules | Time (optional) | Memory |
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
The author ran the add-ons and scripts of this lab end to end on a local Minikube cluster in November 2026, with Claude Code as the operator (see [How this was built](../../README.md#how-this-was-built)). The expected results quoted in the parts come from those runs. Most run logs are not stored in this repository (`reports/` is gitignored). What is stored: one real alert drill with its AI triage ([evidence](../evidence/ai-triage-2026-11-19.md)) and its [postmortem](../postmortems/2026-11-19-alert-drill-and-ai-triage.md), and the [screenshots](../screenshots/), including alerts delivered to a phone through ntfy (`notification-delivered.png`). Delivery to Slack or email is not shown, because it needs a personal webhook or mail account. The 2027 path on IBM-managed laptops (IT approvals, Bob entitlement, VPN) has not been tried by a real cohort yet: run the preflight and use [IT-REQUEST.md](../IT-REQUEST.md). Versions are pinned in the files; when a pinned image disappears (it happened with the AWX operator's `kube-rbac-proxy`), the fix is documented where it applies.

## Suggested assessment
**Nobody grades the First on-call shift.** It is an ice-breaker. This section is only for a course that chooses to grade the optional deeper material.

- **Quizzes and self-checks are formative.** They help students learn and **never count toward a grade**. The XP they give is for motivation only. The self-check answers are in the parts, collapsed under each self-check; the quiz answers in `missions.json` are stored as hashes. Grading uses evidence instead: see [docs/instructor/README.md](../instructor/README.md).
- **Weekly:** the evidence listed in each part's instructor notes (screenshots, generated reports), confirmed in a short live check-off with `lab.py verify`.
- **Final project:** this repository is the reference solution for the six requirements and three bonuses (see the [README](../../README.md#final-project-requirements)), so a clone alone earns no credit. Each student, working in their fork, adds one new endpoint to `app/app.py` with a unit test in `tests/`, an SLI recording rule and an SLO alert with `runbook_url` in `k8s/config/prometheus/slo.yml`, one Grafana panel for it, a runbook in `docs/runbooks/`, and a one-page ORR for the change. CI (`ci.yml`) must pass on the pull request in their fork. Pass criteria: the alert fires in Alertmanager during a provoked failure (screenshot), and `pytest tests -q` and `flake8` pass.
- **Capstone:** the AI-assisted game day (Part 7, M27), graded on the postmortem, the TTD/TTA/TTR numbers and the "what the AI got wrong" log.
- **Suggested weighting:** weekly evidence 40%, final project 30%, capstone 30%. Each item is pass/fail against the evidence listed for it. Quiz scores and XP are not part of the grade.
