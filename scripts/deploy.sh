#!/usr/bin/env bash
# Deploys the whole stack on Minikube. Works on macOS (Colima) and Windows (WSL2 + Ubuntu).
# Usage: ./scripts/deploy.sh            raw Kubernetes manifests (default)
#        ./scripts/deploy.sh --helm     Helm chart + kube-prometheus-stack
set -euo pipefail
cd "$(dirname "$0")/.."

USE_HELM=false
if [[ "${1:-}" == "--helm" || "${1:-}" == "helm" ]]; then
  USE_HELM=true
fi

REQUIRED_COMMANDS=(minikube kubectl docker)
if [[ "$USE_HELM" == true ]]; then
  REQUIRED_COMMANDS+=(helm)
fi

for command in "${REQUIRED_COMMANDS[@]}"; do
  command -v "$command" >/dev/null || {
    echo "$command is not installed. See docs/GUIDE.md, step 2 (Install the tools)." >&2
    exit 1
  }
done

# Docker must be running before Minikube can start.
if ! docker info >/dev/null 2>&1; then
  if [[ "$(uname -s)" == "Darwin" ]] && command -v colima >/dev/null; then
    echo "Docker is not running. Starting Colima (about a minute)..."
    colima start --cpu 4 --memory 6 --disk 60
  else
    echo "Docker is not running." >&2
    echo "  Mac: run 'colima start'." >&2
    echo "  Windows (WSL2 + Ubuntu): run 'sudo systemctl start docker', or reopen the Ubuntu window." >&2
    exit 1
  fi
fi

# Credentials (Alertmanager Slack/SMTP and Grafana admin) live in gitignored Secrets.
# On a fresh clone they do not exist yet, so create them from the examples:
#  - Grafana gets the lab login admin / admin (local only; edit the file for your own password).
#  - Alertmanager keeps the placeholders: alerts still route, only delivery to
#    Slack/email fails until real values are pasted into the file.
SECRET_FILE="k8s/alertmanager-secret.yaml"
GRAFANA_SECRET_FILE="k8s/grafana-secret.yaml"
if [[ ! -f "$SECRET_FILE" ]]; then
  cp k8s/alertmanager-secret.example.yaml "$SECRET_FILE"
  echo "Created $SECRET_FILE with placeholders (edit it to enable Slack/email)."
fi
if [[ ! -f "$GRAFANA_SECRET_FILE" ]]; then
  cp k8s/grafana-secret.example.yaml "$GRAFANA_SECRET_FILE"
  echo "Created $GRAFANA_SECRET_FILE with the lab login admin / admin."
fi


if [[ "$(minikube status -p minikube --format='{{.Host}}' 2>/dev/null || true)" != "Running" ]]; then
  # 4 GB fits the core stack only; add-ons need 6 GB (docs/labs/01 step 4).
  # Minikube refuses more memory than Docker has, so check that first (WSL gives Docker
  # only half of the laptop's RAM unless .wslconfig says otherwise).
  docker_bytes="$(docker info --format '{{.MemTotal}}' 2>/dev/null || echo 0)"
  limit_mb=$(( docker_bytes / 1048576 - 256 ))
  mem=$(( limit_mb < 4096 ? limit_mb : 4096 ))
  if (( mem < 3500 )); then
    echo "Docker has only ${limit_mb}MB of memory; Minikube needs about 4096MB." >&2
    echo "Is Docker running? Windows: raise WSL memory in %USERPROFILE%\\.wslconfig. Mac: colima start --memory 6. See docs/GUIDE.md." >&2
    exit 1
  fi
  minikube start --driver=docker --memory="$mem"
fi

minikube image build -t sre-metrics-app:1.0.0 .

if [[ "$USE_HELM" == true ]]; then
  echo "Deploying via Helm..."
  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
  helm repo update

  # The Secret must exist before the chart mounts it into Alertmanager.
  kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
  kubectl apply -f "$SECRET_FILE"
  kubectl apply -f "$GRAFANA_SECRET_FILE"

  helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
    --namespace monitoring \
    --create-namespace \
    -f helm/values-monitoring.yaml

  helm upgrade --install sre-metrics-app helm/sre-metrics-app \
    --namespace application \
    --create-namespace
  # The image is rebuilt with the same tag (1.0.0), so Kubernetes would keep the old pods running the old code.
  # Restart the app so every deploy runs the image that was just built.
  kubectl rollout restart deployment/sre-metrics-app -n application

  kubectl rollout status deployment/sre-metrics-app -n application --timeout=180s
  kubectl rollout status deployment/kube-prometheus-stack-operator -n monitoring --timeout=180s

  cat <<'EOF'
Helm deployment complete. Use separate terminals for:
  kubectl port-forward -n monitoring service/kube-prometheus-stack-grafana 3000:80
  kubectl port-forward -n monitoring service/kube-prometheus-stack-prometheus 9090:9090
  kubectl port-forward -n monitoring service/kube-prometheus-stack-alertmanager 9093:9093
  kubectl port-forward -n application service/sre-metrics-app 5000:5000
EOF
else
  echo "Deploying the full stack with Kustomize (kubectl apply -k k8s)..."
  kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
  kubectl apply -f "$SECRET_FILE"
  kubectl apply -f "$GRAFANA_SECRET_FILE"
  kubectl apply -k k8s
  # The image is rebuilt with the same tag (1.0.0), so Kubernetes would keep the old pods running the old code.
  # Restart the app so every deploy runs the image that was just built.
  kubectl rollout restart deployment/sre-metrics-app -n application

  for deployment in monitoring/prometheus monitoring/alertmanager monitoring/grafana monitoring/blackbox-exporter \
    opentelemetry/otel-collector opentelemetry/jaeger opentelemetry/loki application/sre-metrics-app; do
    kubectl rollout status "deployment/${deployment#*/}" -n "${deployment%%/*}" --timeout=300s
  done

  echo "Deployment complete."
fi

echo "Grafana login: user admin, credential stored in k8s/grafana-secret.yaml (admin-password)."
echo "Next: run ./scripts/dashboards.sh to open Grafana, Prometheus and Alertmanager in your browser."
