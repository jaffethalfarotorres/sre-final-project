# Step-by-step guide for Mac and Windows (no experience needed)

This guide explains the project in plain language and walks you through running it on a **Mac** or a **Windows** computer, one step at a time. You do not need to know Kubernetes or programming. If a word is new, check the [glossary](#glossary) at the end.

The setup follows the same toolchain as the SRE Academy course: **Colima** on Mac, and **WSL2 with Ubuntu** on Windows. If you already set up your computer for the course exercises, skip to [step 3](#3-download-and-start-the-project).

- [1. What is this project?](#1-what-is-this-project)
- [2. Install the tools (one time)](#2-install-the-tools-one-time)
  - [Mac](#mac)
  - [Windows](#windows)
- [3. Download and start the project](#3-download-and-start-the-project)
- [4. Look at the dashboards](#4-look-at-the-dashboards)
- [5. Make an alert fire](#5-make-an-alert-fire)
- [6. Optional: get alerts in Slack and email](#6-optional-get-alerts-in-slack-and-email)
- [7. Optional: publish the app image to Docker Hub](#7-optional-publish-the-app-image-to-docker-hub)
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
| `ServiceDown` | The shop stops answering for 1 minute. |
| `HighErrorRate` | More than 5% of requests fail for 2 minutes. |
| `HighLatency` | Pages take longer than half a second for 2 minutes. |
| `SyntheticProbeFailing` | A robot check (blackbox exporter) cannot open the shop's home page: fewer than 90% of checks succeed over 2 minutes, for 2 minutes. |
| `ErrorBudgetFastBurn` | The shop is using up its monthly failure allowance more than 6 times faster than planned (see `docs/SLO.md`). This is urgent. |
| `ErrorBudgetSlowBurn` | The failure allowance has been spent faster than planned for hours (6-hour and 1-hour windows), for 15 minutes. This is a warning. |
| `ErrorBudgetExhausted` | The whole 30-day failure allowance is used up. On a fresh cluster this stays quiet until there are about 100,000 requests of history. |
| `AlwaysFiringDemoAlert` | Always on. It only proves the alarm system works. |

Grafana adds two more rules of its own, one built on traces (`StoreLatencyFromTraces`) and one built on logs (`ErrorLogBurst`). You see them under Grafana > Alerting, not in Prometheus.

Everything runs on your computer. Nothing is sent to the internet unless you set up Slack or email in step 6. It works on Apple Silicon (M1 to M4) and Intel Macs, and on any Windows 10 or 11 PC, because the app is built on your own machine instead of downloaded for one type of processor.

**What you need:** about 8 GB of RAM (16 GB is more comfortable; on Windows you must give WSL at least 5 GB, see [Windows step 2](#windows)), 20 GB of free disk space and an internet connection for the first run.

---

## 2. Install the tools (one time)

### Mac

You will type commands in the **Terminal** app. To open it, press **Cmd + Space**, type `Terminal` and press **Enter**. To run a command, copy it, paste it into Terminal with **Cmd + V** and press **Enter**.

1. **Install Homebrew** (an app installer for the Terminal). Paste this, press **Enter**, and type your Mac password when asked (nothing appears while you type; that is normal):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
   When it finishes, it may print two or three lines under **Next steps** that start with `echo` or `eval`. Copy and run those lines too. Then check:
   ```bash
   brew --version
   ```
2. **Install the tools:**
   ```bash
   brew install colima docker minikube kubectl helm git gh python
   ```
   (`gh` is the GitHub command line, used from lab Part 3; `python` gives you `python3` for the add-on scripts.)
3. **Start Colima** (it gives your Mac the engine that runs containers; use Colima instead of Docker Desktop, as in the course):
   ```bash
   colima start --cpu 4 --memory 6 --disk 60
   ```
4. **Check that everything works.** Each line should print a version, not an error:
   ```bash
   docker version
   minikube version
   kubectl version --client
   git --version
   gh --version
   ```

Then log in to GitHub once (needed from lab Part 3): `gh auth login`, choose **GitHub.com**, **HTTPS** and **Login with a web browser**. Go to [step 3](#3-download-and-start-the-project).

### Windows

The tools run inside **Ubuntu Linux**, which Windows can run in a window through **WSL2**. After this setup you type every command in the **Ubuntu** window, not in PowerShell.

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
7. **Install the GitHub command line** (used from lab Part 3; Ubuntu's own `gh` package is too old, so use GitHub's repository) and the Python tools for the add-on scripts:
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

> Already using **Docker Desktop** on Windows instead of WSL2? That works too: install the tools with `winget install -e --id Kubernetes.minikube` and `winget install -e --id Kubernetes.kubectl`, and use PowerShell from the project folder for every later step. Wherever this guide shows `./scripts/deploy.sh`, `./scripts/dashboards.sh` or `./scripts/trigger-alert.sh`, run `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\deploy.ps1` (or `scripts\dashboards.ps1`, `scripts\trigger-alert.ps1`) instead. Wherever it shows `python3 scripts/<name>.py`, run `python scripts\<name>.py` (or `py scripts\<name>.py`). If `python` opens the Microsoft Store, install Python with `winget install -e --id Python.Python.3.12`. The `kubectl` commands are the same.
>
> Docker Desktop with the WSL2 backend also takes its memory from `.wslconfig`, so create it as in step 2 above; only the Hyper-V backend has a **Settings > Resources > Memory** slider (set it to at least 5 GB).

### AI assistants (only for lab Part 7)
Part 7 uses **Claude Code** and/or **IBM Bob**. Install Claude Code by following the official setup page, <https://code.claude.com/docs>, then check it with `claude --version`. It needs a paid Claude plan or an Anthropic Console account; free courses are on Anthropic Academy. IBM Bob is at <https://bob.ibm.com> (IBMers through IBM, others through the trial). Without either, pair with a classmate: every Part 7 exercise can be done with one of the two tools.

---

## 3. Download and start the project

From here on the steps are the same on Mac and Windows. Use **Terminal** on Mac and the **Ubuntu** window on Windows.

1. Mac only: make sure Colima is running (it is fine if it says it already is):
   ```bash
   colima start
   ```
2. Download the project and go into its folder:
   ```bash
   cd ~
   git clone https://github.com/jaffethalfarotorres/sre-final-project.git
   cd sre-final-project
   ```
3. Start everything with one command:
   ```bash
   ./scripts/deploy.sh
   ```
   Docker Desktop/PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\deploy.ps1`

   The first run takes 5 to 10 minutes because it downloads everything. You will see a lot of text. It is done when it prints **Deployment complete**.

   What the script does for you: it starts the mini data center (Minikube), builds the shop app, creates a private Grafana login, starts all the pieces and waits until they are healthy.
4. Check that everything is running:
   ```bash
   kubectl get pods -A
   ```
   Every line should say `Running` and `1/1` (or `2/2`, `3/3`). If some say `ContainerCreating`, wait a minute and run it again. Do not continue until they are all `Running`.

---

## 4. Look at the dashboards

The pieces run inside Minikube, so your browser reaches them through "tunnels" (port-forwards). One command opens all of them and shows the Grafana login:

```bash
./scripts/dashboards.sh
```
Docker Desktop/PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dashboards.ps1`

It prints the addresses and the Grafana password, and opens Grafana in your browser. **Keep this window open** while you use the dashboards; press **Ctrl + C** in it to close the tunnels (on Mac too, it is Ctrl, not Cmd).

| Address | What you see |
| --- | --- |
| <http://localhost:3000> | **Grafana**, the charts. Log in as `admin` with the password the script shows. |
| <http://localhost:9090> | **Prometheus**, the raw measurements and the alarm rules |
| <http://localhost:9093> | **Alertmanager**, who gets notified |
| <http://localhost:16686> | **Jaeger**, the path of each single request (traces) |
| <http://localhost:5000> | The app itself |

To run other commands, open another window: on Mac press **Cmd + T** in Terminal; on Windows open **Ubuntu** again from the **Start** menu. Then go to the project folder with `cd ~/sre-final-project`.

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

The shop fails about 5% of the time on its own, which is just under the alarm limit on purpose. To see a real alarm, send it a burst of bad requests.

1. In a second window (keep the dashboards window open), run:
   ```bash
   ./scripts/trigger-alert.sh
   ```
   Docker Desktop/PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\trigger-alert.ps1`

   It starts a small robot inside the cluster that calls the failing page about 1,000 times (roughly 4 minutes), then waits and tells you when the alarm fires: `HighErrorRate is FIRING after about 150 seconds.`
2. Look at the Grafana **Error rate** chart: it climbs. In Prometheus (**Alerts**) and Alertmanager, `HighErrorRate` turns red (firing). The **SLO and Error Budget** dashboard shows the error budget being spent, and `ErrorBudgetFastBurn` fires too.

The robot stops by itself. A few minutes later the error rate drops and the alerts clear on their own.

---

## 6. Optional: get alerts in Slack and email

Without this step the alarms still work; you just see them in Alertmanager instead of getting a message. Real passwords go in one private file, `k8s/alertmanager-secret.yaml`, which Git never uploads.

### 6a. Get a Slack webhook (a private address that posts into a channel)

1. Go to <https://api.slack.com/apps> and sign in to your Slack workspace.
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
Change these lines (keep the quotes), then save with **Ctrl + O**, **Enter**, **Ctrl + X**:

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
   Docker Desktop/PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\deploy.ps1`
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

The add-ons are started with a Python script (Python 3 comes with Ubuntu; on Mac run `brew install python@3.12` if `python3 --version` fails or shows 3.9, and use `python3.12` instead of `python3`). Run **one at a time** and remove it before the next, so Minikube does not run out of memory.

Add-ons need a 6 GB Minikube on a 16 GB laptop (see [labs/01, step 4](labs/01-foundations.md)). On an 8 GB laptop, stay with the core stack. For example:
```bash
python3 scripts/chaos_test.py
```
Docker Desktop/PowerShell: `python scripts\chaos_test.py`

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
  Then open the tunnels again (step 4).
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
| Windows: `Cannot connect to the Docker daemon` or `permission denied ... docker.sock` | Close and reopen the Ubuntu window. If it persists, run `sudo systemctl start docker`. Check step 4 of the Windows install (systemd) was done. |
| `command not found` for `minikube`, `kubectl` or `helm` | The install step for that tool did not finish. Run it again and reopen the window. |
| `permission denied: ./scripts/deploy.sh` | Run `chmod +x scripts/deploy.sh` once, then try again. |
| `No such file or directory` for `scripts/deploy.sh` or `k8s/...` | You are not in the project folder. Run `cd ~/sre-final-project`. |
| `Docker has only ...MB of memory` (from deploy.sh) or `Docker has only ...MB memory but you specified 4096MB` (from Minikube) | Docker has too little memory. Windows: do step 2 of the Windows install (`.wslconfig`), run `wsl --shutdown` and reopen Ubuntu. Mac: `colima stop` then `colima start --cpu 4 --memory 6`. Then run `minikube delete` and `./scripts/deploy.sh` again. |
| Pods stuck in `Pending` or `ContainerCreating` for more than 5 minutes | The computer is short on memory. Mac: `colima stop` then `colima start --cpu 4 --memory 6`. Windows: close other programs. Then run `minikube delete` and `./scripts/deploy.sh` again. |
| A pod shows `CrashLoopBackOff` | Run `kubectl get pods -A` again in a minute; Kubernetes retries on its own. If it stays, run `./scripts/deploy.sh` again. |
| Browser says "This site can't be reached" on localhost | The tunnel window was closed or stopped. Run the port-forward command again and keep that window open. |
| `address already in use` when opening a tunnel | Another tunnel already uses that port. Close the other window, or run `pkill -f "kubectl port-forward"` and open the tunnels again. |
| A copied command fails with `No such file or directory` and has `<` `>` in it | Text inside `< >` is a placeholder to replace. The commands in this guide do not need any changes. |
| Grafana rejects the password | Run `grep admin-password k8s/grafana-secret.yaml` again and copy the text between the quotes exactly. |
| No Slack or email message | Check the logs: `kubectl logs deployment/alertmanager -n monitoring --tail=30`. `no_team` or `invalid_token` means a wrong Slack URL. `535` means a wrong email address or app password. Fix the file, then repeat step 6e. |
| You changed a setting and nothing happened | Settings are read at start-up. Run `kubectl rollout restart deployment/alertmanager -n monitoring` (or `prometheus`, `grafana`). |

---

## Glossary

| Term | Meaning |
| --- | --- |
| **Alert / alarm** | A rule that turns "on" when a measurement crosses a limit for some time. |
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
