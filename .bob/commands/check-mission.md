---
description: Verify a mission on your real cluster and collect the XP
argument-hint: mission id, for example M05 (or "all")
---
**Mode guard:** if the active mode is not **SRE Lab Guide**, stop here. Tell the student: "Please pick SRE Lab Guide in the mode picker (Ctrl+. on Windows, Cmd+. on Mac), then type this command again." Do nothing else.

The mission id is the text the student typed after the command name. If there is none, run `lab.py journey` (or, once the shift is complete, `lab.py status`), say which mission is current, and ask: "Shall I check that one?"

Run `lab.py check <ID>` (use `lab.py check --all` when the student said "all"). Windows: `python scripts/lab.py ...` (never `python3`). Mac/Linux: `python3 scripts/lab.py ...`.

- **PASS:** celebrate in one sentence and name any achievement. Then ask the mission's quiz questions one by one (from `lab.py show <ID>`) and record each answer with `lab.py answer <ID> <n> <letter>`. Remind them once: full XP on the first try, half on the second, then it locks. If wrong, give a hint, never the answer.
- **LEVEL UP** in the output: celebrate the camp cleared in two short lines (the new capability of Nimbus Store and the SRE principle). During the shift keep it short and move on; after the shift, also read the new CV skills and the interview question and offer `/interview`.
- Then show progress. While the **First on-call shift** is not complete, run `lab.py journey` and say which step is next and how many minutes are left. If this check completed the 9th step (**SHIFT COMPLETE**), follow the "SHIFT COMPLETE" section of .bob/rules-sre-lab-guide/10-game-master.md: congratulate, open Mission Control with `lab.py play`, show `lab.py cv`, and offer the optional next steps without pressure. After the shift, run `lab.py play` after each check.
- **Not yet:** read the detail line with the student, explain what it means in plain words, and suggest the one next step from the lab guide. Do not mark anything done yourself: only the check can.
