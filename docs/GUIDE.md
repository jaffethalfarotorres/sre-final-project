# Step-by-step guide (no experience needed)

This guide explains the project in plain language and walks you through running it on your own computer, one step at a time. You do not need to know Kubernetes or programming. If a word is new, check the [glossary](#glossary) at the end.

- [1. What is this project?](#1-what-is-this-project)
- [2. Install the tools (one time)](#2-install-the-tools-one-time)
- [3. Download and start the project](#3-download-and-start-the-project)
- [4. Look at the dashboards](#4-look-at-the-dashboards)
- [5. Make an alert fire](#5-make-an-alert-fire)
- [6. Optional: get alerts in Slack and email](#6-optional-get-alerts-in-slack-and-email)
- [7. Optional: publish the app image to Docker Hub](#7-optional-publish-the-app-image-to-docker-hub)
- [8. Stop and clean up](#8-stop-and-clean-up)
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
| `AlwaysFiringDemoAlert` | Always on. It only proves the alarm system works. |

Everything runs locally. Nothing is sent to the internet unless you set up Slack or email in step 6.

---

## 2. Install the tools (one time)

You need about 8 GB of free memory and 20 GB of free disk space.

### Windows

1. **Docker Desktop.** Download it from <https://www.docker.com/products/docker-desktop/>, install it, restart your computer if asked, and open it once. Wait until it says **Engine running** in the bottom-left corner.
2. **The other tools.** Open the **Start** menu, type `PowerShell`, and open **Windows PowerShell**. Copy and paste this line, then press **Enter**:
   ```powershell
   winget install -e --id Git.Git; winget install -e --id Kubernetes.minikube; winget install -e --id Kubernetes.kubectl; winget install -e --id Helm.Helm
   ```
   Accept any prompts. When it finishes, **close PowerShell and open it again** so it finds the new tools.
3. **Check.** Paste this. Each line should print a version number, not an error:
   ```powershell
   git --version; minikube version; kubectl version --client; docker --version
   ```

### macOS

1. **Docker Desktop.** Download it from <https://www.docker.com/products/docker-desktop/> (pick Apple chip or Intel chip), install it and open it once.
2. **Homebrew** (a tool installer), if you do not have it: follow the one-line instructions on <https://brew.sh>.
3. **The other tools.** Open **Terminal** and run:
   ```bash
   brew install git minikube kubectl helm
   ```

### Linux

Install Docker Engine (<https://docs.docker.com/engine/install/>), then Minikube (<https://minikube.sigs.k8s.io/docs/start/>), `kubectl` and Helm (<https://helm.sh/docs/intro/install/>) with your package manager.

---

## 3. Download and start the project

1. Make sure **Docker Desktop is open and running**.
2. Open PowerShell (Windows) or Terminal (macOS/Linux).
3. Download the project and go into its folder:
   ```bash
   git clone https://github.com/jaffethalfarotorres/sre-final-project.git
   cd sre-final-project
   ```
4. Start everything with one command.

   Windows:
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\deploy.ps1
   ```
   macOS or Linux:
   ```bash
   ./scripts/deploy.sh
   ```

The first run takes 5 to 10 minutes because it downloads everything. You will see a lot of text. It is done when it prints **Deployment complete**.

What the script does for you: it starts the mini data center (Minikube), builds the shop app, creates a private Grafana login, starts all the pieces and waits until they are healthy.

5. Check that everything is running:
   ```bash
   kubectl get pods -A
   ```
   Every line should say `Running` and `1/1` (or `2/2`, `3/3`). If some say `ContainerCreating`, wait a minute and run it again.

---

## 4. Look at the dashboards

The pieces run inside Minikube, so you open a "tunnel" (called a port-forward) to see each one in your browser. **Each tunnel needs its own PowerShell or Terminal window, and that window must stay open.** Run these commands from the `sre-final-project` folder.

### Grafana (the charts)

1. In a new window, run:
   ```bash
   kubectl port-forward -n monitoring service/grafana 3000:3000
   ```
2. Open <http://localhost:3000> in your browser.
3. Log in:
   - Username: `admin`
   - Password: open the file `k8s/grafana-secret.yaml` in the project folder (Notepad or TextEdit is fine) and copy the value after `admin-password:` without the quotes. The deploy script made this password for you.
4. Click **Dashboards** in the left menu, then **SRE Metrics Demo**. You will see four live charts: requests per second, response time, error rate and total requests.

### Prometheus (the raw measurements and alarm rules)

1. In another new window:
   ```bash
   kubectl port-forward -n monitoring service/prometheus 9090:9090
   ```
2. Open <http://localhost:9090>.
3. Click **Status > Targets**. The app should show a green **UP**.
4. Click **Alerts** to see the four alarm rules and which ones are active.

### Alertmanager (who gets notified)

1. In another new window:
   ```bash
   kubectl port-forward -n monitoring service/alertmanager 9093:9093
   ```
2. Open <http://localhost:9093>. After about a minute you will see `AlwaysFiringDemoAlert`. That means the alarm pipeline works.

To close a tunnel, click its window and press **Ctrl + C**.

> If you started the project with the Helm option (`-Helm` or `--helm`), the names are different: use `service/kube-prometheus-stack-grafana 3000:80`, `service/kube-prometheus-stack-prometheus 9090:9090` and `service/kube-prometheus-stack-alertmanager 9093:9093`.

---

## 5. Make an alert fire

The shop fails about 5% of the time on its own, which is just under the alarm limit on purpose. To see a real alarm, send it a burst of bad requests.

1. Start a robot that calls the failing page about 1,000 times (roughly 4 minutes). This command works the same in PowerShell and Terminal:
   ```bash
   kubectl run errload -n application --image=curlimages/curl:8.10.1 --restart=Never --command -- sh -c 'i=0; while [ $i -lt 1000 ]; do curl -s -o /dev/null http://sre-metrics-app:5000/error; i=$((i+1)); sleep 0.2; done'
   ```
2. Wait about **2 to 3 minutes**.
3. Look at the Grafana **Error rate** chart: it climbs. In Prometheus (**Alerts**) and Alertmanager, `HighErrorRate` turns red (firing).
4. When you are done, remove the robot:
   ```bash
   kubectl delete pod errload -n application
   ```

A few minutes later the error rate drops and the alert clears on its own.

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

Using Outlook or another provider? You need its SMTP server address and port (for Outlook.com: `smtp-mail.outlook.com:587`) and an app password from that provider.

### 6c. Put the secrets in the private file

1. Open `k8s/alertmanager-secret.yaml` in a text editor. (It exists after you ran the deploy script once. If not, copy `k8s/alertmanager-secret.example.yaml` to that name.)
2. Replace the text between the quotes:
   ```yaml
   slack-webhook-url: "PASTE-YOUR-SLACK-WEBHOOK-URL-HERE"
   smtp-auth-password: "PASTE-YOUR-16-LETTER-APP-PASSWORD-HERE"
   ```
3. Save the file.

### 6d. Put your email addresses in the settings

Open `k8s/alertmanager.yaml` and change these lines (keep the quotes):

| Line | Change to |
| --- | --- |
| `smtp_smarthost: 'smtp.gmail.com:587'` | Leave as is for Gmail, or your provider's server. |
| `smtp_from: 'sre-alerts@example.com'` | Your Gmail address. |
| `smtp_auth_username: 'sre-alerts@example.com'` | Your Gmail address. |
| `- to: 'sre-oncall@example.com'` (appears twice) | The address that should receive alerts. |

If you use the Helm option, make the same changes in `helm/values-monitoring.yaml`.

Note: `k8s/alertmanager.yaml` is a normal project file. If you upload your copy to GitHub, these email addresses become public. The passwords stay private.

### 6e. Apply the changes and test

1. Run the deploy script again (same command as in step 3).
2. Restart Alertmanager so it reads the new settings:
   ```bash
   kubectl rollout restart deployment/alertmanager -n monitoring
   ```
   (Helm option: `kubectl delete pod alertmanager-kube-prometheus-stack-alertmanager-0 -n monitoring`. It comes back by itself.)
3. Do [step 5](#5-make-an-alert-fire) again. In about 3 minutes a `HighErrorRate` message arrives in Slack and in the email inbox.
4. Take screenshots (Windows: **Windows + Shift + S**; macOS: **Cmd + Shift + 4**) and save them as `docs/screenshots/slack-notification.png` and `docs/screenshots/email-notification.png`.

Nothing arrives? See [Troubleshooting](#troubleshooting).

---

## 7. Optional: publish the app image to Docker Hub

This is only for the owner of a copy of the project on GitHub. It makes GitHub build the app and upload it to Docker Hub automatically (that is the "CD" part).

1. **Create a Docker Hub token.** Sign in at <https://hub.docker.com>, open your profile menu > **Account settings > Personal access tokens > Generate new token**. Name it `github-cd`, choose **Read & Write**, click **Generate**, and copy the token.
2. **Store it in GitHub.** On your repository page go to **Settings > Secrets and variables > Actions > New repository secret** and create two secrets:
   - Name `DOCKERHUB_USERNAME`, value: your Docker Hub username.
   - Name `DOCKERHUB_TOKEN`, value: the token from step 1.
3. **Start a release.** On the repository page click **Releases > Draft a new release**. In **Choose a tag** type `v1.0.0` and click **Create new tag**. Give it a title such as `v1.0.0` and click **Publish release**.
4. **Watch it.** Open the **Actions** tab. The **CD** workflow starts and should end with a green check in a few minutes. Your image then appears at `https://hub.docker.com/r/<your-username>/sre-metrics-app`.

You can also start it by hand: **Actions > CD > Run workflow**.

---

## 8. Stop and clean up

- **Pause** (keeps everything for next time):
  ```bash
  minikube stop
  ```
  Next time, open Docker Desktop and run `minikube start`, then open the tunnels again.
- **Remove the project** from Minikube:
  ```bash
  kubectl delete namespace application monitoring
  ```
- **Remove Minikube completely** (frees the most space):
  ```bash
  minikube delete
  ```

---

## Troubleshooting

| What you see | What to do |
| --- | --- |
| `docker: command not found` or "cannot connect to the Docker daemon" | Open Docker Desktop and wait for **Engine running**, then try again. |
| `minikube`, `kubectl` or `helm` is "not recognized" | Close and reopen PowerShell or Terminal after installing. |
| Windows: "running scripts is disabled on this system" | Use the full command from step 3 that starts with `powershell -NoProfile -ExecutionPolicy Bypass`. |
| macOS/Linux: `permission denied: ./scripts/deploy.sh` | Run `chmod +x scripts/deploy.sh` once, then try again. |
| Pods stuck in `Pending` or `ContainerCreating` for more than 5 minutes | Give Docker Desktop more memory (**Settings > Resources**, at least 6 GB), then run `minikube delete` and the deploy script again. |
| Browser says "This site can't be reached" on localhost | The tunnel window was closed. Run the port-forward command again and keep that window open. |
| "address already in use" when opening a tunnel | Another tunnel already uses that port. Close the other window, or on Windows run `Get-Process kubectl \| Stop-Process`. |
| Grafana rejects the password | Copy it again from `k8s/grafana-secret.yaml`, without the quotes or spaces. |
| No Slack or email message | Check the logs: `kubectl logs deployment/alertmanager -n monitoring --tail=30`. `invalid_token` or `no_team` means a wrong Slack URL. `535` means a wrong email address or app password. Fix the file, then repeat step 6e. |

---

## Glossary

| Term | Meaning |
| --- | --- |
| **Alert / alarm** | A rule that turns "on" when a measurement crosses a limit for some time. |
| **Container** | A sealed box that holds one program and everything it needs, so it runs the same anywhere. |
| **Docker** | The tool that builds and runs containers. |
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
