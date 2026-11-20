---
description: A guided session - Bob sets up the lab, tours every tool with you, fires an alert drill and answers questions
---
**Mode guard:** this works in Agent, Code and SRE Lab Guide. Only if the active mode cannot run commands (Plan, Ask), do nothing else and tell the student: "Please switch to Agent or SRE Lab Guide in the mode picker, then type /start-lab again."

Lead a guided session. Follow AGENTS.md ("First message") and keep it warm, short and one step at a time. The student is usually not technical: you do the typing, they approve and watch.

1. Greet them. In three short sentences: they will see a small online shop (**Nimbus Store**) watched by real SRE tools, running on their own laptop; you set it up and show every tool working; nothing is graded and nothing leaves the laptop.
2. Make sure the open folder is the repository root (it contains AGENTS.md and scripts/lab_up.py). If it is not, ask them to use File > Open Folder on `sre-final-project`.
3. **Set up.** Ask for ONE OK, then run `python scripts/lab_up.py` (Mac: `python3`). Follow its result line exactly as AGENTS.md says (DONE, NOT_FINISHED: run it again, NEEDS_HUMAN: say what to click, FAILED: read the log). While it works, explain the big picture in a few lines.
4. **Tour.** `python scripts/lab_up.py --tour 1`, then 2, 3 and so on up to 5: shop, Prometheus, Grafana, Jaeger, Alertmanager. At each stop say what they see, let them click around, answer questions, and only move on when they say so.
5. **Break it on purpose.** `python scripts/lab_up.py --drill`. Follow the alert together from Grafana to Prometheus to Alertmanager. Offer phone alerts (`python scripts/notify_setup.py`, free ntfy app) as an option.
6. **Explore.** Everything runs now. Offer docs/EXPLORE.md, "what if" questions, and `/explain <tool>`. Triage of the drill alert is read-only: offer the SRE Triage mode.
7. **Optional game.** If they want a challenge, offer the 9-step First on-call shift with quizzes and a badge: follow "The First on-call shift, step by step" in .bob/rules-sre-lab-guide/10-game-master.md (SRE Lab Guide mode). Stopping after the tour and drill is a perfectly good ending.

If the lab is already running, skip step 3 (lab_up.py returns DONE in seconds) and continue from the tour.
