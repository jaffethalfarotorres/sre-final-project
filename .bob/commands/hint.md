---
description: Get a hint for the current step, without the full answer
argument-hint: optional mission id or quiz question
---
**Mode guard:** this works in Agent, Code and SRE Lab Guide. Only if the active mode cannot run commands (Plan, Ask), do nothing else and tell the student: "Please switch to Agent or SRE Lab Guide in the mode picker, then type this command again."

What the student is stuck on is the text they typed after the command name. If there is none, run `lab.py status` (Windows: `python scripts/lab.py status`, never `python3`; Mac: `python3 scripts/lab.py status`) and use the current mission.

Give the smallest useful hint. Hint ladder:
1. First, a question that points them in the right direction.
2. If they ask again, point to the exact section of the lab guide.
3. Only on the third request, show the command (still for them to approve).

Never reveal or confirm quiz answers, never work them out from lab/missions.json, and never open docs/instructor/.
