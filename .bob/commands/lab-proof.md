---
description: Generate your shareable SRE Lab Passport and badge
argument-hint: your full name as it should appear on the passport
---
Run `python3 scripts/lab.py check --all` first, so every mission that is done is recorded. Then run `python3 scripts/lab.py proof --name "$ARGUMENTS"` (Windows: `python scripts\lab.py ...`).

Open lab-proof/PASSPORT.md with the student and explain:
- the badge (lab-proof/badge.svg) shows their level and XP;
- every mission listed was verified automatically on their own cluster, and evidence.json carries a SHA-256 hash of the evidence;
- to share it: commit lab-proof/ to their fork (`git add lab-proof && git commit -m "Add my SRE lab passport" && git push`), then link PASSPORT.md on their profile or CV. The push is something the student runs and approves.
