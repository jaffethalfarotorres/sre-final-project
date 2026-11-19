# Step-by-step guide for Mac and Windows (no experience needed)

> **Using an AI coding agent?** (IBM Bob, recommended for IBMers, Claude Code, or another agent.) Then you do not need this page to start. Follow [BOB-QUICKSTART.md](BOB-QUICKSTART.md): the agent runs your **First on-call shift**, 9 short steps in one sitting of about 2-3 hours once the laptop is ready (an estimate, not yet timed), and does the setup below with you. This guide is the **by-hand version** of the same lab, and the reference the agent uses when something fails. Nothing here is graded. By hand, the shift ends at step 7: steps 8-9 (M17, M18) need an AI coding agent.

> **Using an AI coding agent on Windows?** Use the [Windows (PowerShell, used by IBM Bob)](#windows-powershell-used-by-ibm-bob) section and skip WSL. The agent's terminal is PowerShell (in IBM Bob always), so every command must work there.

> **Start with the preflight.** Run `python scripts\preflight.py` (Windows) or `python3 scripts/preflight.py` (Mac). It only reads your laptop and tells you what is missing. On an IBM-managed laptop, send [IT-REQUEST.md](IT-REQUEST.md) to IT before you start.

This guide explains the project in plain language and walks you through running it on a **Mac** or a **Windows** computer, one step at a time. You do not need to know Kubernetes or programming. If a word is new, check the [glossary](#glossary) at the end.

There are three install paths. Pick **one**:
- **Mac:** Colima, as in the SRE Academy course.
- **Windows with an AI coding agent (for example IBM Bob):** PowerShell and `winget`. This is the path the agent follows.
- **Windows by hand (no agent):** WSL2 with Ubuntu, as in the course.

If you already set up your computer for the course exercises, skip to [step 3](#3-download-and-start-the-project).

- [1. What is this project?](#1-what-is-this-project)
- [2. Install the tools (one time)](#2-install-the-tools-one-time)
  - [Mac](#mac)
  - [Windows (PowerShell, used by IBM Bob)](#windows-powershell-used-by-ibm-bob)
  - [Windows by hand (WSL2 and Ubuntu)](#windows-by-hand-wsl2-and-ubuntu)
  - [On an IBM-managed laptop](#on-an-ibm-managed-laptop)
- [3. Download and start the project](#3-download-and-start-the-project)
- [4. Look at the dashboards](#4-look-at-the-dashboards)
- [5. Make an alert fire](#5-make-an-alert-fire)
- [6. Optional: get alerts in Slack and email](#6-optional-get-alerts-in-slack-and-email)
- [7. Optional: publish the app image to Docker Hub](#7-optional-publish-the-app-image-to-docker-hub)
- [Your final project: what you must hand in](#your-final-project-what-you-must-hand-in)
- [8. Stop, restart and clean up](#8-stop-restart-and-clean-up)
- [Troubleshooting](#troubleshooting)
- [Glossary](#glossary)

---

## 1. What is this project?

Think of a small online shop that must stay up all the time. Site Reliability Engineers (SREs) keep services like that healthy. To do it they need three things:

1. **Measurements.** How many visitors arrive, how fast pages load, how many requests fail.
2. **A screen to watch them.** Charts that show at a glance whether things look normal.
3. **An alarm.** Something that warns a person when a problem starts, even when nobody is looking at the charts.

This project builds all three on your own computer:

| Piece | Plain-language role | Tool used |
| --- | --- | --- |
| The app | A tiny pretend shop. It answers requests and sometimes fails on purpose, so there is something to watch. | Python (Flask) |
| Traffic generator | A robot "customer" that visits the shop every 2 seconds. | curl |
| Prometheus | Collects the shop's measurements every few seconds and checks the alarm rules. | Prometheus |
| Grafana | Shows the measurements as live charts. | Grafana |
| Alertmanager | Decides who gets told about a problem, and sends Slack and email messages. | Alertmanager |
| Kubernetes (Minikube) | A "mini data center" inside your computer that runs and restarts all the pieces. | Minikube |

The alarm rules are:

| Alarm | When it goes off |
| --- | --- |
| `ServiceDown` | Prometheus cannot reach one copy (pod) of the shop for 1 minute. It checks each pod on its own, so one lost pod is enough. |
| `HighErrorRate` | More than 5% of requests fail over 5 minutes, while the shop gets real traffic (more than 0.2 requests per second), for 2 minutes. |
| `HighLatency` | The slowest 5% of `/store` requests take longer than half a second, for 2 minutes. |
| `SyntheticProbeFailing` | A robot check (blackbox exporter) cannot open the shop's home page: fewer than 90% of checks succeed over 2 minutes, for 2 minutes. |
| `ErrorBudgetFastBurn` | The shop is using up its monthly failure allowance more than 14.4 times faster than planned, over both the last hour and the last 5 minutes (see `docs/SLO.md`). At that speed the whole month's allowance is gone in about 2 days. This is urgent: it pages a person. |
| `ErrorBudgetSlowBurn` | The failure allowance is being spent more than 6 times faster than planned, over both the last 6 hours and the last 30 minutes. This is serious: fix it today, in working hours. A third, gentler rule opens a ticket when the burn stays above 1x for 3 days. |
| `ErrorBudgetExhausted` | The whole 30-day failure allowance is used up. On a fresh cluster this stays quiet until there are 500,000 requests of history (about 4.5 days of lab traffic). |
| `AlwaysFiringDemoAlert` | Always on. It only proves the alarm system works. |

Grafana adds two more rules of its own, one built on traces (`StoreLatencyFromTraces`) and one built on logs (`ErrorLogBurst`). You see them under Grafana > Alerting, not in Prometheus.

Everything runs on your computer. Only the alert text goes to ntfy.sh, on a random private topic, when you turn on the phone push ([6-0](#6-0-phone-push-with-ntfy-recommended-on-ibm-laptops-no-account)); Slack and email are optional. It works on Apple Silicon (M1 to M4) and Intel Macs, and on any Windows 10 or 11 PC, because the app is built on your own machine instead of downloaded for one type of processor.

**What you need:** about 8 GB of RAM (16 GB is more comfortable; with WSL you must give it at least 5 GB, see [WSL step 2](#windows-by-hand-wsl2-and-ubuntu); on an 8 GB Mac give Colima 4 GB, see [Mac step 5](#mac)), 20 GB of free disk space and an internet connection for the first run.

---

## 2. Install the tools (one time)

> **Fastest way: the setup kit.** Once the project is on your laptop (step 3 clones it), one command checks every tool and installs only the missing ones, then runs the preflight:
> - Windows PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-tools.ps1 -Engine rancher` (or `-Engine docker` if you have a Docker Desktop licence; add `-DryRun` first to only see what is missing). It works without winget too: kubectl, minikube, helm and gh go into `%USERPROFILE%\tools\bin`, no admin rights needed.
> - Mac: `./scripts/install-tools.sh` (add `--dry-run` first to only see what is missing).
>
> The sections below are the same steps by hand.

### Mac

You will type commands in the **Terminal** app. To open it, press **Cmd + Space**, type `Terminal` and press **Enter**. To run a command, copy it, paste it into Terminal with **Cmd + V** and press **Enter**.

1. **Install Homebrew** (an app installer for the Terminal). Paste this, press **Enter**, and type your Mac password when asked (nothing appears while you type; that is normal):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
   When it finishes, it may print two or three lines under **Next steps** that start with `echo` or `eval`. Copy and run those lines too.
2. **Apple silicon Macs (M1 to M4) only: add Homebrew to your PATH.** On these Macs Homebrew lives in `/opt/homebrew`, and Terminal does not find it until you run these two lines. The first line fixes this window. The second line fixes every new window. (Intel Macs skip this step. If you already ran the same `eval` and `echo` lines from **Next steps** in step 1, skip it too.)
   ```bash
   eval "$(/opt/homebrew/bin/brew shellenv)"
   echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
   ```
   Then check:
   ```bash
   brew --version
   ```
   `command not found: brew` means this step was skipped. Run it, then try again.
3. **Install the tools:**
   ```bash
   brew install colima docker minikube kubectl helm git gh python
   ```
   (`gh` is the GitHub command line, used in [step 3](#3-download-and-start-the-project) to fork the project and again in lab Part 3; `python` gives you `python3` for the tests and the lab scripts.)
4. **Check your Python version.** The lab needs Python **3.10 or newer**:
   ```bash
   python3 --version
   ```
   If it shows `3.9` (Apple's own Python, too old for the tests), Homebrew is not first in your PATH. Do step 2 again and open a new Terminal window. Still `3.9`? Install a fixed version and use `python3.12` wherever this guide says `python3`:
   ```bash
   brew install python@3.12
   python3.12 --version
   ```
5. **Start Colima** (it gives your Mac the engine that runs containers; use Colima instead of Docker Desktop, as in the course):
   ```bash
   colima start --cpu 4 --memory 6 --disk 60
   ```
   **Mac with 8 GB of memory:** 6 GB for Colima leaves too little for macOS. Use this line instead, and run **no add-ons** (stay with the core stack):
   ```bash
   colima start --cpu 2 --memory 4 --disk 60
   ```
   Start Colima yourself **before** you run `./scripts/deploy.sh`. The deploy script starts Colima only when it is not running, and then it always uses 6 GB. With 4 GB in Colima, Minikube gets about 3.6 GB. That is enough for the core stack, but not for add-ons.
6. **Check that everything works.** Each line should print a version, not an error:
   ```bash
   docker version
   minikube version
   kubectl version --client
   git --version
   gh --version
   python3 --version
   ```

Then log in to GitHub once (needed for the fork in step 3): `gh auth login`, choose **GitHub.com**, **HTTPS** and **Login with a web browser**. Go to [step 3](#3-download-and-start-the-project).

### Windows (PowerShell, used by IBM Bob)

Use this path if an AI coding agent (for example IBM Bob) is guiding you. Every command runs in **PowerShell** (the agent's terminal). There is no Ubuntu window and no WSL setup to do by hand.

1. **Install a container engine** (the program that runs containers). This needs administrator rights and maybe one restart; you click through the installer yourself.
   - **Docker Desktop:** `winget install -e --id Docker.DockerDesktop`, if your company has a licence for it (see [On an IBM-managed laptop](#on-an-ibm-managed-laptop)).
   - **Rancher Desktop** (free): `winget install -e --id SUSE.RancherDesktop`. On first start choose the **dockerd (moby)** engine and turn **Kubernetes off** (Minikube provides it).

   Start the app once from the **Start** menu and wait until it says it is running.
2. **Install the tools,** one line at a time:
   ```powershell
   winget install -e --id Kubernetes.minikube
   winget install -e --id Kubernetes.kubectl
   winget install -e --id Helm.Helm
   winget install -e --id Git.Git
   winget install -e --id GitHub.cli
   winget install -e --id Python.Python.3.12 --scope user
   ```
3. **Refresh PATH after each install.** A terminal that was already open does not see a new program. Paste this line (or open a new terminal):
   ```powershell
   $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
   ```
4. **Use `python`, never `python3`.** On Windows `python3` opens the Microsoft Store instead of Python. Wherever this guide shows `python3 scripts/<name>.py`, run `python scripts\<name>.py` (or `py scripts\<name>.py`).
5. **Run the `.ps1` scripts.** Wherever this guide shows `./scripts/deploy.sh`, `./scripts/dashboards.sh` or `./scripts/trigger-alert.sh`, run `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\deploy.ps1` (or `scripts\dashboards.ps1`, `scripts\trigger-alert.ps1`). `-ExecutionPolicy Bypass` works for that one script only and changes no setting. The `kubectl` commands are the same.
6. **Check that everything works.** Each line should print a version, not an error:
   ```powershell
   docker version
   minikube version
   kubectl version --client
   git --version
   gh --version
   python --version
   ```
   Then log in to GitHub once: `gh auth login`, choose **GitHub.com**, **HTTPS** and **Login with a web browser**. This is a human step: you finish it in your browser.

> Docker Desktop with the WSL2 backend takes its memory from `.wslconfig` (see [WSL step 2](#windows-by-hand-wsl2-and-ubuntu)); only the Hyper-V backend has a **Settings > Resources > Memory** slider (set it to at least 5 GB). Rancher Desktop has a memory slider under **Preferences > Virtual Machine**.

### Windows by hand (WSL2 and Ubuntu)

Use this path only if you follow the guide **without** IBM Bob. The tools run inside **Ubuntu Linux**, which Windows can run in a window through **WSL2**. After this setup you type every command in the **Ubuntu** window, not in PowerShell.

1. **Install WSL2 and Ubuntu.** Click **Start**, type `PowerShell`, right-click **Windows PowerShell** and choose **Run as administrator**. Paste this and press **Enter**:
   ```powershell
   wsl --install
   ```
   Restart your computer when it finishes.
2. **Give WSL enough memory.** Windows lets Ubuntu use only half of your RAM by default, and Minikube needs 4 GB. In PowerShell (normal) run `notepad $env:USERPROFILE\.wslconfig`, choose **Yes** to create the file, paste:
   ```
   [wsl2]
   memory=6GB
   ```
   (on an 8 GB laptop use `memory=5GB`), save, then run `wsl --shutdown`.
3. **Create your Ubuntu user.** After the restart, open **Ubuntu** from the **Start** menu. The first time, it asks for a new username and password (this is only for Ubuntu; nothing appears while you type the password). Remember them.
4. **Turn on systemd** (lets Docker start by itself). In the Ubuntu window, paste:
   ```bash
   printf '[boot]\nsystemd=true\n' | sudo tee /etc/wsl.conf
   ```
   Then open **PowerShell** (normal, not administrator) and run:
   ```powershell
   wsl --shutdown
   ```
   Open **Ubuntu** again from the **Start** menu.
5. **Install Docker Engine.** In Ubuntu, paste this whole block at once and press **Enter**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y ca-certificates curl gnupg git
   sudo install -m 0755 -d /etc/apt/keyrings
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   sudo apt-get update
   sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
   sudo usermod -aG docker $USER
   sudo systemctl enable --now docker
   ```
   **Close the Ubuntu window and open it again** so your user can use Docker.
6. **Install kubectl, Minikube and Helm:**
   ```bash
   curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.35/deb/Release.key | sudo gpg --dearmor --yes -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
   echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.35/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
   sudo apt-get update && sudo apt-get install -y kubectl
   curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
   sudo install minikube-linux-amd64 /usr/local/bin/minikube && rm minikube-linux-amd64
   curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
   ```
7. **Install the GitHub command line** (used in step 3 to fork the project and in lab Part 3; Ubuntu's own `gh` package is too old, so use GitHub's repository) and the Python tools for the add-on scripts:
   ```bash
   curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/etc/apt/keyrings/githubcli-archive-keyring.gpg
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
   sudo apt-get update && sudo apt-get install -y gh python3 python3-venv python3-pip
   ```
8. **Check that everything works.** Each line should print a version, not an error:
   ```bash
   docker version
   minikube version
   kubectl version --client
   git --version
   gh --version
   python3 --version
   ```
   Then log in to GitHub once: `gh auth login`, choose **GitHub.com**, **HTTPS** and **Login with a web browser**.

### On an IBM-managed laptop

Company laptops have a few extra locks. Fix them **before** the lab day:
- **Administrator rights.** The installers need them. Request temporary administrator rights through IBM's usual IT help process.
- **Which container engine.** Docker Desktop needs a paid licence in large companies ([Docker's licence terms](https://docs.docker.com/subscription/desktop-license/)). Ask your manager or IT which engine is approved. If Docker Desktop is not licensed for you, use [Rancher Desktop](https://rancherdesktop.io/) with the **dockerd (moby)** engine.
- **VPN.** Downloads can fail or hang on the VPN. Disconnect it during installs and the first deploy (if your IBM policy allows), then reconnect.
- **Script policy.** If PowerShell says "running scripts is disabled on this system", use the `powershell -NoProfile -ExecutionPolicy Bypass -File ...` form shown in this guide. If that is also blocked, IT has locked the policy: send them [IT-REQUEST.md](IT-REQUEST.md).
- **Data.** Never put client data, w3 credentials or screenshots of internal IBM tools into the lab, into any AI agent or into your fork.

### AI assistants (only for lab Part 7)
Part 7 uses an **AI coding agent**. This repository has ready-made setups for **IBM Bob** (recommended for IBMers, in `.bob/`) and **Claude Code** (in `CLAUDE.md` and `.claude/`); other agents can follow `AGENTS.md`, but they were not tested. If you want Claude Code, install it by following the official setup page, <https://code.claude.com/docs>, then check it with `claude --version`. It needs a paid Claude plan or an Anthropic Console account; free courses are on Anthropic Academy. IBM Bob is at <https://bob.ibm.com> (IBMers through IBM, others through the trial). Without either, pair with a classmate: every Part 7 exercise can be done with one of the two tools.

---

## 3. Download and start the project

From here on the steps are the same on Mac and Windows. Use **Terminal** on Mac, **PowerShell** on Windows with IBM Bob, and the **Ubuntu** window on Windows by hand.

1. Mac only: make sure Colima is running (it is fine if it says it already is):
   ```bash
   colima start
   ```
2. Make your own copy of the project and download it. A **fork** is your own copy on GitHub; `--clone` also downloads it to your laptop. Your work and your lab proof live in your fork (mission M09b checks this). Log in first with `gh auth login` (see step 2).
   ```bash
   cd ~
   gh repo fork jaffethalfarotorres/sre-final-project --clone
   cd sre-final-project
   ```
   Only want to look around, without a GitHub account? `git clone https://github.com/jaffethalfarotorres/sre-final-project.git` works too, but the fork mission will not pass.
3. Start everything with one command:
   ```bash
   ./scripts/deploy.sh
   ```
   Windows PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\deploy.ps1`

   The first run takes 5 to 10 minutes because it downloads everything. You will see a lot of text. It is done when it prints **Deployment complete**.

   What the script does for you: it starts the mini data center (Minikube), builds the shop app, creates a private Grafana login, starts all the pieces and waits until they are healthy.
4. Check that everything is running:
   ```bash
   kubectl get pods -A
   ```
   Every line should say `Running` and `1/1` (or `2/2`, `3/3`). If some say `ContainerCreating`, wait a minute and run it again. Do not continue until they are all `Running`.

---

## 4. Look at the dashboards

The pieces run inside Minikube, so your browser reaches them through "tunnels" (port-forwards). One command opens all of them in the background and gives you your terminal back:

```bash
./scripts/dashboards.sh --background
```
Windows PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dashboards.ps1 -Background`

It prints the addresses, opens Grafana in your browser and prints the Grafana login. Grafana opens view-only without a login; to change things, sign in with **`admin` / `admin`** (a lab-only login: Grafana is reachable only from your own laptop). The tunnels keep running until you stop them:

```bash
./scripts/dashboards.sh --stop
```
Windows PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dashboards.ps1 -Stop`

| Address | What you see |
| --- | --- |
| <http://localhost:3000> | **Grafana**, the charts. Opens without a login (view-only). To edit, sign in with `admin` / `admin`. |
| <http://localhost:9090> | **Prometheus**, the raw measurements and the alarm rules |
| <http://localhost:9093> | **Alertmanager**, who gets notified |
| <http://localhost:16686> | **Jaeger**, the path of each single request (traces) |
| <http://localhost:5000> | The app itself |

Because the tunnels run in the background, you can keep using the same window. Lost your place? Go back to the project folder with `cd ~/sre-final-project`.

### Grafana (the charts)
Click **Dashboards** in the left menu, then the **SRE Demo** folder. There are four dashboards:
- **SRE Metrics Demo**: requests per second, response time, errors, total requests. Start here.
- **Golden Signals**: latency, traffic, errors and saturation, plus the app's logs. Click a log line, then **TraceID**, to see that request in Jaeger.
- **SLO and Error Budget**: how reliable the shop has been and how much failure is still "allowed" (see [SLO.md](SLO.md)).
- **LLM Observability**: tokens, cost and latency of a simulated AI model call.

### Prometheus (the raw measurements and alarm rules)
Click **Status > Targets**: every target shows a green **UP**. Click **Alerts** to see the alarm rules and which ones are active.

### Alertmanager (who gets notified)
After about a minute you see `AlwaysFiringDemoAlert`. It is always on, to prove the alarm pipeline works.

> If you started the project with the Helm option (`./scripts/deploy.sh --helm`), the dashboards script detects it and uses the right names automatically.

---

## 5. Make an alert fire

The shop fails about 0.5% of the time on its own, well inside its 99% target (see [SLO.md](SLO.md)), so the alarms stay quiet. To see a real alarm, send it a burst of bad requests.

1. With the tunnels running (step 4), run:
   ```bash
   ./scripts/trigger-alert.sh
   ```
   Windows PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\trigger-alert.ps1`

   It starts a small robot inside the cluster that calls the failing page about 1,000 times (roughly 4 minutes), then waits and tells you when the alarm fires: `HighErrorRate is FIRING after about 150 seconds.` The window looks busy for a few minutes. That is normal; wait for it to finish.
2. Look at the Grafana **Error rate** chart: it climbs. In Prometheus (**Alerts**) and Alertmanager, `HighErrorRate` turns red (firing). The **SLO and Error Budget** dashboard shows the error budget being spent, and `ErrorBudgetFastBurn` fires too.

The robot stops by itself. A few minutes later the error rate drops and the alerts clear on their own.

---

## 6. Optional: get alerts in Slack and email

Without this step the alarms still work; you just see them in Alertmanager instead of getting a message.

> **IBMers:** never connect the lab to IBM Slack or IBM mail. On an IBM-managed laptop, personal Slack and personal mail are usually blocked too, so use **6-0 (phone push)**: it needs no account and works on IBM laptops. Slack and email (6a to 6e) are for personal computers.

### 6-0. Phone push with ntfy (recommended on IBM laptops, no account)

[ntfy](https://ntfy.sh) is a free push notification service: no sign-up, no password. The lab sends each critical and warning alert to a private "topic" (a random name only you know), and you read it in the ntfy app on your phone or in a browser.

1. Connect the lab (one command):
   ```bash
   python3 scripts/notify_setup.py
   ```
   Windows PowerShell: `python scripts\notify_setup.py`

   What you should see: `Phone push is ON`, your private topic name (`sre-lab-...`), and a test push called `LabConnected`.
2. On your phone, install the free **ntfy** app (App Store or Google Play). Tap **+**, type your topic name, keep the server `ntfy.sh`, and tap **Subscribe**. No phone? Open `https://ntfy.sh/<your topic>` in a browser and keep the tab open.
3. Make an alert fire ([step 5](#5-make-an-alert-fire)). About 3 minutes later a push arrives: `[firing] critical: HighErrorRate`, followed by `[resolved] ...` when it clears.
4. Take a screenshot of the push (Windows: **Windows + Shift + S**; phone: the usual screenshot buttons) and save it as `docs/screenshots/notification-delivered.png`. That is the evidence for the final project's advanced alerting bonus.

Good to know:
- Send another test at any time: `python3 scripts/notify_setup.py --test`. Turn it off: `python3 scripts/notify_setup.py --off`.
- Anyone who knows your topic name can read the pushes. Keep it to yourself, and send only lab alerts there, never IBM, client or personal data.
- The script changes only the `ntfy-url` line of your private file `k8s/alertmanager-secret.yaml` (Git never uploads it) and restarts Alertmanager.
- Nothing arrives? Check that `https://ntfy.sh` opens in your browser (a VPN or proxy may block it), then run `kubectl logs -n monitoring deploy/alertmanager --since=10m` and look for `ntfy` or `webhook` errors.

On a personal computer you can also use Slack and email, below. Real passwords go in one private file, `k8s/alertmanager-secret.yaml`, which Git never uploads. Use a **personal** Slack workspace (create a free one at <https://slack.com/get-started>) and a **personal** Gmail.

### 6a. Get a Slack webhook (a private address that posts into a channel)

1. Go to <https://api.slack.com/apps> and sign in to your personal Slack workspace.
2. Click **Create New App > From scratch**. Name it `SRE Alerts`, pick your workspace, click **Create App**.
3. In the left menu click **Incoming Webhooks** and switch it **On**.
4. Click **Add New Webhook to Workspace**, choose the channel that should receive alerts, click **Allow**.
5. Copy the **Webhook URL** (it starts with `https://hooks.slack.com/services/`). Treat it like a password.

### 6b. Get a Gmail app password (lets the project send email from your account)

1. Your Google account must have **2-Step Verification** turned on (<https://myaccount.google.com/security>).
2. Go to <https://myaccount.google.com/apppasswords>.
3. Type a name such as `SRE Alerts` and click **Create**.
4. Copy the 16-letter password and remove the spaces. Your normal Gmail password will **not** work here.

Using Outlook.com instead? Use the server `smtp-mail.outlook.com:587` and an app password from your Microsoft account security page.

### 6c. Put the secrets in the private file

1. Open the file in a simple text editor that works in the Terminal and Ubuntu window:
   ```bash
   nano k8s/alertmanager-secret.yaml
   ```
   Windows PowerShell (IBM Bob): open it yourself with `notepad k8s\alertmanager-secret.yaml`, then save with **Ctrl + S** and close Notepad. Do not ask Bob to open or read this file: it holds your passwords.
2. Use the arrow keys to move. Replace the text between the quotes on these two lines (paste with **Cmd + V** on Mac, or **right-click** in the Ubuntu window):
   ```yaml
   slack-webhook-url: "your Slack webhook URL"
   smtp-auth-password: "your 16-letter app password"
   ```
3. Save and exit: press **Ctrl + O**, then **Enter**, then **Ctrl + X**.

### 6d. Put your email addresses in the settings

Open the settings file the same way:
```bash
nano k8s/alertmanager.yaml
```
Windows PowerShell: `notepad k8s\alertmanager.yaml` (save with **Ctrl + S**).
Change these lines (keep the quotes), then save (nano: **Ctrl + O**, **Enter**, **Ctrl + X**):

| Line | Change to |
| --- | --- |
| `smtp_smarthost: 'smtp.gmail.com:587'` | Leave as is for Gmail, or your provider's server. |
| `smtp_from: 'sre-alerts@example.com'` | Your Gmail address. |
| `smtp_auth_username: 'sre-alerts@example.com'` | Your Gmail address. |
| `- to: 'sre-oncall@example.com'` (appears twice) | The address that should receive alerts. |

If you use the Helm option, make the same changes in `helm/values-monitoring.yaml`.

Note: `k8s/alertmanager.yaml` is a normal project file. If you upload your copy to GitHub, these email addresses become public. The passwords stay private.

### 6e. Apply the changes and test

1. Run the deploy script again:
   ```bash
   ./scripts/deploy.sh
   ```
   Windows PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\deploy.ps1`
2. Restart Alertmanager so it reads the new settings (Kubernetes does not reload changed settings by itself):
   ```bash
   kubectl rollout restart deployment/alertmanager -n monitoring
   ```
   (Helm option: `kubectl delete pod alertmanager-kube-prometheus-stack-alertmanager-0 -n monitoring`. It comes back by itself.)
3. Do [step 5](#5-make-an-alert-fire) again. In about 3 minutes a `HighErrorRate` message arrives in Slack and in the email inbox.
4. Take screenshots (Mac: **Cmd + Shift + 4**; Windows: **Windows + Shift + S**) and save them as `slack-notification.png` and `email-notification.png` in the `docs/screenshots` folder.

Nothing arrives? See [Troubleshooting](#troubleshooting).

---

## 7. Optional: publish the app image to Docker Hub

This is only for someone who has their own copy of the project on GitHub. It makes GitHub build the app and upload it to Docker Hub automatically (that is the "CD" part). Everything here is done in the web browser.

1. **Create a Docker Hub token.** Sign in at <https://hub.docker.com>, open your profile menu > **Account settings > Personal access tokens > Generate new token**. Name it `github-cd`, choose **Read & Write**, click **Generate**, and copy the token. It is shown only once.
2. **Store it in GitHub.** On your repository page go to **Settings > Secrets and variables > Actions > New repository secret** and create two secrets:
   - Name `DOCKERHUB_USERNAME`, value: your Docker Hub username.
   - Name `DOCKERHUB_TOKEN`, value: the token from step 1.
3. **Start a release.** On the repository page click **Releases > Draft a new release**. In **Choose a tag** type `v1.0.0` and click **Create new tag**. Give it the title `v1.0.0` and click **Publish release**.
4. **Watch it.** Open the **Actions** tab. The **CD** workflow starts and should end with a green check in a few minutes. Your image then appears on Docker Hub under your username, named `sre-metrics-app`.

You can also start it by hand: **Actions > CD > Run workflow**.

---

## 7b. Going further: the lab guide and the add-ons

Everything above is the core of the project. The [lab guide](labs/README.md) continues from here, one topic at a time: logs and traces, SLOs, automation with Ansible and AWX, GitOps with ArgoCD, chaos engineering, policies, canary releases, and AI assistants (Claude Code and IBM Bob) that help investigate incidents without being allowed to change anything ([AI-SRE.md](AI-SRE.md)).

The add-ons are started with a Python script (Python 3 comes with Ubuntu; on Mac run `brew install python@3.12` if `python3 --version` fails or shows 3.9, and use `python3.12` instead of `python3`, see [Mac step 4](#mac); in Windows PowerShell always use `python`, never `python3`). Run **one at a time** and remove it before the next, so Minikube does not run out of memory.

Add-ons need a 6 GB Minikube on a 16 GB laptop (see [labs/01, step 4](labs/01-foundations.md)). On an 8 GB laptop, stay with the core stack (Mac: Colima with `--memory 4`, see [Mac step 5](#mac)). For example:
```bash
python3 scripts/chaos_test.py
```
Windows PowerShell: `python scripts\chaos_test.py`

### The Road to Junior SRE (the lab game, also without an agent)

The lab is one journey: you start as a **Career Changer** and climb 8 camps to **On-Call Ready**, the day a team trusts you with the pager. Each camp gives Nimbus Store (the pretend shop) a real new capability, teaches one SRE principle and lists skills you can name on your CV. The default start is the **First on-call shift**, 9 missions in one sitting: `python3 scripts/lab.py journey` lists them with done marks and minutes left. Everything after it is optional. You can play it by hand with the same script the agents use. By hand, the shift ends at step 7: steps 8-9 (M17, M18) need an AI coding agent, because their check looks for the agent's triage report in `reports/`. The commands below are for **Mac** and for the **Ubuntu window (WSL)**: `python3 scripts/lab.py ...`. Only in **Windows PowerShell** type `python scripts\lab.py ...` instead (the backslash and `python` work only there):

```bash
python3 scripts/lab.py journey         # the 9 steps of the First on-call shift
python3 scripts/lab.py status          # your rank, XP and next mission
python3 scripts/lab.py show M05        # what to do and the quiz questions
python3 scripts/lab.py check M05       # check the mission on your laptop (read-only)
python3 scripts/lab.py answer M05 1 b  # answer quiz question 1 (2 attempts: full XP, then half, then locked)
python3 scripts/lab.py cv              # your skills, principles and interview questions so far
python3 scripts/lab.py play            # Mission Control, the visual dashboard
python3 scripts/lab.py proof --name "Your Name"   # your SRE Lab Passport
```

Ranks by XP: Career Changer (0), Tech Apprentice (500), SRE Intern (1300), Junior SRE Candidate (2300), Junior SRE Lab Graduate (3300). Quizzes are for learning only: they never block a mission and are never graded. The passport is a self-generated record, not a certificate; its fingerprint shows later edits but is not a signature. A mentor can confirm it with `lab.py verify` or a short live demo.

---

## Your final project: what you must hand in

> Only for students of the SRE Academy course. If you came for the First on-call shift, you can skip this section.

The SRE Academy final project has **six required items** and **three bonuses**. This table shows where you do each one in this lab. Everything you hand in lives in **your own fork** (see [step 3](#3-download-and-start-the-project)). A copy of this repository with no changes of your own earns no credit.

| # | Requirement | What you do in this lab |
| --- | --- | --- |
| 1 | An app that emits metrics or alerts | Deploy the core stack ([step 3](#3-download-and-start-the-project)). The app in `app/app.py` emits metrics, traces and logs. |
| 2 | Deployment on Kubernetes | Same: `deploy.sh` (or `deploy.ps1`) runs everything on Minikube. |
| 3 | Prometheus collects the metrics | Same: check **Status > Targets** in Prometheus ([step 4](#4-look-at-the-dashboards)). |
| 4 | Grafana dashboards | Same: the four dashboards in the **SRE Demo** folder ([step 4](#4-look-at-the-dashboards)). |
| 5 | Alertmanager | Make an alert fire ([step 5](#5-make-an-alert-fire)) and see it in Alertmanager. |
| 6 | Professional documentation | In your fork: a `README.md` that explains **your** work, comments in your code, `LICENSE.md`, `CONTRIBUTING.md`, and **your own screenshots** in `docs/screenshots/`, taken on your laptop. |
| Bonus a | Notifications to Slack or email | [Step 6](#6-optional-get-alerts-in-slack-and-email). Keep one screenshot of the message that arrived (hide the webhook and passwords). |
| Bonus b | Infrastructure as Code | The `terraform/`, `ansible/` and `helm/` folders (`./scripts/deploy.sh --helm` is the Helm path). Show that you ran one of them. |
| Bonus c | CI/CD pipeline | The GitHub Actions workflows in **your fork** (**Actions** tab). Keep a screenshot of a green run. [Step 7](#7-optional-publish-the-app-image-to-docker-hub) adds the CD part. |

Your own change counts too. The [lab guide](labs/README.md) says what your professor expects: for example a new endpoint with a test, an SLO alert, a Grafana panel and a runbook, with CI green in your fork.

**The licence.** Keep the MIT copyright line in `LICENSE.md` as it is (it names the original author). Add a new line under it with your own name and year, for example `Copyright (c) 2027 Your Name`. Do not delete the original line.

---

## 8. Stop, restart and clean up

- **Pause** (keeps everything for next time):
  ```bash
  minikube stop
  ```
  Mac: you can also run `colima stop` to free memory.
- **Start again later:**
  ```bash
  colima start        # Mac only
  minikube start
  cd ~/sre-final-project
  kubectl get pods -A
  ```
  Then open the tunnels again (step 4). Before `minikube stop`, close them with `./scripts/dashboards.sh --stop` (Windows PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dashboards.ps1 -Stop`).
- **Remove the project** from Minikube:
  ```bash
  kubectl delete namespace application monitoring opentelemetry
  ```
  If you installed add-ons, remove them with the **Clean up** section of each lab in [docs/labs](labs/README.md).
- **Remove Minikube completely** (frees the most space):
  ```bash
  minikube delete
  ```

---

## Troubleshooting

If a command fails, **you are probably not doing anything wrong**. Find the message below.

| What you see | What to do |
| --- | --- |
| Mac: `Cannot connect to the Docker daemon` | Run `colima start`, wait for it to finish, try again. |
| Mac: `command not found: brew`, or `python3 --version` shows 3.9 | Homebrew is not in your PATH. Do [Mac step 2](#mac) (the `brew shellenv` lines), open a new Terminal window and check again. Still 3.9? Do Mac step 4 (`brew install python@3.12`). |
| Windows (PowerShell): `Cannot connect to the Docker daemon` or `error during connect` | Start Docker Desktop or Rancher Desktop from the **Start** menu and wait until it says it is running. |
| Windows (WSL): `Cannot connect to the Docker daemon` or `permission denied ... docker.sock` | Close and reopen the Ubuntu window. If it persists, run `sudo systemctl start docker`. Check step 4 of the Windows install (systemd) was done. |
| `command not found` for `minikube`, `kubectl` or `helm` | The install step for that tool did not finish. Run it again and reopen the window. |
| `permission denied: ./scripts/deploy.sh` | Run `chmod +x scripts/deploy.sh` once, then try again. |
| `No such file or directory` for `scripts/deploy.sh` or `k8s/...` | You are not in the project folder. Run `cd ~/sre-final-project`. |
| `Docker has only ...MB of memory` (from deploy.sh) or `Docker has only ...MB memory but you specified 4096MB` (from Minikube) | Docker has too little memory. Windows with IBM Bob: raise the memory in Docker Desktop (**Settings > Resources**) or Rancher Desktop (**Preferences > Virtual Machine**) to at least 5 GB. Windows by hand: do step 2 of the WSL install (`.wslconfig`), run `wsl --shutdown` and reopen Ubuntu. Mac: `colima stop` then `colima start --cpu 4 --memory 6`. Then run `minikube delete` and `./scripts/deploy.sh` again. |
| Pods stuck in `Pending` or `ContainerCreating` for more than 5 minutes | The computer is short on memory. Mac: `colima stop` then `colima start --cpu 4 --memory 6` (8 GB Mac: `--cpu 2 --memory 4`, and close other apps). Windows: close other programs. Then run `minikube delete` and `./scripts/deploy.sh` again. |
| A pod shows `CrashLoopBackOff` | Run `kubectl get pods -A` again in a minute; Kubernetes retries on its own. If it stays, run `./scripts/deploy.sh` again. |
| Browser says "This site can't be reached" on localhost | The tunnels are not running. Run `./scripts/dashboards.sh --background` again (Windows: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dashboards.ps1 -Background`). |
| `curl` or the browser gets nothing right after starting the tunnels | The tunnels need a few seconds to get ready. Wait 5 seconds and try again. |
| `address already in use` when opening a tunnel | Old tunnels are still running. Run `./scripts/dashboards.sh --stop` (Windows PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dashboards.ps1 -Stop`), then start them again. |
| A copied command fails with `No such file or directory` and has `<` `>` in it | Text inside `< >` is a placeholder to replace. The commands in this guide do not need any changes. |
| Grafana rejects `admin` / `admin` | This lab was deployed before the simple login, or you set your own password in `k8s/grafana-secret.yaml`. The dashboards script copies your own password to the clipboard. To go back to `admin` / `admin`, delete `k8s/grafana-secret.yaml` and run `scripts/lab_up.py --redeploy`. |
| No Slack or email message | Check the logs: `kubectl logs deployment/alertmanager -n monitoring --tail=30`. `no_team` or `invalid_token` means a wrong Slack URL. `535` means a wrong email address or app password. Fix the file, then repeat step 6e. |
| Windows: `python` opens the Microsoft Store, or `python3` does nothing | Install Python with `winget install -e --id Python.Python.3.12 --scope user`, refresh PATH (see [Windows step 3](#windows-powershell-used-by-ibm-bob)), and use `python`, never `python3`. |
| Windows: a tool is "not recognized" right after `winget install` | The open terminal has an old PATH. Run the PATH refresh line from [Windows step 3](#windows-powershell-used-by-ibm-bob), or open a new terminal. |
| Windows: "running scripts is disabled on this system" | Use the full form `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\<name>.ps1`. If that is also blocked, the policy is locked by IT: see [IT-REQUEST.md](IT-REQUEST.md). |
| `winget` or a download fails, hangs or shows a certificate error | Usually the VPN or a company proxy. Disconnect the VPN during installs (if your policy allows) and try again. |
| An installer asks for administrator rights you do not have | Request temporary admin rights through IBM's IT help process, then run the install again. See [On an IBM-managed laptop](#on-an-ibm-managed-laptop). |
| Docker Desktop asks for a subscription | Your company may not have a licence for you. Use Rancher Desktop with the dockerd (moby) engine instead. |
| You changed a setting and nothing happened | Settings are read at start-up. Run `kubectl rollout restart deployment/alertmanager -n monitoring` (or `prometheus`, `grafana`). |

---

## Glossary

| Term | Meaning |
| --- | --- |
| **Alert / alarm** | A rule that turns "on" when a measurement crosses a limit for some time. |
| **Repository (repo)** | A project folder whose full history is kept online, on GitHub. |
| **Fork** | Your own copy of someone else's repository, under your GitHub account. |
| **Clone** | Download a repository to your laptop. |
| **Terminal** | A window where you type commands. On Windows with IBM Bob it is **PowerShell**. |
| **winget** | The Windows app installer you use from PowerShell. |
| **PATH** | The list of folders where the terminal looks for programs. A new install is found only after PATH is refreshed. |
| **IBM Bob** | IBM's AI assistant. In this lab it is your AI pair: it proposes every command, and you approve each one. |
| **Mode** | Bob's "job hat": *SRE Lab Guide* runs lab commands you approve; *SRE Triage* only reads. |
| **Dashboard** | A screen of live charts. |
| **Runbook** | Step-by-step instructions for fixing one known problem. |
| **Colima** | A small program that lets a Mac run containers (the Mac equivalent of what Linux has built in). |
| **Container** | A sealed box that holds one program and everything it needs, so it runs the same anywhere. |
| **Docker** | The tool that builds and runs containers. |
| **WSL2** | Windows Subsystem for Linux: runs a real Ubuntu Linux inside Windows. |
| **Kubernetes** | Software that runs many containers, restarts them if they crash and connects them. |
| **Minikube** | A one-computer version of Kubernetes for learning and testing. |
| **Pod** | Kubernetes' name for a running container (or a small group of them). |
| **Namespace** | A folder inside Kubernetes. This project uses `application` and `monitoring`. |
| **Port-forward** | A temporary tunnel from your browser to a program inside Minikube. |
| **Metric** | A number measured over time, such as "requests per second". |
| **Helm** | An installer for Kubernetes apps. It is an alternative way to deploy this project. |
| **Webhook** | A private web address that posts a message into a chat channel when called. |
| **CI/CD** | Automatic checks on every change (CI) and automatic publishing of new versions (CD). Here it is done by GitHub Actions. |
| **SRE** | Site Reliability Engineering: keeping online services reliable using measurements and automation. |
