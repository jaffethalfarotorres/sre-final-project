---
description: Turn the skills you earned in the lab into honest CV and LinkedIn lines
argument-hint: optional, the role you are aiming for, for example "junior SRE" or "DevOps"
---
**Mode guard:** if the active mode is not **SRE Lab Guide**, stop here. Tell the student: "Please pick SRE Lab Guide in the mode picker (Ctrl+. on Windows, Cmd+. on Mac), then type /my-cv again." Do nothing else.

Windows: `python scripts\lab.py ...` (never `python3`). Mac/Linux: `python3 scripts/lab.py ...`.

The role the student is aiming for is the text they typed after the command name. If there is none, ask: "Which kind of role are you aiming for: junior SRE, DevOps, cloud or operations?"

1. Run `lab.py cv`. It lists the skills from the camps they cleared, any portfolio projects they finished, the SRE principles they practised and the interview questions for those camps. If it says no camp is cleared yet, encourage them to finish mission B00 and stop.
2. Write, in plain English:
   - **3 to 6 CV bullet lines**, each one starting with a verb and naming what they actually did in the lab, for example: "Deployed a small web shop on Kubernetes (Minikube) with zero-downtime rolling updates, in a hands-on SRE lab." Mention Nimbus Store as a lab project, never as a real customer system.
   - **One short LinkedIn "About" paragraph** (3 or 4 sentences): their move from a non-technical team into tech, what they built in the lab, and the kind of role they want.
   - **A skills list** copied from `lab.py cv`, using the real tool names.
3. **Honesty rules (always):**
   - Use only skills and missions that `lab.py cv` lists. Never invent experience, years, production work, certifications, job titles or results they did not get.
   - Call it what it is: a hands-on lab on their own laptop. Words like "lab", "hands-on project" or "practice environment" are correct; "production" or "at a client" are not.
   - Do not inflate the level. This is evidence for a junior role, not senior experience.
   - Never invent facts about IBM hiring, roles, salaries, bands or internal programs. For those, suggest they ask their manager, a mentor or HR.
4. Show the text in the chat only. Do not write it to a file. The student copies what they like into their own CV or profile. If they have lab-proof/PASSPORT.md, suggest linking it as evidence, and remind them it is a self-generated record, not a certificate.
5. End with one line: "Want to rehearse explaining these in an interview? Type `/interview`."
