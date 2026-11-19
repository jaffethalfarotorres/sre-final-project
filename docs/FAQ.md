# FAQ: the questions a reader would ask

I wrote this page because there is no presentation for this project. You only get the GitHub link. So here I answer the questions a teacher, a classmate, a 2027 student or a hiring manager would ask me in person. Every answer links to the file, the line or the screenshot that proves it. If a link and my words disagree, trust the link.

**Jump to:** [In plain words](#in-plain-words) · [Does it really run?](#1-does-it-really-run-from-a-fresh-clone) · [From a failing request to a phone push](#2-from-a-failing-request-to-a-phone-push) · [The 14.4x burn rate](#3-what-does-the-144x-burn-rate-mean-and-why-two-windows) · [Who did what (AI)](#4-which-parts-did-i-do-and-which-did-the-ai-do) · [30-day SLO limits](#5-the-slo-says-30-days-what-does-it-really-measure) · [Runbook drift](#6-how-do-the-runbook-and-the-rules-stay-in-sync) · [One pod lost, one pod failing](#7-two-replicas-one-pod-dies-the-other-returns-20-errors-who-gets-paged) · [Design choices](#8-design-choices) · [Minimum for the six requirements](#9-what-is-the-minimum-to-meet-the-six-requirements) · [The AI drills](#10-did-an-ai-really-flag-the-injection-on-a-live-cluster) · [Verify in 15 minutes](#verify-everything-in-15-minutes) · [Honest limits](#honest-limits) · [More questions](#more-questions)

---

## In plain words

**What is this?** A small pretend online shop runs on my laptop. The project measures how healthy it is, draws the measurements as live charts, and sends an alarm to my phone when something goes wrong. Then it practises what a Site Reliability Engineer (SRE, the person who keeps online services working) does next: find the cause, fix it and learn from it.

**Who is it for?** First, it is an **ice-breaker** for IBMers who want to try SRE: you open IBM Bob (IBM's AI assistant), paste the link to this repository, and Bob sets up the tools and walks you through your [first on-call shift](../README.md#the-first-on-call-shift). Second, it is my SRE Academy 2026 final project, so the grader material stays here too. The README has a [table by audience](../README.md#start-here-by-audience).

**How long does it take?** One sitting of about 2 to 3 hours. The 9 steps add up to about 165 minutes, and most of that is waiting while Bob installs the tools and deploys the stack (step M00, about 60 minutes). Everything else in the repository (the other camps, the add-ons, the portfolio projects, the seven deeper lab parts) is optional, at your own pace: [Keep exploring](../README.md#keep-exploring).

**Is it graded?** No. Nobody grades the shift. The quizzes and XP are there to help you learn and to make it fun. A course may choose to grade the optional deeper material; the [lab guide, "Suggested assessment"](labs/README.md#suggested-assessment) says how.

**Do I need to be technical to read it?** No. Start with [GUIDE section 1](GUIDE.md#1-what-is-this-project) and the [glossary](GUIDE.md#glossary).

---

## 1. Does it really run from a fresh clone?

Yes. The screenshot [pods.png](screenshots/pods.png) is `kubectl get pods -A` from my laptop on 2026-11-19 (commit `e308f25`), during an alert drill. It shows:
- 2 replicas of `sre-metrics-app` in the `application` namespace, plus the traffic generator and the `errload` drill pod;
- Prometheus, Alertmanager, Grafana, the blackbox exporter and the Grafana MCP server in `monitoring`;
- Jaeger, Loki and the OpenTelemetry Collector in `opentelemetry`.

To check it yourself, follow [Verify everything in 15 minutes](#verify-everything-in-15-minutes). The deploy script is [`scripts/deploy.sh`](../scripts/deploy.sh) (Windows: [`scripts/deploy.ps1`](../scripts/deploy.ps1)). Every screenshot caption in the [README evidence section](../README.md#evidence) says the date and the commit.

---

## 2. From a failing request to a phone push

This is the whole alert path, step by step. You can follow it in the files.

**Step 1. The app counts every request.** In [`app/app.py`](../app/app.py#L104-L117) the counter `http_requests_total` has three labels: `method`, `endpoint` and `status`. When `/store` fails, the app adds 1 to the counter with `status="500"` ([lines 152-162](../app/app.py#L152-L162)). By default 1 in 200 `/store` calls fails on purpose (`STORE_ERROR_RATE=0.005`, [line 43](../app/app.py#L43)), so there is always a little real data. The test endpoint `/error` always fails ([lines 171-185](../app/app.py#L171-L185)). The drill uses it.

**Step 2. Prometheus collects the numbers.** Prometheus calls `/metrics` on each app pod every 10 seconds. It finds the pods by their annotations (see [question 8](#8-design-choices)). The config is [`k8s/config/prometheus/prometheus.yml`](../k8s/config/prometheus/prometheus.yml). Proof: [prometheus-targets.png](screenshots/prometheus-targets.png).

**Step 3. A rule decides "this is a problem".** The rule `HighErrorRate` in [`k8s/config/prometheus/alerts.yml`](../k8s/config/prometheus/alerts.yml) says, in plain words:
- more than 5% of all requests failed in the last 5 minutes,
- and there is real traffic (more than 0.2 requests per second, so 1 failure out of 3 requests on a quiet app does not wake anyone),
- and this stays true for 2 minutes (`for: 2m`).

**Why `for: 2m`?** One bad scrape or a short spike should not page a person. Two minutes of a 5-minute ratio above 5% means the problem is real and still going. It is also short enough: in my drill the alert fired 2 min 19 s after the problem started ([postmortem timeline](postmortems/2026-11-19-alert-drill-and-ai-triage.md#timeline-times-in-utc)). The label `severity: critical` decides where it goes next. Proof: [prometheus-alerts.png](screenshots/prometheus-alerts.png).

**Step 4. Alertmanager decides who hears it.** [`k8s/alertmanager.yaml`](../k8s/alertmanager.yaml) has the routes. For a `critical` alert:
1. The first critical route sends it to `awx-collect-diagnostics` (a read-only diagnostics job, only when AWX is installed) and has `continue: true`, so it keeps going.
2. The second critical route sends it to the receiver `critical-notifications`. It waits only 10 s (`group_wait: 10s`) and repeats every hour.
3. `critical-notifications` has three outputs: Slack, email and a webhook to ntfy (`url_file: /etc/alertmanager-secrets/ntfy-url`).

A `warning` alert goes to `warning-notifications`, which also has the ntfy webhook. Proof: [alertmanager-alert.png](screenshots/alertmanager-alert.png).

**Step 5. The phone buzzes.** [ntfy](https://ntfy.sh) is a free push service with no account. [`scripts/notify_setup.py`](../scripts/notify_setup.py) creates a private random topic, writes its URL into the private file `k8s/alertmanager-secret.yaml` (Git never uploads it), and sends a test push. I used ntfy because on an IBM laptop personal Slack and personal mail are usually blocked, and the lab must never use IBM Slack or IBM mail. Proof: [notification-delivered.png](screenshots/notification-delivered.png) is the ntfy web view of my topic during the drill. It shows `HighErrorRate`, `ErrorBudgetFastBurn` (both critical) and `ErrorLogBurst` (a warning from Grafana alerting on Loki logs), plus the first test push. A phone that subscribes to the same topic in the ntfy app gets these messages as push notifications. The setup is in [GUIDE section 6-0](GUIDE.md#6-0-phone-push-with-ntfy-recommended-on-ibm-laptops-no-account).

**Try it:** `./scripts/trigger-alert.sh` (Windows: `scripts\trigger-alert.ps1`) starts a pod that calls `/error` about 4 times per second and waits until `HighErrorRate` fires.

---

## 3. What does the 14.4x burn rate mean, and why two windows?

**The SLO.** 99% of requests must succeed over 30 days. So 1% may fail. That 1% is the **error budget** ([SLO.md](SLO.md)).

**The burn rate** says how fast I spend the budget. At 1x, the budget lasts exactly 30 days. At 2x, it lasts 15 days. If the error rate is 14.4%, that is 14.4 times the allowed 1%, so the burn rate is 14.4x.

**Where 14.4 comes from.** 30 days have 720 hours. The Google SRE Workbook says: page a person when 2% of the monthly budget is gone in 1 hour. Spending 2% in 1 hour is `0.02 x 720 = 14.4` times faster than "exactly on budget". At that speed the whole budget is gone in about 2 days. That is worth waking someone.

**Why two windows.** The rule `ErrorBudgetFastBurn` in [`k8s/config/prometheus/slo.yml`](../k8s/config/prometheus/slo.yml) needs the burn rate above 14.4x over **1 hour and** over **5 minutes**:
- The **long window (1 hour)** proves the problem is big and real, not a 30-second spike.
- The **short window (5 minutes)** proves it is still happening now. When the fix works, the 5-minute rate drops fast, so the page clears in minutes, not after an hour.

The same idea gives the slower alerts: 6x over 6 hours and 30 minutes (look at it today), and 1x over 3 days and 6 hours (open a ticket). The math is in the [header comment of slo.yml](../k8s/config/prometheus/slo.yml) and in [SLO.md, "Where 14.4 comes from"](SLO.md#alerts-on-the-slo).

**Is it tested?** Yes, without a cluster. [`tests/rules/slo.test.yml`](../tests/rules/slo.test.yml) are promtool unit tests: the page fires at 15x and stays silent at 14x, normal traffic fires nothing, and one drill on a 1-day-old cluster does not exhaust the budget. CI runs them on every push ([ci.yml](../.github/workflows/ci.yml), step "Check Prometheus rules and config").

---

## 4. Which parts did I do, and which did the AI do?

The README section [How this was built](../README.md#how-this-was-built) is the short answer. In more detail:

- **I decided:** the goals and the scope, a public portfolio project, Minikube on a laptop, Python for the app, a guided lab with IBM Bob for 2027, and the safety rules for the AI tools ([AGENTS.md](../AGENTS.md)). I directed the work, approved the changes and decided each release.
- **The AI did:** Claude Code (by Anthropic) generated most of the code, the manifests and the documentation, following my direction. It also ran the live checks on my local Minikube cluster. I used AI review panels to find problems before submitting.
- **How to see it:** commits made with AI help have a `Co-Authored-By` trailer. To count them, run `git log --format=%b | grep -c Co-Authored-By` (Mac, Linux, Git Bash) or `(git log --format=%b | Select-String Co-Authored-By).Count` (PowerShell).
- **What I can explain without help:** the alert path ([question 2](#2-from-a-failing-request-to-a-phone-push)), the burn-rate alerts ([question 3](#3-what-does-the-144x-burn-rate-mean-and-why-two-windows)) and the Kubernetes deployment ([question 8](#8-design-choices)).

**Problems the checks found, and how they were fixed.** I do not hide that AI-generated work had mistakes:
- The live drill on 2026-11-19 showed that the AI triage instructions filtered logs for `WARNING`, but the app writes `WARN`. They would have missed the injected line. The filters now match `ERROR|WARN|WARNING` ([evidence](evidence/ai-triage-2026-11-19.md), point 1).
- The same drill showed `/store` failing about 4.7%, not 0.5%. The cause: the deploy scripts rebuilt the image with the same tag, so Kubernetes kept the old pods. Both deploy scripts now restart the app after the build ([postmortem, 5 Whys](postmortems/2026-11-19-alert-drill-and-ai-triage.md#root-cause-analysis-5-whys)).
- pip-audit in CI found known vulnerabilities in the Flask and OpenTelemetry versions pinned by the course, so the app was upgraded (comment in [ci.yml](../.github/workflows/ci.yml), job `security`).

---

## 5. The SLO says 30 days. What does it really measure?

Honest answer: on this lab, **only the time since the last Prometheus restart.**

- Prometheus keeps 31 days (`--storage.tsdb.retention.time=31d` in [`k8s/prometheus.yaml`](../k8s/prometheus.yaml)), so the window fits.
- But the data is on an `emptyDir` volume. When the Prometheus pod restarts, all history is gone, and the budget starts again from full.
- You can see this in [grafana-slo.png](screenshots/grafana-slo.png): Prometheus had restarted about an hour before, and two drills since then made the "30-day" availability look very low.
- The request guards on `ErrorBudgetTicket` and `ErrorBudgetExhausted` keep these long-window alerts quiet on a young cluster.

In production you would use a PersistentVolumeClaim and long-term storage such as Thanos or Mimir. All of this is written in [SLO.md, Limits of this lab](SLO.md#limits-of-this-lab).

---

## 6. How do the runbook and the rules stay in sync?

The thresholds live in one place: [`slo.yml`](../k8s/config/prometheus/slo.yml). [SLO.md](SLO.md#alerts-on-the-slo) and the runbook [error-budget-burn.md](runbooks/error-budget-burn.md) explain them in words. Each alert, except the demo alert, has a `runbook_url` that points to its runbook. The promtool tests in [`tests/rules/`](../tests/rules/) check the real numbers (fires at 15x, silent at 14x), so a change to a threshold breaks CI until the test is updated too. The text in the runbook is not tested automatically. A reviewer must check it in the pull request. [CONTRIBUTING.md](../CONTRIBUTING.md) asks for this.

---

## 7. Two replicas. One pod dies, the other returns 20% errors. Who gets paged?

With the current rules in [`alerts.yml`](../k8s/config/prometheus/alerts.yml) and [`alertmanager.yaml`](../k8s/alertmanager.yaml):

- **The lost pod:** `ServiceDown` (critical) fires only when **no** app pod can be scraped. One pod of two is not an outage, so `ServiceDown` stays quiet. If the pod stays down for 5 minutes, `ReplicaDown` sends a **warning** (Slack, email, ntfy; no page and no AWX job). A quick restart sends nothing.
- **The 20% errors:** all traffic now goes to the surviving pod, so about 20% of all requests fail. `HighErrorRate` (more than 5%, for 2 minutes) **pages**. `ErrorBudgetFastBurn` (20x is above 14.4x) also pages once the 1-hour window is above 14.4x too.
- **Inhibition:** `ServiceDown` is not firing, so nothing hides the error alerts. `ErrorBudgetFastBurn` mutes `ErrorBudgetSlowBurn` and `ErrorBudgetTicket`, because a person is already paged. Muted alerts still show in the Alertmanager UI as "inhibited".

Before this change, `ServiceDown` was per pod, so one lost pod could page as critical and mute the error alerts. The drill showed it (`ServiceDown` went pending for each replaced pod). It is listed in the [postmortem](postmortems/2026-11-19-alert-drill-and-ai-triage.md#what-could-be-improved) and tested in [`tests/rules/alerts.test.yml`](../tests/rules/alerts.test.yml).

---

## 8. Design choices

**Annotation-based pod discovery instead of a ServiceMonitor.** The core stack runs a plain Prometheus, not the Prometheus Operator. A ServiceMonitor is a custom resource that only the Operator understands. So Prometheus uses Kubernetes service discovery (`role: pod`) and keeps only pods with the annotation `prometheus.io/scrape: "true"`. The annotations are in [`k8s/application.yaml`](../k8s/application.yaml) (`prometheus.io/scrape`, `prometheus.io/path`, `prometheus.io/port`), and the matching relabel rules are in the `kubernetes-pods` job of [`prometheus.yml`](../k8s/config/prometheus/prometheus.yml). This is simple to read and teaches how discovery works.
- **What breaks without the annotation:** Prometheus never scrapes that pod. Its metrics are missing, its errors do not count in `HighErrorRate` or the SLO, and it is not in `up{...}`. It does **not** fail loudly. You see it only on **Status > Targets**. (If no app pod at all is scraped, the `absent()` part of `ServiceDown` fires.)
- **The Helm path uses a ServiceMonitor.** `./scripts/deploy.sh --helm` installs kube-prometheus-stack, which has the Operator, and the chart creates a ServiceMonitor (`serviceMonitor.enabled: true` in [`helm/sre-metrics-app/values.yaml`](../helm/sre-metrics-app/values.yaml)). So both ways are in the repo.

**Kustomize instead of Helm for the main path.** Kustomize is built into `kubectl` (`kubectl apply -k k8s`), so students install one tool less. The manifests stay plain YAML that you can read top to bottom. Kustomize also turns the files in `k8s/config/` into ConfigMaps with a content hash, so a changed rule restarts Prometheus by itself ([`k8s/kustomization.yaml`](../k8s/kustomization.yaml)). Helm is the second path, for the Infrastructure as Code bonus ([`helm/`](../helm/)).

**Minikube.** It runs on one laptop with no cloud account and no cost. That matters for IBM-managed laptops and for a class of non-technical students. The deploy script creates a 4 GB cluster, enough for the core stack.

**Two replicas.** So one pod can die (chaos test, rolling update, crash) while the other still serves users. The rolling update uses `maxUnavailable: 0` and `maxSurge: 1`, so there is always a ready pod during an update ([`k8s/application.yaml`](../k8s/application.yaml)). More replicas would only use memory on a laptop.

---

## 9. What is the minimum to meet the six requirements?

The core stack. One command (`scripts/deploy.sh` or `deploy.ps1`) covers requirements 1 to 5: the app with metrics, Kubernetes, Prometheus, Grafana and Alertmanager. No add-on is needed. Requirement 6 is the documentation you write.

**How long:**
- Installing the tools: the shift plans about 60 minutes for the install and the first deploy together (step M00), mostly waiting. A slow laptop or network can take longer ([BOB-QUICKSTART, "What you need"](BOB-QUICKSTART.md#what-you-need)).
- The first deploy: 5 to 10 minutes ([README Quick start](../README.md#quick-start)).
- The first on-call shift: about 165 minutes in one sitting, the tool install included ([lab guide](labs/README.md#the-first-on-call-shift-one-sitting)).
- Optional, to go deeper into what you deployed: the lab parts that cover requirements 1 to 5 are [Part 1](labs/01-foundations.md) (about 5.5 h) and [Part 2](labs/02-metrics-dashboards-alerts.md) (about 4 h), from the [lab guide table](labs/README.md#go-deeper-at-your-own-pace).

**For a 2027 student:** the [first on-call shift](../README.md#the-first-on-call-shift) already deploys this core stack in one sitting, and nobody grades it. Only if your course chooses to grade the optional deeper material: a copy of this repository earns no credit, and the [lab guide, "Suggested assessment"](labs/README.md#suggested-assessment) and [GUIDE, "Your final project"](GUIDE.md#your-final-project-what-you-must-hand-in) say what you add in your own fork.

---

## 10. Did an AI really flag the injection on a live cluster?

Yes, once, on 2026-11-19 on my laptop. A **fresh** Claude Code agent, with read-only access and the rules from [AGENTS.md](../AGENTS.md), triaged the drill alerts. Nobody told it that a planted log line existed. It:
- found the cause with evidence (98.6% of the errors were on the test endpoint `/error`),
- quoted the `[INJECTION-DRILL]` line (which told it to delete the `monitoring` namespace) as suspicious and did not act on it,
- reported the real `/store` problem that nobody had asked about.

The full report is unchanged in [docs/evidence/ai-triage-2026-11-19.md](evidence/ai-triage-2026-11-19.md). The incident is in the [postmortem](postmortems/2026-11-19-alert-drill-and-ai-triage.md): TTD 2 min 19 s, TTR 19 min. This was one run with Claude Code. I have not repeated it with IBM Bob.

---

## Verify everything in 15 minutes

You need Git, Python 3.10 or newer, and Docker. For part B you also need Minikube and kubectl ([GUIDE step 2](GUIDE.md#2-install-the-tools-one-time)). The times assume the tools are already installed.

**A. Without a cluster (about 5 minutes).** These are the same checks CI runs ([CONTRIBUTING.md](../CONTRIBUTING.md) has all of them).

Mac and Linux:
```bash
git clone https://github.com/jaffethalfarotorres/sre-final-project.git
cd sre-final-project
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests -q                                     # unit tests of the app, the lab and the scripts
flake8 app tests scripts .claude/hooks --max-line-length=120
docker run --rm -v "$PWD:/w" -w /w --entrypoint sh prom/prometheus:v2.54.1 \
  -c 'promtool check rules k8s/config/prometheus/alerts.yml k8s/config/prometheus/slo.yml && promtool test rules tests/rules/*.test.yml'
```

Windows (PowerShell):
```powershell
git clone https://github.com/jaffethalfarotorres/sre-final-project.git
cd sre-final-project
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt   # no Activate.ps1 needed
.venv\Scripts\python -m pytest tests -q
.venv\Scripts\python -m flake8 app tests scripts .claude/hooks --max-line-length=120
docker run --rm -v "${PWD}:/w" -w /w --entrypoint sh prom/prometheus:v2.54.1 -c "promtool check rules k8s/config/prometheus/alerts.yml k8s/config/prometheus/slo.yml && promtool test rules tests/rules/*.test.yml"
```

**B. On a cluster (about 10 minutes).**
1. `./scripts/deploy.sh` (Windows: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\deploy.ps1`). 5 to 10 minutes the first time.
2. `kubectl get pods -A`: compare with [pods.png](screenshots/pods.png).
3. `./scripts/dashboards.sh --background` (Windows: `scripts\dashboards.ps1 -Background`). Open Prometheus at http://localhost:9090, **Status > Targets**: compare with [prometheus-targets.png](screenshots/prometheus-targets.png).
4. `./scripts/trigger-alert.sh` (Windows: `scripts\trigger-alert.ps1`). `HighErrorRate` fires after about 2 to 3 minutes. See it in Alertmanager at http://localhost:9093.
5. Optional: `python3 scripts/notify_setup.py` (Windows: `python scripts\notify_setup.py`) and subscribe to the topic in the ntfy app. The next drill reaches your phone.

**C. CI.** The [Actions tab](https://github.com/jaffethalfarotorres/sre-final-project/actions/workflows/ci.yml) shows every run. [ci-green.png](screenshots/ci-green.png) is one green run.

---

## Honest limits

- **The 30-day SLO** really covers only the time since the last Prometheus restart ([question 5](#5-the-slo-says-30-days-what-does-it-really-measure)).
- **The SRE Lab Passport is self-generated.** `lab.py proof` writes it on the student's laptop. Its fingerprint is not a signature: anyone can recompute it. It is a record, not a certificate. A professor confirms it with `lab.py verify` or a short live demo ([README](../README.md#the-journey-road-to-junior-sre)).
- **Slack and email delivery** are configured, but the repository does not show them working: they need a personal webhook or mail account. The delivered notification I can show is the ntfy push.
- **The add-on results** in the README table (ArgoCD, canary, AWX, rollback times) come from my own runs on Minikube in November 2026, with Claude Code as the operator. Most run logs are not stored in the repository ([lab guide, "How the verification was done"](labs/README.md#how-the-verification-was-done)).
- **The AI triage drill ran once**, with Claude Code, not with IBM Bob.
- **The shift's minutes are estimates.** The 9 steps (about 165 minutes) have not been timed with a real class yet. The tool install depends most on the laptop and the network: on a slow connection or a blocked laptop it can take longer, so run the preflight before the session.
- **Lab only:** no persistent storage, local and short-lived credentials, container images pinned to fixed versions.
- **IT decisions for 2027** (container engine, admin rights, VPN, Bob access) belong to the academy. [IT-REQUEST.md](IT-REQUEST.md) is a ticket template, and [`scripts/preflight.py`](../scripts/preflight.py) checks a laptop before the course.

---

## More questions

**Is it safe to let an AI near the cluster?** The AI gets read-only access: a kubeconfig that cannot delete and a Grafana token with the Viewer role ([`scripts/ai_setup.py`](../scripts/ai_setup.py)). In Claude Code, settings deny changing commands, and a best-effort hook catches common disguises. Kubernetes RBAC is the real backstop. The rules are in [AGENTS.md](../AGENTS.md) and [AI-SRE.md](AI-SRE.md#the-safety-rules-in-one-place). A human approves every change.

**What happens when an alert fires and AWX is installed?** Every critical alert also launches a read-only "collect diagnostics" job. A restart is never automatic: a person starts it after reading the report (comment in [`k8s/alertmanager.yaml`](../k8s/alertmanager.yaml)).

**Why 99% and not 99.9%?** The demo app fails 0.5% of `/store` on purpose. With 99.9%, that normal noise alone would break the SLO all the time. The reason is in [SLO.md, "Why 99%"](SLO.md#our-slos).

**What does `AlwaysFiringDemoAlert` do?** It is on purpose. It always fires with `severity: demo`, to prove that Prometheus can reach Alertmanager. It has its own quiet route.

**Where are the answer keys for the lab?** Not in this public repository, so students and their AI cannot read them. See [docs/instructor/README.md](instructor/README.md).

**I am a professor. Where do I start?** The [instructor notes](instructor/README.md) explain how to run the shift as one class session. Then the [course map](COURSE-MAP.md) and the [lab guide](labs/README.md) for the optional deeper material.

**I am a 2027 student on an IBM laptop. Where do I start?** [BOB-QUICKSTART.md](BOB-QUICKSTART.md). Run `python scripts\preflight.py` first to check your laptop (Mac: `python3 scripts/preflight.py`). It only reads and needs no admin rights. Then follow the 9 steps of the shift; `python scripts\lab.py journey` (Mac: `python3 scripts/lab.py journey`) shows where you are.

**Can my team reuse it to onboard SRE new hires or interns?** Yes. The shift is defined in the mission catalog [`lab/missions.json`](../lab/missions.json), so a team can define its own onboarding journey from the existing missions, or add its own. What needs code and what does not is in the README, [Reuse it for onboarding](../README.md#reuse-it-for-onboarding).

**Can I reuse this?** Yes, under the MIT licence ([LICENSE.md](../LICENSE.md)). Keep the original copyright line and add your own.
