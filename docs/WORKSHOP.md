# Run this lab as a workshop (for the person leading it)

One facilitator, about 30 people, one day. Everybody sets up their own copy of the lab on their own laptop **at the same time**, with an AI coding agent (IBM Bob) doing the typing. Then the group tours the tools together, fires a real alert, and explores.

> **Honest status.** Nothing here has been run with a group yet. Every duration below is an **estimate** until you run a pilot. Section [Measure it](#measure-it-do-not-guess) shows how to replace each estimate with a measured number.

The learners only ever see three things: the Bob chat, five browser tabs, and your one-page agenda. They never need to open a folder; the [README](../README.md) has their step-by-step.

## Before the day (send 3-5 days ahead, resend the day before)

| Everyone | Why |
|---|---|
| Bob installed, signed in, can clone from GitHub | The agent does the setup |
| A container engine installed and started once (Docker Desktop, or Rancher Desktop) | Needs admin rights; IBM laptops: send [docs/IT-REQUEST.md](IT-REQUEST.md) to IT early |
| 16 GB RAM (8 GB works slowly), 25 GB free disk | Minikube plus the monitoring stack |
| `python scripts/preflight.py` run once, result sent back | You see who is blocked **before** the day |
| The free ntfy app on a phone (optional) | Only for the phone-alert stop |

**Best trick:** ask everyone to run `python scripts/lab_up.py` at home, on a good network, 1-2 days before. Every step is idempotent, so on the day it finishes in seconds and the workshop starts from a running lab. The first run downloads about 10 container images plus the tools; 30 people doing that on one venue wifi is the biggest risk of the day.

## Agenda (about 5 hours, all minutes estimated)

| Block | Min | What happens | Checkpoint you can see |
|---|---|---|---|
| 0. Welcome | 20 | Why SRE, what the lab is, safety rules (Bob proposes, you approve; nothing leaves the laptop) | Everyone has the repo open in Bob |
| 1. Setup | 50 | Everyone sends one message to Bob: "Set up the lab and show me every tool working." | `LAB_UP RESULT: DONE` on every screen |
| 2. Catch-up | 10 | Stuck people get help; the rest read [docs/EXPLORE.md](EXPLORE.md) intro | Hands up count: how many not DONE |
| 3. Tour, stops 1-5 | 45 | Bob opens each page: shop, Prometheus, Grafana, Jaeger, Alertmanager. About 9 min per tool: look, click, ask Bob | Each person finds one thing per tool (see below) |
| Break | 15 | | |
| 4. Alert drill | 30 | `lab_up.py --drill` breaks the shop on purpose; follow the alert: Grafana, Prometheus, Alertmanager. It fires about 2.5 min in (one measured run) | `HighErrorRate is firing` on every screen |
| 5. Explore | 60 | Free time with Bob: [docs/EXPLORE.md](EXPLORE.md), "what if" questions, [AI triage](AI-SRE.md) of the drill alert | One question each that Bob answered |
| 6. Wrap-up | 20 | What clicked, what lost you, five feedback questions below | Feedback collected |

**What to look for in each tool** (three minutes each, the rest is questions to Bob):
- **Shop:** click around; every click is a request that becomes a number, a log line and a trace.
- **Prometheus** `/targets`: every row UP. Run one query.
- **Grafana** (`admin` / `admin`): open Golden Signals, then Explore with the Loki data source.
- **Jaeger:** open one trace and read the spans.
- **Alertmanager:** the always-on demo alert is expected; that is the pipeline test.

## If people are behind

- **Not DONE at checkpoint 1:** they keep going; `lab_up.py` is resumable and runs in the background. Pair them with a neighbour for the tour.
- **`NEEDS_HUMAN`:** almost always the container engine (licence, first start) or an admin prompt. Bob says exactly what to click.
- **More than about 5 laptops `NEEDS_HUMAN` or `FAILED`:** stop the block, fix the common cause once (see below), then continue.
- **Still not working at the drill:** they watch the drill on your screen. Keep a demo cluster running on your laptop as the fallback.
- To triage fast, ask people to read out the **result word** from `python scripts/lab_up.py --status`: DONE, NOT_FINISHED, NEEDS_HUMAN or FAILED.

## What can stall many people at once

| Risk | What you see | Cheapest fix |
|---|---|---|
| Docker Hub throttles the venue's shared IP (30 laptops, about 270 image pulls) | Pods stuck in `ImagePullBackOff`, setup ends "still not ready after 15 minutes" | Pre-run `lab_up.py` at home (above); or pre-pull with `docker save` tarballs on a USB stick; or a free Docker Hub login per person. Check the current anonymous limits before the day |
| Wifi saturated | Steps hit their timeouts | Same: do the first run before the day |
| 8 GB laptops | Slow, restarts | Pair them with a 16 GB laptop |
| Windows memory limits | Minikube will not start | Raise the container engine's memory in its settings |
| Add-ons (AWX, Argo CD, Kyverno, chaos, canary) | Heavy, not needed | Out of scope for the day: core stack only |

## Measure it, do not guess

Two real cold runs (one IBM-managed Windows laptop, one Mac), then one run with 5-10 laptops on the venue network. The lab now records how long each step took:

```powershell
python scripts/lab_up.py --status
```

It prints `step times:` and `run time:` for the last run (also in `.lab/status.json`). Put the real minutes into the agenda table and delete the word "estimated".

After the workshop, ask every person for their setup minutes and the result word; you then have measured numbers for the next group.

## Five feedback questions

1. Which tool was clearest? 2. Which step lost you? 3. Did Bob explain in plain words? 4. Would you use this at work? 5. One thing to change.

## Reusing this for another tool set

The lab is data plus a small engine: the tour is a list in `scripts/lab_up.py` (`TOUR`: title, page, what to say, ready check) and the optional game is in `lab/missions.json` (see [docs/JOURNEY.md](JOURNEY.md)). A new workshop keeps this agenda table and swaps the stops. Each block needs the same five things: goal, the one thing the learner types, a checkpoint you can see, what to do if behind, minutes (estimated or measured).
