# SRE Metrics Demo

[![CI](https://github.com/jaffethalfarotorres/sre-final-project/actions/workflows/ci.yml/badge.svg)](https://github.com/jaffethalfarotorres/sre-final-project/actions/workflows/ci.yml)
[![CD](https://github.com/jaffethalfarotorres/sre-final-project/actions/workflows/cd.yml/badge.svg)](https://github.com/jaffethalfarotorres/sre-final-project/actions/workflows/cd.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE.md)
[![Python 3.10](https://img.shields.io/badge/Python-3.10-3776AB.svg?logo=python&logoColor=white)](app/app.py)

**In plain words:** this project runs a tiny pretend online shop on your computer, measures how healthy it is, shows those measurements as live charts, and raises an alarm (in Slack and email) when something goes wrong. It is the kind of setup Site Reliability Engineers use to keep real services running.

> **New to this? Start with the [step-by-step guide](docs/GUIDE.md).** It explains every piece in plain language and walks you through installing the tools, running the project, seeing the charts and triggering an alert. No Kubernetes experience needed.

**Technical summary:** a small Kubernetes observability project for the SRE Academy final project. A Python 3.10 Flask application (`app/app.py`, instrumented with `prometheus_client` and tested with pytest) exposes Prometheus metrics. Prometheus scrapes and evaluates alert rules, Alertmanager sends notifications to Slack and email, and Grafana visualizes the data. It can be deployed with plain manifests or with Helm, and it is validated by GitHub Actions.

**Skills shown:** application instrumentation, Kubernetes deployment, Prometheus scraping and alert rules (SLO-style error-rate and latency alerts), Grafana dashboards as code, Alertmanager routing to Slack and email, Helm (IaC), and CI/CD with GitHub Actions.

## Quick start

Works on **macOS** (Colima, Apple Silicon or Intel) and **Windows** (WSL2 + Ubuntu), the same toolchain as the SRE Academy course. You need Docker, [Minikube](https://minikube.sigs.k8s.io/docs/start/) and `kubectl`; the [guide](docs/GUIDE.md#2-install-the-tools-one-time) installs them step by step. No accounts or credentials are required to run the demo.

In Terminal (Mac) or the Ubuntu window (Windows):

```bash
colima start                   # Mac only
git clone https://github.com/jaffethalfarotorres/sre-final-project.git
cd sre-final-project
./scripts/deploy.sh
```

Using Docker Desktop with PowerShell on Windows instead? Run `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\deploy.ps1`.

The script starts Minikube, builds the image, creates local Secrets from the examples (with a random Grafana admin credential), deploys everything and waits for it to be ready. Then open the services with the port-forward commands in [Access the services](#access-the-services).

## Architecture

```mermaid
flowchart LR
    TG[Traffic generator] -->|GET /store every 2s| APP[Flask app<br/>/store /error /metrics]
    PROM[Prometheus] -->|scrape /metrics| APP
    PROM -->|firing alerts| AM[Alertmanager]
    AM -->|notifications| SLACK[Slack]
    AM -->|notifications| EMAIL[Email]
    GRAF[Grafana] -->|PromQL| PROM
```

| Namespace | Components |
| --- | --- |
| `application` | `sre-metrics-app` (Gunicorn, 1 worker + 4 threads), `traffic-generator` |
| `monitoring` | Prometheus, Alertmanager, Grafana (raw manifests) or kube-prometheus-stack (Helm) |

## Requirements covered

| Requirement | Implementation |
| --- | --- |
| 1. Application | [`app/app.py`](app/app.py): `http_requests_total` (counter) and `http_request_duration_seconds` (histogram). `/store` fails about 5% of the time and `/error` always fails, so alerts have real signals. |
| 2. Kubernetes deployment | [`k8s/`](k8s/) manifests for Minikube, with resource limits, probes and a non-root container. |
| 3. Prometheus | Pod discovery by annotation (raw) or a `ServiceMonitor` (Helm). Rules in [`k8s/prometheus.yaml`](k8s/prometheus.yaml). |
| 4. Grafana | Provisioned datasource and a 4-panel dashboard (request rate, p95 latency, error rate, total requests). |
| 5. Alertmanager | Deployed with severity-based routing. |
| 6. Documentation | This README, [`LICENSE.md`](LICENSE.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), commented code and screenshots. |
| Bonus: notifications | Slack and email receivers in [`k8s/alertmanager.yaml`](k8s/alertmanager.yaml). |
| Bonus: IaC | Helm chart [`helm/sre-metrics-app/`](helm/sre-metrics-app/) plus `kube-prometheus-stack` values ([`helm/values-monitoring.yaml`](helm/values-monitoring.yaml)). |
| Bonus: CI/CD | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) and [`cd.yml`](.github/workflows/cd.yml). |

## Alert rules

| Alert | Condition | Severity |
| --- | --- | --- |
| `ServiceDown` | `up == 0` for 1 minute | critical |
| `HighErrorRate` | 5xx ratio above 5% for 2 minutes | critical |
| `HighLatency` | p95 latency above 500 ms for 2 minutes | warning |
| `AlwaysFiringDemoAlert` | `vector(1)`, a smoke test for the alert pipeline | demo |

The built-in 5% error rate on `/store` stays below the 5% threshold on purpose. To trigger `HighErrorRate`, generate load on `/error` (see [Trigger an alert](#trigger-an-alert)).

## Prerequisites

- **macOS:** Homebrew, Colima (`colima start --cpu 4 --memory 6 --disk 60`), `docker` CLI
- **Windows:** WSL2 with Ubuntu and Docker Engine (or Docker Desktop with PowerShell)
- [Minikube](https://minikube.sigs.k8s.io/docs/start/) with the Docker driver
- `kubectl`
- [Helm 3](https://helm.sh/) (only for the Helm path)

Step-by-step install commands for both systems are in [`docs/GUIDE.md`](docs/GUIDE.md#2-install-the-tools-one-time).

## Configure notifications (optional)

The stack runs without this step: alerts still fire and route in Alertmanager, only delivery to Slack and email fails. To receive real notifications:

1. Edit `k8s/alertmanager-secret.yaml` (the deploy script creates it from [`k8s/alertmanager-secret.example.yaml`](k8s/alertmanager-secret.example.yaml); it is gitignored and **never committed**):
   - `slack-webhook-url`: a Slack incoming-webhook URL.
   - `smtp-auth-password`: an SMTP password or app password (for example a Google App Password).
2. In [`k8s/alertmanager.yaml`](k8s/alertmanager.yaml) (and [`helm/values-monitoring.yaml`](helm/values-monitoring.yaml) for Helm), set `smtp_smarthost`, `smtp_from`, `smtp_auth_username` and the `to:` addresses to your own.
3. Run the deploy script again.

Only the two Secret files (`k8s/alertmanager-secret.yaml`, `k8s/grafana-secret.yaml`) are gitignored. The configuration files with addresses are tracked.

## Deploy

From the repository root, choose one shell and one method.

**Raw manifests**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\deploy.ps1
```

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

**Helm**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\deploy.ps1 -Helm
```

```bash
./scripts/deploy.sh --helm
```

The scripts start Minikube when necessary, build the image inside Minikube, apply the Secret, deploy the stack and wait for the rollouts. See [`helm/README.md`](helm/README.md) for the Helm details and image overrides.

## Access the services

Run each command in a separate terminal.

| Service | Raw manifests | Helm |
| --- | --- | --- |
| Grafana | `kubectl port-forward -n monitoring service/grafana 3000:3000` | `kubectl port-forward -n monitoring service/kube-prometheus-stack-grafana 3000:80` |
| Prometheus | `kubectl port-forward -n monitoring service/prometheus 9090:9090` | `kubectl port-forward -n monitoring service/kube-prometheus-stack-prometheus 9090:9090` |
| Alertmanager | `kubectl port-forward -n monitoring service/alertmanager 9093:9093` | `kubectl port-forward -n monitoring service/kube-prometheus-stack-alertmanager 9093:9093` |

- Grafana: <http://localhost:3000>, login `admin` with the `admin-password` value from `k8s/grafana-secret.yaml` (generated by the deploy script on first run).
- Prometheus: <http://localhost:9090>, open **Status > Targets** and confirm the app is `UP`.
- Alertmanager: <http://localhost:9093>, wait about a minute for `AlwaysFiringDemoAlert`.

## Trigger an alert

```bash
kubectl -n application port-forward service/sre-metrics-app 5000:5000
# in another terminal: send failing requests for a few minutes
while true; do curl -s -o /dev/null http://localhost:5000/error; sleep 0.2; done
```

After about two minutes `HighErrorRate` fires, and a notification arrives in Slack and email.

## Verification

```bash
kubectl get pods -A
```

All application and monitoring pods are Running, the Prometheus target is UP, the Grafana panels contain data, and Alertmanager shows the alerts.

## Evidence

Screenshots of the working deployment are stored in [`docs/screenshots/`](docs/screenshots/).

**All pods running** (`kubectl get pods -A`)

![All pods running](docs/screenshots/pods.png)

**Prometheus target UP** (Status > Targets)

![Prometheus targets](docs/screenshots/prometheus-targets.png)

**Grafana dashboard with live data**

![Grafana dashboard](docs/screenshots/grafana-dashboard.png)

**Prometheus alerts**

![Prometheus alerts](docs/screenshots/prometheus-alerts.png)

**Alertmanager with `AlwaysFiringDemoAlert` and a firing `HighErrorRate`** (triggered by load on `/error`)

![Alertmanager alerts](docs/screenshots/alertmanager-alert.png)

**Helm deployment** (`helm list -A` and the pods of both namespaces)

![Helm deployment](docs/screenshots/helm-deployment.png)

**Prometheus target UP through the Helm `ServiceMonitor`**

![Helm Prometheus targets](docs/screenshots/helm-prometheus-targets.png)

> Slack and email routing is configured, but the committed example uses placeholder credentials. Alertmanager logs show delivery attempts failing with `no_team` (Slack) and `535 BadCredentials` (SMTP) until real credentials are supplied in `k8s/alertmanager-secret.yaml`.

## CI/CD

- **CI** runs on every push and pull request: flake8, pytest, `helm lint`, `kubeconform`, `promtool check rules`, `amtool check-config` and a Docker build.
- **CD** runs on `v*` tags (for example `git tag v1.0.0 && git push --tags`) and manually from the Actions tab. It pushes the image to Docker Hub and runs a `kind` smoke test. It needs the repository secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`.

Run the checks locally:

```bash
pip install -r requirements-dev.txt
flake8 app tests --max-line-length=120
pytest tests -q
helm lint helm/sre-metrics-app
```

## Cleanup

```bash
kubectl delete namespace application monitoring
# Helm: helm uninstall sre-metrics-app -n application && helm uninstall kube-prometheus-stack -n monitoring
```

## Notes

This is a classroom demonstration. Data is ephemeral, and the Grafana demo password is for local use only. Keep real webhook URLs and passwords out of Git.

## License

MIT, see [`LICENSE.md`](LICENSE.md). Contributions are welcome, see [`CONTRIBUTING.md`](CONTRIBUTING.md).
