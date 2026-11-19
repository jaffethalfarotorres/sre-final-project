---
description: Verify a mission on your real cluster and collect the XP
argument-hint: mission id, for example M05 (or "all")
---
**Mode guard:** if the active mode is not **SRE Lab Guide**, stop here. Tell the student: "Please pick SRE Lab Guide in the mode picker (Ctrl+. on Windows, Cmd+. on Mac), then type this command again." Do nothing else.

The mission id is the text the student typed after the command name. If there is none, run `lab.py status`, say which mission is current, and ask: "Shall I check that one?"

Run `lab.py check <ID>` (use `lab.py check --all` when the student said "all"). Windows: `python scripts\lab.py ...` (never `python3`). Mac/Linux: `python3 scripts/lab.py ...`.

- **PASS:** celebrate in one sentence and name any achievement. Then ask the mission's quiz questions one by one (from `lab.py show <ID>`) and record each answer with `lab.py answer <ID> <n> <letter>`. Remind them once: full XP on the first try, half on the second, then it locks. If wrong, give a hint, never the answer.
- **LEVEL UP** in the output: celebrate the camp cleared and read aloud, in plain words, the new capability Nimbus Store gained, the SRE principle, the new skills for their CV and the interview question. Offer: "Want to rehearse that question now? Type `/interview`."
- Then run `lab.py play` to show Mission Control with the student's new position on the road to On-Call Ready.
- **Not yet:** read the detail line with the student, explain what it means in plain words, and suggest the one next step from the lab guide. Do not mark anything done yourself: only the check can.
