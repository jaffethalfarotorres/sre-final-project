---
description: Open Mission Control, the visual map of your First on-call shift and everything you can explore after it
---
**Mode guard:** if the active mode is not **SRE Lab Guide**, stop here. Tell the student: "Please pick SRE Lab Guide in the mode picker (Ctrl+. on Windows, Cmd+. on Mac), then type this command again." Do nothing else.

Run `lab.py play` (Windows: `python scripts\lab.py play`, never `python3`; Mac/Linux: `python3 scripts/lab.py play`). It writes `.lab/mission-control.html` and opens it in the browser and returns. Inside Bob the student can also open it with Command Palette > **Simple Browser: Show** and the file:/// link the command prints.

Walk the student through it in five short lines: how far they are in the **First on-call shift** (or that it is complete), their XP and rank, what Nimbus Store can do now, the next mission card, and the **Your CV so far** panel (skills they touched). If the shift is complete, add that the rest of the map (more camps, portfolio projects, and the **Interview practice** panel that says "Type to Bob: /interview") is optional, there to explore whenever they are curious.
