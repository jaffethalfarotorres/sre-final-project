# The Road to Junior SRE (optional guided path)

This page holds the longer, optional, game-like path through the lab: camps, ranks, badges, portfolio projects, and how another team can reuse the engine. It moved here from the README so the front page stays short. Start with the [README](../README.md); come back here when you want more structure.

## Keep exploring (optional, at your own pace)

The shift is the whole ice-breaker. If you liked it, the rest of the repository is there for you, with no deadline and no grade. Your agent stays your guide: in IBM Bob, choose the **SRE Lab Guide** mode and type `/next-mission`; in Claude Code, type `/lab`.

| You are... | Start with |
| --- | --- |
| A student with IBM Bob | [BOB-QUICKSTART.md](BOB-QUICKSTART.md): open the folder in Bob, choose the **SRE Lab Guide** mode, type `/start-lab` |
| A student without Bob | The [step-by-step guide for Mac and Windows](GUIDE.md), then `python3 scripts/lab.py status` (Windows: `python scripts/lab.py status`; or `/lab` in Claude Code) |
| A professor | The [lab guide](labs/README.md) (the shift, then the deeper parts with objectives and timing), the [course map](COURSE-MAP.md) and the [instructor notes](instructor/README.md) |

A mission counts only when [`scripts/lab.py`](../scripts/lab.py) finds the evidence on your own cluster or fork. Quizzes are for learning and never count toward a grade.

### The journey: Road to Junior SRE

The full lab is a longer climb, built for IBMers from non-technical teams who want to move into technical roles such as junior SRE, DevOps, cloud or operations. With **your AI pair**, your AI coding agent (fast and helpful, never allowed to change anything without your OK), you climb camp by camp from **Career Changer** to the last camp, **On-Call Ready**. Each camp gives Nimbus a real capability, teaches one SRE principle, lists skills you can name on a CV and adds one interview question to rehearse with your agent (`lab.py cv`; in Bob: `/my-cv` and `/interview`). The first on-call shift already touches camps 0, 1, 2, 4 and 7. The lab gives hands-on evidence for junior roles; it does not claim to make anyone a senior engineer.

| Camp | SRE principle |
| --- | --- |
| 0. Orientation Day | Humans stay in control: automation and AI propose, people approve |
| 1. The Engine Room | Reliability starts with small, safe, repeatable changes |
| 2. The Watchtower | Monitor what users feel, and alert only when a human must act |
| 3. The War Room | Embrace risk with SLOs and error budgets; learn from incidents without blame |
| 4. The Detective Agency | Observability: explain any failure from evidence, not guesses |
| 5. The Robot Workshop | Eliminate toil: automate repetitive work and keep infrastructure in code |
| 6. The Proving Grounds | Release engineering: gradual, reversible changes, tested by breaking things on purpose |
| 7. The AI Command Center | Trust, but verify: AI helps on call only with least privilege and human judgement |

Ranks by XP: Career Changer (0) → Tech Apprentice (500) → SRE Intern (1300) → Junior SRE Candidate (2300) → Junior SRE Lab Graduate (3300). See every mission with `lab.py missions`: the 9 shift missions, the other core missions of the camps (for example M02, M03, M06, M09, M09b work in your own fork, M14), 6 optional add-ons (M10X, M13, M15, M19, M20, M21), 4 optional portfolio projects and the capstone game day **M27**. The mission IDs have gaps on purpose: M22 and M24 to M26 are not used.

**Portfolio projects** (optional, open to everyone, pieces to show in interviews):

| Project | What you build | Badge |
| --- | --- | --- |
| **P-DASH** | Your own Grafana dashboard | Dashboard Builder |
| **P-ENV** | A second `dev` environment with a Terraform workspace | Environment Builder |
| **P-RUNBOOK** | A new runbook linked from an alert's `runbook_url` | Runbook Author |
| **P-POLICY** | A new Kyverno ClusterPolicy | Guardrail Author |

**Badges** are earned along the way, for example *Paired with AI* (B00), *Hello, Cluster* (M00), *First Page* (M05), *AI Wrangler* (M17) and *Injection Proof* (M18) during the shift, then *Budget Keeper* (M06), *Storyteller* (M09), *Rollback Hero* (M14) and *Game Day Captain* (M27), plus one per add-on and portfolio project. `lab.py play` (Bob: `/mission-control`) opens Mission Control, the visual dashboard of the climb, with "Your CV so far" and "Interview practice" panels.

**For professors (optional):** `python3 scripts/cohort_report.py <folder of the students' lab-proof/evidence.json files>` (Windows: `python scripts\cohort_report.py ...`) gives a class summary: how many students reached On-Call Ready, the missions most students skipped and a fingerprint check of each file. The passport from `lab.py proof` is a self-generated record, not a certificate; its fingerprint is not a signature.

<a id="reuse-it-for-onboarding"></a>
## Reuse it for onboarding

Nothing in the shift is hard-coded to one class. The steps live in the catalog [`lab/missions.json`](../lab/missions.json), and [`scripts/lab.py`](../scripts/lab.py) reads them. That makes the repository a starting kit for a team that onboards **SRE new hires or interns**: fork it and define your own first-week journey.

- **A journey** is one entry in the catalog's `journeys` list: an `id` (here `first-shift`), a `name` ("First on-call shift"), a `summary` (one plain sentence for the student), an `achievement` (the badge recorded when every step is done, here "First On-Call Shift"), `default: true` for the journey `lab.py status` shows first, an optional `banner` (the big line at the end; "SHIFT COMPLETE" when it is left out), and `steps`, an ordered list where each step is `{"mission": "<mission id>", "minutes": <estimate>}`. `lab.py journey` shows the steps in order, the done marks and the minutes left. A step can only point to a mission that exists in the same catalog.
- **A mission** has an `id`, a `title`, a `goal`, a `guide` (the page that teaches it), `xp`, a `kind` (for example `core`, `addon` or `portfolio`), a `part` (its camp), `needs` (an add-on it depends on, or `null`), an optional `achievement`, an optional short `quiz` and a `check`: the name of the evidence test that marks it done, sometimes with one argument after a colon (for example `alert_fired:HighErrorRate`).
- **What needs no code:** a new journey that reuses existing missions, new titles, goals, guides and minutes, and new quiz questions. A quiz answer is stored as the first 16 characters of `sha256("<salt>:<mission id>:<question number>:<letter>")`, using the catalog's `salt`, so students and their AI cannot read it.
- **What needs a little Python:** a new kind of evidence. Each `check` name maps to one `check_<name>()` function in `scripts/lab.py` (for example `check_alert_fired`), so a new check is one new function and a test in `tests/`.
- **Keep the safety rules:** [`AGENTS.md`](../AGENTS.md) and the "Stay in control" box in B00 are what make it safe to let an AI guide a beginner. Keep them in your fork.

