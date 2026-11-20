---
description: Generate your SRE Lab Passport and badge (self-generated; a mentor can confirm it live)
argument-hint: your full name as it should appear on the passport
---
**Mode guard:** if the active mode is not **SRE Lab Guide**, stop here. Tell the student: "Please pick SRE Lab Guide in the mode picker (Ctrl+. on Windows, Cmd+. on Mac), then type this command again." Do nothing else.

The student's full name is the text they typed after the command name. If there is none, ask: "What is your full name, exactly as it should appear on the passport?"

Windows: `python scripts/lab.py ...` (never `python3`). Mac/Linux: `python3 scripts/lab.py ...`.

1. Run `lab.py check --all` first, so every mission that is done is recorded.
2. Run `lab.py proof --name "<the student's full name>"`.
3. Open lab-proof/PASSPORT.md with the student and explain, honestly:
   - the badge (lab-proof/badge.svg) shows their rank and XP;
   - the passport has a **Skills practised hands-on** section they can reuse on a CV (`/my-cv` helps them word it);
   - the passport is **self-generated**, a record and not a certificate: it lists the missions `lab.py` found evidence for on their own laptop. evidence.json carries a fingerprint (a checksum), not a signature. If a mentor or instructor wants to confirm it, they do a short live check-off (`lab.py verify`, run only when they ask);
   - to share it: commit lab-proof/ to their fork. First propose `git remote -v` and check that `origin` is the student's own fork, not the original repository (if it is the original, do mission M09b first and never push). Then propose `git add lab-proof`, then `git commit -m "Add my SRE lab passport"`, then `git push`, one at a time; each is a step the student approves. Then they can link PASSPORT.md on their profile or CV.
4. If they reached the summit, congratulate them by name: they are **On-Call Ready**. Suggest `/interview` to rehearse, and remind them honestly that this is hands-on evidence for a junior role, not a senior title.
