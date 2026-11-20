---
description: For teachers and graders - check the whole project in one read-only command and get a report
---
**Mode guard:** if the active mode cannot run commands (Plan, Ask), do not write a plan or a file. Ask the person to switch to Agent, Code or SRE Lab Guide in the mode picker and type /smoke-test again. Do nothing else.

This command is for a **teacher, grader or reviewer** who wants to check the project, not take the shift. It works in **SRE Lab Guide**, **Agent** or **Code** mode (any mode that can run commands). It never changes the project: do not edit files, do not create plan files, and never commit, push, fork or create a repository.

1. In one sentence, say what happens: one read-only script runs the main CI checks (unit tests, code style, Kubernetes manifests, Helm chart, alert and SLO rule tests), and, if the lab is running, also checks the live pods, Prometheus targets, alert rules, Alertmanager and Grafana. It takes about 2 minutes (longer the first time, while Docker downloads the Prometheus image).
2. Make sure the open folder is the repository root (it contains AGENTS.md and scripts/smoke_test.py). If it is not cloned yet, propose `git clone https://github.com/jaffethalfarotorres/sre-final-project.git` and ask the person to open that folder.
3. If `pytest` or `flake8` are missing, propose the one-time setup, one approved command at a time (Windows shown; Mac/Linux use `python3` and `.venv/bin/python`): `python -m venv .venv`, then `.venv\Scripts\python -m pip install -r requirements-dev.txt`. Use `.venv\Scripts\python` for the next step.
4. Run the smoke test. If the lab is running (`kubectl get pods -A` shows the `application` namespace, or the person says so), add `--cluster`:
   `python scripts/smoke_test.py --cluster --report reports\smoke-test.md` (Mac/Linux: `python3 scripts/smoke_test.py --cluster --report reports/smoke-test.md`). `reports/` is not tracked by Git, so the report stays on this laptop.
5. Show the result as a short table: PASS, FAIL or SKIP per check, with the fix for anything not PASS. A SKIP is a missing tool on this laptop, not a problem in the project: say how to turn it into a PASS.
6. Then map the result to the rubric with the **grader view** in README.md (each requirement links to its file and its screenshot) and point to the evidence: docs/FAQ.md, docs/postmortems/, docs/evidence/.
7. Offer to show it running, which is the real point of the project: "Want to see every tool working? With your OK I run one command, `python scripts/lab_up.py`: it installs what is missing, deploys the lab on this laptop (15-40 minutes, mostly downloads), opens the web pages and checks they are connected. Then I fire an alert drill and we follow the alert through Prometheus, Alertmanager and your phone." Then follow AGENTS.md "First message", steps 3 to 6.
