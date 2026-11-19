# Start the lab with IBM Bob

**No experience needed.** You will paste one message into IBM Bob. Bob installs what you need, sets up the lab on your laptop and then guides you mission by mission. You learn the SRE tools, the concepts behind them, and how to work with an AI partner, all at the same time. At the end you get a **verified SRE Lab Passport** you can share.

> Don't have IBM Bob? IBMers get it through IBM; everyone else can use the trial at [bob.ibm.com](https://bob.ibm.com). No Bob at all? Follow the [step-by-step guide](GUIDE.md) by hand, or use Claude Code with `/lab`.

## What you need
- A Mac or a Windows laptop with **at least 8 GB of memory** (16 GB is better) and **20 GB of free disk**.
- Administrator rights on your laptop (to install tools) and about **2 hours** for the setup.
- IBM Bob installed and signed in.

## Step 1: paste this into IBM Bob

1. Open IBM Bob and open any empty folder (for example a new folder called `labs` in your home folder).
2. In the chat, choose the **Agent** mode.
3. Copy and paste this message exactly:

```text
Set up the SRE Academy lab for me. I am new to this, so explain each step in simple words.
1. Check whether git is installed; if not, install it (on Windows with winget, on Mac with the Xcode command line tools).
2. Clone https://github.com/jaffethalfarotorres/sre-final-project.git into my home folder.
3. Tell me how to open that folder in Bob, then stop.
```

4. Bob proposes each command and **waits for you to approve it**. Read the one-line explanation, then click approve. That is how you stay in control.

## Step 2: open the lab and meet your guide

1. Open the `sre-final-project` folder in Bob (Bob tells you how). If Bob asks whether you trust the folder, it is safe to say yes for this lab: the rules Bob will follow are in `AGENTS.md` and the `.bob/` folder, and you can read them.
2. In the mode picker, choose **SRE Lab Guide**.
3. Type `/start-lab` and press Enter.

From now on Bob is your tutor. It will:
- explain every idea in plain words before any command;
- install the tools (Docker, Minikube, kubectl and friends) one approved command at a time;
- deploy the lab and open the dashboards with you;
- run each **mission**, check it on your real cluster, give you **XP** and **badges**, and ask a short quiz.

## Commands you can type to Bob

| Command | What it does |
| --- | --- |
| `/start-lab` | Start, or continue where you left off |
| `/next-mission` | Explain and begin the next mission |
| `/check-mission M05` | Verify a mission on your cluster and collect the XP |
| `/hint` | A small hint, without spoiling the answer |
| `/explain error budget` | Explain any concept in plain words |
| `/lab-status` | Your level, XP, badges and next mission |
| `/lab-proof Your Name` | Create your shareable SRE Lab Passport |

## How the game works

- **26 missions** grouped in 8 parts, from "Meet your AI partner" to an AI-assisted **game day**.
- **Levels:** SRE Intern → Junior SRE (500 XP) → SRE (1,300) → Senior SRE (2,300) → Staff SRE (3,300).
- **Badges** such as *First Page*, *Budget Keeper*, *Rollback Hero*, *Chaos Survivor*, *Injection Proof*.
- **No cheating needed, no cheating possible:** a mission only counts when `scripts/lab.py` finds the evidence on your own cluster or repository.
- **Two modes, two jobs:** *SRE Lab Guide* may run lab commands **you approve**. *SRE Triage (read-only)* is the on-call assistant you use in the incident missions: it investigates but can never change anything. Learning that difference is part of the lab.

## Your proof

When you finish the core missions, type `/lab-proof Your Name`. Bob creates `lab-proof/PASSPORT.md` (your missions, dates and evidence), a badge image and a hash of the evidence. Commit it to your own fork of the repository and share the link on your profile or CV.

## If something goes wrong
- Ask Bob: "This failed, what does it mean?" It will read the error with you and use the troubleshooting tables in the guide.
- Your laptop is slow or pods stay "Pending": you probably ran two add-ons at once. Ask Bob to clean up the last add-on.
- Still stuck: open an issue on the repository with the **Bug report** form, or ask your professor.
