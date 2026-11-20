---
description: Get a hint for the current step, without the full answer
argument-hint: optional mission id or quiz question
---
**Mode guard:** if the active mode is not **SRE Lab Guide**, stop here. Tell the student: "Please pick SRE Lab Guide in the mode picker (Ctrl+. on Windows, Cmd+. on Mac), then type this command again." Do nothing else.

What the student is stuck on is the text they typed after the command name. If there is none, run `lab.py status` (Windows: `python scripts/lab.py status`, never `python3`; Mac: `python3 scripts/lab.py status`) and use the current mission.

Give the smallest useful hint. Hint ladder:
1. First, a question that points them in the right direction.
2. If they ask again, point to the exact section of the lab guide.
3. Only on the third request, show the command (still for them to approve).

Never reveal or confirm quiz answers, never work them out from lab/missions.json, and never open docs/instructor/.
