---
description: Open Mission Control, the visual map of your road from Career Changer to On-Call Ready
---
**Mode guard:** if the active mode is not **SRE Lab Guide**, stop here. Tell the student: "Please pick SRE Lab Guide in the mode picker (Ctrl+. on Windows, Cmd+. on Mac), then type this command again." Do nothing else.

Run `lab.py play` (Windows: `python scripts\lab.py play`, never `python3`; Mac/Linux: `python3 scripts/lab.py play`). It writes `.lab/mission-control.html` and opens it in the browser and returns. Inside Bob the student can also open it with Command Palette > **Simple Browser: Show** and the file:/// link the command prints.

Walk the student through it in five short lines: which camp they are at (and their rank), what Nimbus Store can do now, the next mission card, the **Your CV so far** panel (skills they earned), and the **Interview practice** panel. That panel says "Type to Bob: /interview": tell them that is how they rehearse with you.
