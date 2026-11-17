# SRE Metrics Demo

A small Kubernetes observability project for the SRE Academy final project. It demonstrates an application exposing Prometheus metrics, Prometheus collection and alerting, Grafana visualization, and Alertmanager handling.

## Architecture

```text
Traffic generator -> Flask application (/store, /metrics)
                         |
                         v
                    Prometheus ----> Alertmanager
                         |
                         v
                      Grafana
```

The traffic generator calls `/store` every two seconds. This creates live request and latency metrics without manual browser traffic.

## Requirements covered

| Requirement | Implementation |
| --- | --- |
| Application Development | Flask app exposes `/metrics` with a request counter and latency histogram. |
| Kubernetes Deployment | Deployments and Services run the app and monitoring stack on Minikube. |
| Prometheus Integration | Kubernetes pod discovery scrapes the annotated app pod. |
| Grafana Visualization | A provisioned dashboard displays request rate, p95 latency, and request totals. |
| Alertmanager Deployment | Prometheus forwards `AlwaysFiringDemoAlert` to Alertmanager. |
| Professional Documentation | This README, contributing guide, license, manifests, scripts, and screenshot checklist are included. |

## Prerequisites

- Docker Desktop running
- [Minikube](https://minikube.sigs.k8s.io/docs/start/) with the Docker driver
- `kubectl`
- PowerShell on Windows, or Bash/WSL2

## Deploy

From the repository root, choose one shell:

```powershell
./scripts/deploy.ps1
```

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

The scripts start Minikube when necessary, build the local application image inside Minikube, apply the manifests, and wait for all main Deployments to be ready.

## Access the services

Run each command in a separate terminal, then open the shown local URL.

```bash
kubectl port-forward -n monitoring service/grafana 3000:3000
kubectl port-forward -n monitoring service/prometheus 9090:9090
kubectl port-forward -n monitoring service/alertmanager 9093:9093
```

- Grafana: http://localhost:3000 — initial local-demo login: `admin` / `admin`.
- Prometheus: http://localhost:9090 — open **Status > Targets** and confirm the application target is `UP`.
- Alertmanager: http://localhost:9093 — wait about one minute for `AlwaysFiringDemoAlert` to appear.

Grafana opens with a provisioned **SRE Demo / SRE Metrics Demo** dashboard. Allow a minute of traffic before inspecting the latency panel.

## Verification

```bash
kubectl get pods -A
```

Successful verification means all application and monitoring pods are Running, the Prometheus target is UP, the Grafana panels contain data, and Alertmanager displays `AlwaysFiringDemoAlert`.

## Screenshots for submission

Save evidence in `docs/screenshots/`:

1. `pods.png`: `kubectl get pods -A` showing all pods running.
2. `prometheus-targets.png`: Prometheus Targets page showing `sre-metrics-app` as UP.
3. `grafana-dashboard.png`: provisioned dashboard with live data.
4. `alertmanager-alert.png`: Alertmanager showing `AlwaysFiringDemoAlert`.

## Cleanup

```bash
kubectl delete namespace application monitoring
```

## Publish to GitHub

Review the files and screenshots, then create an empty public GitHub repository named `sre-final-project`. From this directory, initialize Git, commit the project, add the GitHub remote, and push the default branch. Do not include credentials, kubeconfig files, or personal data.

## Notes

This is intentionally a classroom demonstration: data is ephemeral, the Alertmanager receiver discards notifications, and the always-firing rule exists solely to demonstrate the Prometheus-to-Alertmanager integration. Replace the demo receiver and rule before using this pattern beyond a lab.
