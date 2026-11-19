---
description: Show the next step of your First on-call shift (or, after it, the next optional mission) and start teaching it
argument-hint: optional mission id, for example M05
---
**Mode guard:** if the active mode is not **SRE Lab Guide**, stop here. Tell the student: "Please pick SRE Lab Guide in the mode picker (Ctrl+. on Windows, Cmd+. on Mac), then type this command again." Do nothing else.

Windows: `python scripts\lab.py ...` (never `python3`). Mac/Linux: `python3 scripts/lab.py ...`.

If the student typed a mission id after the command name, run `lab.py show <ID>` for that mission. Otherwise run `lab.py journey`: while the **First on-call shift** is not complete, use the next step it names. Once the shift is complete, run `lab.py status` and use the next mission it names; that is optional "keep exploring" work, so say so kindly.

Tell the student the mission title, the XP, and the goal in one friendly sentence. Add one line on why it matters at work (for example: "On-call SREs do this every week."). During the shift, also say which step it is (for example "step 5 of 9") and about how many minutes it takes. If it is a portfolio project (P-DASH, P-ENV, P-RUNBOOK, P-POLICY), say it is optional and a good piece to show in interviews. Teach it with the loop in .bob/rules-sre-lab-guide/10-game-master.md: for a shift step, follow its section "The First on-call shift, step by step"; otherwise open the guide file the mission points to and find the matching module. Explain the idea in two short sentences, then one approved command at a time. If the mission is an add-on, check memory first and remind them to clean up after the check. For M17 and M18, follow the game-master steps on the grafana MCP server and switching to SRE Triage.
