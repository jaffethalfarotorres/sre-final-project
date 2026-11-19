# Start the lab with IBM Bob

## Your first on-call shift, in one sitting

**One sitting, about 2-3 hours, mostly installs.** You paste one message into IBM Bob. Bob installs the tools on your laptop, starts a small online shop called **Nimbus Store**, and walks you through your **first on-call shift**: you watch the shop, fire a real alert, get it on your phone, and investigate it with an AI that is not allowed to change anything. Nobody grades it. It is a friendly first taste of SRE (Site Reliability Engineering).

**No experience needed.** Last week Nimbus Store went down for an hour, and nobody noticed until customers complained. Today you make sure that does not happen again. **Bob** (IBM Bob, an AI assistant) is **your AI pair**: it explains every step and proposes every command, but it never changes anything without your OK.

### The 9 steps of your shift (about 165 minutes)

1. **Meet your AI partner** (B00, 15 min): how you and Bob work together, and how you stay in control.
2. **Boot the lab** (M00, 60 min): Bob installs the tools and starts the shop. Mostly waiting.
3. **Instrument a service** (M01, 10 min): see the shop's numbers and the path of one request.
4. **Dashboards as code** (M04, 10 min): open the live charts in Grafana.
5. **First alert** (M05, 15 min): break the shop on purpose and watch the alarm fire.
6. **Alerts on your phone** (N01, 10 min): get that alarm as a push on your phone, with the free ntfy app.
7. **Follow the trace** (M07, 10 min): find the error in the logs and the failed request in Jaeger.
8. **AI on call** (M17, 20 min): Bob investigates the alert in a read-only mode and writes a report.
9. **Injection proof** (M18, 15 min): a fake attack hides in a log line; Bob must spot it and not obey it.

When all 9 are done: **SHIFT COMPLETE**, and you earn the **First On-Call Shift** badge. Everything after that is optional: see [Keep exploring](#keep-exploring-optional).

> Don't have IBM Bob? IBMers use their IBM Bob entitlement. Everyone else can use the trial at [bob.ibm.com](https://bob.ibm.com). No Bob at all? Follow the [step-by-step guide](GUIDE.md) by hand, or use Claude Code with `/lab`.

## What you need
- A Mac or a Windows laptop with **at least 8 GB of memory** (16 GB is better) and **20 GB of free disk**. With 8 GB you run the core stack only, with no add-ons (Mac: see the Mac box below).
- Administrator rights on your laptop (to install tools) and **one sitting of about 2-3 hours**. Most of it is waiting while things install.
- IBM Bob installed and signed in, a free [GitHub](https://github.com) account, and (for step 6) your phone.

<details>
<summary><b>New words? Open this first (1 minute)</b></summary>

| Word | Plain meaning |
| --- | --- |
| **Repository (repo)** | A project folder whose full history is kept online, on GitHub. |
| **Fork** | Your own copy of someone else's repository, under your GitHub account. You can change it freely. |
| **Clone** | Download a repository to your laptop. |
| **Terminal** | A window where you type commands. Bob has one built in. On Windows it is **PowerShell**. |
| **Command** | One line of text that tells the computer to do one thing. |
| **Mode** | Bob's "job hat". Each mode allows different things. You pick it in the mode picker under the chat box. |
| **Approve / Reject** | The two buttons Bob shows before it runs anything. Nothing runs until you click Approve. |

</details>

## Stay in control (read before Step 1)

> **You are the one in charge, not Bob.** Bob proposes; you approve. A few rules keep your laptop safe:
>
> - **Never** turn on auto-approve for **Execute** (running commands) or **Write** (changing files).
> - **Never** click "always allow" for `python`, `powershell`, `bash`, `curl`, `kubectl`, `git` or `winget`. Approve each command one by one.
> - **Reject** any command that contains `|`, `;`, `iex`, `-c` as a separate word (like `python -c`), `--kubeconfig`, `delete`, or a web address you do not recognise. Then ask Bob: "Why do you need this?" (Longer words that only start with `-c`, like `--clone` in Step 1, are fine.)
> - Two known exceptions are safe: the **PATH refresh line** in Step 1 (its `;` is inside quotes), and on Mac the official **Homebrew installer** from [brew.sh](https://brew.sh) (it uses `-c` and an address starting with `https://raw.githubusercontent.com/Homebrew/`). The two Mac `brew shellenv` lines in Step 1 are also install steps from this page: they only add Homebrew to your PATH.
> - Only the lab's own commands should run: `python scripts\lab.py ...` and `scripts\*.ps1` in Windows PowerShell; `python3 scripts/lab.py ...` and `scripts/*.sh` on Mac and in Ubuntu (WSL); and the install steps in this page.
> - A clean-up step that **deletes** something is fine only after Bob has told you what will be lost and you have typed "yes".
> - If something feels wrong, click **Reject**. Nothing breaks when you say no.

<details>
<summary><b>Optional extra lock: a deny list for Bob</b></summary>

In Bob's settings, add this deny list. Bob then refuses these commands even if you click Approve by mistake. If your Bob version names the setting differently, look for the denied commands setting. Never add an "allow" list instead.

```json
"deniedCommands": ["iex", "Invoke-Expression", "curl | ", "python -c", "python3 -c", "kubectl delete", "minikube delete", "git push --force", "Remove-Item -Recurse", "rm -rf", "--kubeconfig"]
```

</details>

### Data rules for IBMers
- Use your IBM Bob entitlement for this lab.
- **Never** paste client data, your w3 password, IBM tokens or screenshots of internal IBM tools into Bob or into this repository.
- To get alerts on your phone on an IBM laptop, ask Bob to run `python scripts\notify_setup.py` (ntfy: no account, section 6-0 of the [guide](GUIDE.md)). Slack and email (sections 6a-6e) need a **personal** Slack workspace and a **personal** Gmail, which IBM laptops usually block. Never IBM Slack or IBM mail.

<details>
<summary><b>On an IBM-managed laptop? Read this before the lab day</b></summary>

- **Preflight first:** once the lab is on your laptop, Bob runs `python scripts\preflight.py`. It only reads your laptop and says what is missing. If IBM IT has to unlock something, send them [IT-REQUEST.md](IT-REQUEST.md).
- **Admin rights:** installers need them. Request temporary administrator rights through IBM's usual IT help process **before** the lab.
- **Container engine:** Docker Desktop needs a paid licence in large companies ([licence terms](https://docs.docker.com/subscription/desktop-license/)). Ask your manager or IT which one is approved. If Docker Desktop is not licensed for you, use [Rancher Desktop](https://rancherdesktop.io/) with the **dockerd (moby)** engine.
- **VPN:** if downloads fail or hang, disconnect the VPN during installs (if your IBM policy allows), then reconnect.
- **"Running scripts is disabled on this system":** the lab always runs scripts with `-ExecutionPolicy Bypass`, which works for one script only and changes no setting. If it is still blocked, the policy is locked by IT: see [IT-REQUEST.md](IT-REQUEST.md).

More detail: [On an IBM-managed laptop](GUIDE.md#on-an-ibm-managed-laptop) in the guide.

</details>

<details>
<summary><b>On a Mac? Read this before the lab day</b></summary>

- **Homebrew PATH (Apple silicon, M1 to M4):** after Homebrew installs, run `eval "$(/opt/homebrew/bin/brew shellenv)"` and add the same line to `~/.zprofile` (Step 1 shows both commands). Without it, Terminal does not find `brew`, and `python3` is Apple's old Python.
- **Python 3.10 or newer:** run `python3 --version`. Apple's Python 3.9 is too old for the tests. Install a newer one with `brew install python@3.12`, then use `python3.12`.
- **8 GB Mac:** start Colima yourself with `colima start --cpu 2 --memory 4 --disk 60` before the deploy, and run **no add-ons**. (The deploy script starts Colima with 6 GB only if it is not running yet.)
- **Container engine:** on a Mac the lab uses Colima, not Docker Desktop, so no Docker licence is needed.
- More detail: [Mac](GUIDE.md#mac) in the guide.

</details>

## Step 1: paste this into IBM Bob

1. Open IBM Bob. Open any empty folder (for example a new folder called `labs` in your home folder).
2. In the mode picker, choose **Agent**.
3. Copy and paste this message exactly:

```text
Set up the SRE Academy lab for me. I am new to this, so explain each step in simple words and propose one command at a time.
1. Find out if I am on Windows or Mac.
2. Install git, Python 3.12 and the GitHub command line (gh) if they are missing.
   Windows: winget install -e --id Git.Git, then Python.Python.3.12 --scope user, then GitHub.cli.
   If winget is not available (common on IBM laptops), tell me, and I will install Git from
   https://git-scm.com/download/win and Python from https://www.python.org/downloads/windows/
   ("Install for me only", tick "Add python.exe to PATH") myself.
   After each winget install, refresh PATH in the same terminal:
   $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
   On Windows always use "python", never "python3" (python3 opens the Microsoft Store).
   Mac: xcode-select --install for git; then Homebrew.
   Apple silicon Mac (M1 to M4): after Homebrew, add it to PATH with two commands:
   eval "$(/opt/homebrew/bin/brew shellenv)"
   echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
   Then brew install python gh, and check python3 --version.
   It must be 3.10 or newer. If it shows 3.9 (Apple's own Python, too old):
   brew install python@3.12, and use python3.12 instead of python3.
3. Ask me to run "gh auth login" myself (GitHub.com, HTTPS, Login with a web browser). That is my step; wait until I say done.
4. Go to my home folder and run: gh repo fork jaffethalfarotorres/sre-final-project --clone
5. Tell me how to open the sre-final-project folder in Bob, then stop.
```

4. Bob proposes each command and **waits for you**. Read the one-line explanation, then click **Approve**.
   - The first time, Bob may show **"I understand the risks"**. That is normal: it means "you will approve each command". Accept it, and keep the rules above.
   - An installer may ask for admin rights or show a Windows pop-up. Click it yourself, then tell Bob "done".

**What is the fork for?** `gh repo fork ... --clone` makes **your own copy** of the lab on GitHub (the *fork*) and downloads it to your laptop (the *clone*). Your work and your proof live in your copy, so you can share it later. The `gh auth login` step tells GitHub who you are; only you can do it, in your browser.

## Step 2: open the lab and meet Bob, your AI pair

1. Open the **`sre-final-project` folder itself**: **File > Open Folder…**, then choose `sre-final-project`. In the Explorer on the left, the top line must say `SRE-FINAL-PROJECT`, with `AGENTS.md`, `README.md` and the `scripts` folder right underneath.
   > **Important:** do not open a parent folder that only *contains* `sre-final-project`. Bob reads the lab rules, the **SRE Lab Guide** mode and the `/start-lab` command only from the top of the open folder.
2. If Bob asks whether you **trust** this folder, say yes. The rules Bob follows are in `AGENTS.md` and the `.bob/` folder, and you can read them.
3. Open Bob's **Permissions** (auto-approve) menu. Tick **Read** and **MCP** only. Leave **Execute** and **Write** off. (MCP is how Bob reads your dashboards. The **grafana** server stays off until step 8 of your shift, M17, when Bob shows you how to switch it on.)
4. In the mode picker, choose **SRE Lab Guide**. Type `/start-lab` and press Enter.

Bob then runs the **setup kit** (`scripts\install-tools.ps1`, Mac `scripts/install-tools.sh`): one approved command that installs only the tools that are missing, even on IBM laptops without winget. Bob also runs the **preflight** (`python scripts\preflight.py`, Mac `python3 scripts/preflight.py`). It only reads your laptop and tells you what is missing. Then Bob walks you through the 9 steps of your shift: it explains each idea in plain words, proposes one approved command at a time, checks each step on your real laptop, and asks a short quiz.

## Step 3: your shift starts with B00

The first step, **B00 "Meet your AI partner"**, is your first minutes on the team. Bob explains how you two work together, and you answer **5 short quiz questions**. The **Stay in control** box at the top of this page is part of it: read it with Bob before you answer. Then Bob takes you through the other 8 steps, one at a time. Type `/lab-status` at any moment to see how far you are and how many minutes are left.

## Keep exploring (optional)

Your shift is complete? Well done. You can stop here; that is a perfectly good ending. If you are curious, there is much more in this repository, any time, at your own pace. Type `/next-mission` and Bob picks it up from where you are. The deeper lab parts, one topic at a time, are in the [lab guide](labs/README.md).

### The bigger map: 8 camps

Your shift touched a few missions from a bigger map, the **Road to Junior SRE**. It has **8 camps**, from Career Changer to the summit **On-Call Ready**. Each camp gives Nimbus a real new capability on your laptop and teaches you **one SRE principle**.

| Camp | What Nimbus can do after it | The SRE principle you learn |
| --- | --- | --- |
| 0. Orientation Day | You and Bob know the rules: Bob proposes, you approve | Humans stay in control: automation and AI propose, people approve |
| 1. The Engine Room | Nimbus runs on Kubernetes and updates with zero downtime | Small, safe, repeatable changes |
| 2. The Watchtower | Nimbus sees its own health and raises an alarm when users suffer | Monitor what users feel; alert only when a human must act |
| 3. The War Room | Nimbus has a reliability promise, an error budget and an incident process | Embrace risk with SLOs and error budgets; learn without blame |
| 4. The Detective Agency | Any failing request can be traced from the alarm to the exact evidence | Explain any failure from evidence, not guesses |
| 5. The Robot Workshop | Nimbus is rebuilt from code, tested on every change, and diagnoses itself | Eliminate toil: automate and keep infrastructure in code |
| 6. The Proving Grounds | Nimbus survives crashes and bad releases, and refuses unsafe deployments | Changes are gradual, reversible and tested by breaking things on purpose |
| 7. The AI Command Center | **On-Call Ready**: you lead incidents with an AI teammate you can trust and verify | Trust, but verify: AI helps only with least privilege and human judgement |

- **Clearing a camp is a LEVEL UP.** Bob then shows you three things: the SRE principle of that camp, the **new skills for your CV**, and **one interview question** to practise.
- **About 30 missions.** The core missions go from "Meet your AI partner" to "Watching the model", then the capstone **M27 "Game day captain"**, where you lead a practice incident. One core mission, **M09b "Join the guild (fork the repo)"**, checks that you work in your own copy of the project. There are also 6 optional add-ons for laptops with more memory.
- **XP and ranks:** Career Changer (0 XP) → Tech Apprentice (500) → SRE Intern (1300) → Junior SRE Candidate (2300) → Junior SRE Lab Graduate (3300). `/lab-status` shows your XP and what comes next.
- **Quizzes:** you get full XP on the first try and half on the second. After that the question locks. Quizzes are for learning: they never block a mission and nothing is graded. Bob never tells you the answer.
- **Mission Control:** type `/mission-control`. Bob opens a visual map with your camp, what Nimbus can do now, your next mission, your badges, a **"Your CV so far"** panel and an **"Interview practice"** panel.
- **Two modes, two jobs:** *SRE Lab Guide* runs lab commands **you approve**. *SRE Triage (read-only)* is the on-call helper for the incident missions: it investigates but can never change anything.

### Portfolio projects

Want something extra to show in an interview? Pick one or more. Each one is your own work, not a copy of the lab, and earns a badge.

| Project | What you build | Badge |
| --- | --- | --- |
| **P-DASH** | Your own Grafana dashboard | Dashboard Builder |
| **P-ENV** | A second `dev` environment, made from code with a Terraform workspace | Environment Builder |
| **P-RUNBOOK** | A new runbook, linked from an alert (its `runbook_url`) | Runbook Author |
| **P-POLICY** | A new Kyverno rule (a ClusterPolicy) that blocks an unsafe setting | Guardrail Author |

Take a screenshot, keep the file in your fork, and you have a real story to tell: "here is what I built, and why".

### Your CV and interview practice

- **`/my-cv`**: Bob runs `python scripts\lab.py cv` (Mac and Ubuntu: `python3 scripts/lab.py cv`). You see the skills you earned, the principles you practised and the interview questions of the camps you cleared. Then Bob helps you turn them into CV or LinkedIn lines in plain English. Bob only writes what you actually did in the lab. It never invents experience.
- **`/interview`**: Bob plays a friendly interviewer for a junior SRE or DevOps role. It asks the questions of the camps you cleared, one at a time. After each answer you get kind feedback and a model answer that points to what you really did in the lab.

### Your proof (optional)

A mission counts only when `scripts/lab.py` finds the evidence on your laptop.

If you climb all the camps, type `/lab-proof Your Name`. Bob creates `lab-proof/PASSPORT.md` (your missions, dates, evidence and the **skills** you earned), a badge image and a **fingerprint** of the evidence. The fingerprint shows if the file was edited later; it is **not a signature**. The passport is a **self-generated record, not a certificate**. A mentor can confirm it in a short live check (`lab.py verify`). Commit it to your fork and share the link, for example next to your CV.

### Commands you can type to Bob

| Command | What it does |
| --- | --- |
| `/start-lab` | Start your shift, or continue where you left off |
| `/next-mission` | Explain and begin the next mission |
| `/check-mission M05` | Check a mission on your laptop and collect the XP |
| `/hint` | A small hint, without spoiling the answer |
| `/explain error budget` | Explain any idea in plain words |
| `/lab-status` | How far you are in your shift, your XP and what comes next |
| `/mission-control` | Open the visual map: your shift and everything after it |
| `/save-triage` | Save the SRE Triage answer as a report (missions M17 and M18). Type it in **SRE Lab Guide** mode |
| `/my-cv` | Your skills so far, turned into CV and LinkedIn lines |
| `/interview` | Practise a junior SRE interview with Bob |
| `/lab-proof Your Name` | Create your SRE Lab Passport |

## If something goes wrong

| What you see | What to do |
| --- | --- |
| **SRE Lab Guide** is missing from the mode picker, or `/start-lab` is "not found" | Check you opened the `sre-final-project` folder **itself** (Step 2.1). Then type `/permissions`, choose **Trust** for this folder, and reload Bob (Command Palette > **Developer: Reload Window**). |
| Mac: `command not found: brew`, or `python3 --version` shows 3.9 | Run the two `brew shellenv` lines from Step 1, open a new Terminal, and check again. Still 3.9? `brew install python@3.12` and use `python3.12`. |
| `python` opens the Microsoft Store | Install Python with `winget install -e --id Python.Python.3.12 --scope user`, refresh PATH (the line in Step 1), and use `python`, never `python3`. |
| "not recognized" right after an install | The terminal has an old PATH. Run the PATH refresh line from Step 1, or open a new terminal. |
| A command keeps running and the chat seems stuck | Some steps take minutes (the alert test takes about 4). That is normal. Wait for Bob to say it finished. |
| Laptop slow, or pods stay "Pending" | You probably ran two add-ons at once. Ask Bob to clean up the last add-on. |
| The preflight prints FAIL | Read the fix on that line with Bob. If an IBM-managed laptop blocks it, send [IT-REQUEST.md](IT-REQUEST.md) to IBM IT. |
| Anything else | Ask Bob: "This failed, what does it mean?" It reads the error with you and uses the [guide's troubleshooting table](GUIDE.md#troubleshooting). Still stuck? Open an issue with the **Bug report** form, or ask a mentor. |
