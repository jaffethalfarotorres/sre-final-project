# SRE Metrics Demo – Helm Infrastructure as Code (IaC)

This directory contains Helm charts and values files for deploying the complete SRE Metrics Demo stack on Kubernetes (Minikube).

## Architecture

The deployment is split into two complementary Helm components:

1. **`sre-metrics-app/`** (Custom Helm Chart):
   - Deploys the Python Flask WSGI application (`sre-metrics-app`).
   - Deploys the automated traffic generator (`traffic-generator` using `curlimages/curl`).
   - Creates the application `Service`.
   - Optionally creates a `ServiceMonitor` or `PodMonitor` for native Prometheus Operator integration.
   - Fully parameterized via [`values.yaml`](sre-metrics-app/values.yaml).

2. **`values-monitoring.yaml`** (Upstream `kube-prometheus-stack` Configuration):
   - Configures the official [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack) chart.
   - Provisions Prometheus with cross-namespace ServiceMonitor discovery.
   - Injects the custom Prometheus alerting rules (`ServiceDown`, `HighErrorRate`, `HighLatency`, `AlwaysFiringDemoAlert`).
   - Injects multi-channel Alertmanager configuration (Slack webhook & SMTP email).
   - Injects the custom 4-panel Grafana dashboard (`SRE Metrics Demo`) and pre-configured admin credentials.

---

## Prerequisites

- [Minikube](https://minikube.sigs.k8s.io/) with Docker driver
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Helm v3](https://helm.sh/)

---

## Quickstart Deployment via Helm

### 1. Build Application Image in Minikube
```bash
minikube image build -t sre-metrics-app:1.0.0 .
```

To use a registry image instead (for example the one pushed by CD), override the repository, tag, and pull policy in step 4:
```bash
helm upgrade --install sre-metrics-app helm/sre-metrics-app -n application --create-namespace \
  --set image.repository=<dockerhub-user>/sre-metrics-app --set image.tag=<tag> --set image.pullPolicy=Always
```

### 1b. Create the Alertmanager Secret (Slack webhook + SMTP password)
`values-monitoring.yaml` mounts a Secret named `alertmanager-secret` into Alertmanager. Create it before installing the monitoring stack. The real file is gitignored.
```bash
cp k8s/alertmanager-secret.example.yaml k8s/alertmanager-secret.yaml   # then edit the values
kubectl create namespace monitoring
kubectl apply -f k8s/alertmanager-secret.yaml
```
Also edit the `smtp_*` and `to:` addresses in [`values-monitoring.yaml`](values-monitoring.yaml). The deploy scripts perform the Secret step automatically.

### 2. Add Prometheus Community Helm Repository
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

### 3. Deploy Monitoring Stack (`kube-prometheus-stack`)
```bash
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  -f helm/values-monitoring.yaml
```

### 4. Deploy Application Stack (`sre-metrics-app`)
```bash
helm upgrade --install sre-metrics-app helm/sre-metrics-app \
  --namespace application \
  --create-namespace
```

---

## Verifying Deployments

Check pod status in both namespaces:
```bash
kubectl get pods -n application
kubectl get pods -n monitoring
```

Port-forward to access services:
```bash
# Flask Application & Metrics:
kubectl port-forward -n application service/sre-metrics-app 5000:5000

# Grafana Dashboard (admin / admin, or your own password from k8s/grafana-secret.yaml):
kubectl port-forward -n monitoring service/kube-prometheus-stack-grafana 3000:80

# Prometheus UI:
kubectl port-forward -n monitoring service/kube-prometheus-stack-prometheus 9090:9090

# Alertmanager UI:
kubectl port-forward -n monitoring service/kube-prometheus-stack-alertmanager 9093:9093
```

---

## Parameterization & Values Reference (`sre-metrics-app`)

| Parameter | Description | Default |
| --- | --- | --- |
| `replicaCount` | Number of application replicas | `1` |
| `image.repository` | App container image repository | `sre-metrics-app` |
| `image.tag` | App container image tag | `1.0.0` |
| `image.pullPolicy` | Image pull policy (`IfNotPresent`, `Never`, `Always`) | `IfNotPresent` |
| `service.type` | Kubernetes Service type | `ClusterIP` |
| `service.port` | Service port | `5000` |
| `resources.requests.cpu` | Requested CPU for Flask app | `50m` |
| `resources.requests.memory` | Requested memory for Flask app | `64Mi` |
| `resources.limits.cpu` | CPU limit for Flask app | `250m` |
| `resources.limits.memory` | Memory limit for Flask app | `128Mi` |
| `trafficGenerator.enabled` | Whether to enable continuous traffic generator | `true` |
| `trafficGenerator.intervalSeconds` | Delay between simulated requests | `2` |
| `serviceMonitor.enabled` | Deploy Prometheus Operator `ServiceMonitor` | `true` |
| `podAnnotations` | Pod annotations (for raw Prometheus pod discovery) | Scrape enabled on port 5000 |
