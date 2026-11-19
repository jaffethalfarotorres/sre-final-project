---
description: Verify a mission on your real cluster and collect the XP
argument-hint: mission id, for example M05 (or "all")
---
Run `python3 scripts/lab.py check <id>` for the mission in $ARGUMENTS (use `--all` when the argument is "all"; Windows: `python scripts\lab.py ...`).

- PASS: celebrate in one sentence, mention any achievement, then ask the mission's quiz questions one by one and record each answer with `python3 scripts/lab.py answer <id> <n> <letter>`. If the output says LEVEL UP, celebrate the camp reached and the new capability Nimbus Store gained. Then run `python3 scripts/lab.py play` to show Mission Control with Bob's new position on the mountain.
- Not yet: read the detail line with the student, explain what it means, and suggest the one next step from the lab guide. Do not mark anything done yourself: only the check can.
