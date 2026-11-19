---
description: Show the next lab mission and start teaching it
argument-hint: optional mission id, for example M05
---
Run `python3 scripts/lab.py status` (Windows: `python scripts\lab.py status`). If an id was given ($ARGUMENTS), use `python3 scripts/lab.py show <id>` for that mission instead.

Tell the student the mission title, the XP, and the goal in one friendly sentence. Open the guide file it points to, find the matching module, and teach it with the loop in .bob/rules-sre-lab-guide/10-game-master.md: explain the idea simply, then one approved command at a time. If the mission is an add-on, check memory first and remind them to clean up after the check.
