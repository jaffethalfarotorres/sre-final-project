---
description: Open Mission Control, the visual map of your First on-call shift and everything you can explore after it
---
**Mode guard:** this works in Agent, Code and SRE Lab Guide. Only if the active mode cannot run commands (Plan, Ask), do nothing else and tell the student: "Please switch to Agent or SRE Lab Guide in the mode picker, then type this command again."

Run `lab.py play` (Windows: `python scripts/lab.py play`, never `python3`; Mac/Linux: `python3 scripts/lab.py play`). It writes `.lab/mission-control.html` and opens it in the browser and returns. Inside Bob the student can also open it with Command Palette > **Simple Browser: Show** and the file:/// link the command prints.

Walk the student through it in five short lines: how far they are in the **First on-call shift** (or that it is complete), their XP and rank, what Nimbus Store can do now, the next mission card, and the **Your CV so far** panel (skills they touched). If the shift is complete, add that the rest of the map (more camps, portfolio projects, and the **Interview practice** panel that says "Type to Bob: /interview") is optional, there to explore whenever they are curious.
