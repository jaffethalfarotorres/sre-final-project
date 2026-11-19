---
description: Show your rank, XP, camp, achievements and next mission
---
**Mode guard:** if the active mode is not **SRE Lab Guide**, stop here. Tell the student: "Please pick SRE Lab Guide in the mode picker (Ctrl+. on Windows, Cmd+. on Mac), then type this command again." Do nothing else.

Run `lab.py status`, then `lab.py missions` (Windows: `python scripts\lab.py ...`, never `python3`; Mac/Linux: `python3 scripts/lab.py ...`). Summarize in four short lines: rank and XP (and the next rank); the camp they are at on the road to On-Call Ready; missions done out of total; the next mission with its goal. If they have cleared at least one camp, add: "Type `/my-cv` to see the skills you can already put on your CV." Encourage the student.
