---
description: Show how far you are in your First on-call shift, your XP and what comes next
---
**Mode guard:** this works in Agent, Code and SRE Lab Guide. Only if the active mode cannot run commands (Plan, Ask), do nothing else and tell the student: "Please switch to Agent or SRE Lab Guide in the mode picker, then type this command again."

Run `lab.py journey`, then `lab.py status` (Windows: `python scripts/lab.py ...`, never `python3`; Mac/Linux: `python3 scripts/lab.py ...`). Summarize in four short lines:
- **Shift not complete yet:** steps done out of 9 and the minutes left; the next step with its goal in one sentence; their XP; one line of encouragement.
- **Shift complete:** congratulate them on their First On-Call Shift; their XP and rank; the next optional mission from `lab.py status`; and: "Type `/my-cv` to see the skills you touched." Never make the optional missions sound like homework.
