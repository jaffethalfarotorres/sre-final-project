#!/usr/bin/env bash
set -euo pipefail

USE_HELM=false
if [[ "${1:-}" == "--helm" || "${1:-}" == "helm" ]]; then
  USE_HELM=true
fi

REQUIRED_COMMANDS=(minikube kubectl docker)
if [[ "$USE_HELM" == true ]]; then
  REQUIRED_COMMANDS+=(helm)
fi

for command in "${REQUIRED_COMMANDS[@]}"; do
  command -v "$command" >/dev/null || { echo "$command is required." >&2; exit 1; }
done

# Credentials (Alertmanager Slack/SMTP and Grafana admin) live in gitignored Secrets.
# On a fresh clone they do not exist yet, so create them from the examples:
#  - Grafana gets a random admin credential, readable later from the cluster Secret.
#  - Alertmanager keeps the placeholders: alerts still route, only delivery to
#    Slack/email fails until real values are pasted into the file.
SECRET_FILE="k8s/alertmanager-secret.yaml"
GRAFANA_SECRET_FILE="k8s/grafana-secret.yaml"
if [[ ! -f "$SECRET_FILE" ]]; then
  cp k8s/alertmanager-secret.example.yaml "$SECRET_FILE"
  echo "Created $SECRET_FILE with placeholders (edit it to enable Slack/email)."
fi
if [[ ! -f "$GRAFANA_SECRET_FILE" ]]; then
  generated="$(od -An -N12 -tx1 /dev/urandom | tr -d ' \n')"
  sed "s/change-me-before-applying/${generated}/" k8s/grafana-secret.example.yaml > "$GRAFANA_SECRET_FILE"
  echo "Created $GRAFANA_SECRET_FILE with a random Grafana admin credential."
fi


if [[ "$(minikube status -p minikube --format='{{.Host}}' 2>/dev/null || true)" != "Running" ]]; then
  minikube start --driver=docker
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
  echo "Deploying via raw Kubernetes manifests..."
  kubectl apply -f k8s/prometheus.yaml
  kubectl apply -f k8s/rbac.yaml
  kubectl apply -f "$SECRET_FILE"
  kubectl apply -f "$GRAFANA_SECRET_FILE"
  kubectl apply -f k8s/alertmanager.yaml
  kubectl apply -f k8s/grafana.yaml
  kubectl apply -f k8s/application.yaml

  kubectl rollout status deployment/sre-metrics-app -n application --timeout=180s
  kubectl rollout status deployment/prometheus -n monitoring --timeout=180s
  kubectl rollout status deployment/alertmanager -n monitoring --timeout=180s
  kubectl rollout status deployment/grafana -n monitoring --timeout=180s

  cat <<'EOF'
Deployment complete. Use separate terminals for:
  kubectl port-forward -n monitoring service/grafana 3000:3000
  kubectl port-forward -n monitoring service/prometheus 9090:9090
  kubectl port-forward -n monitoring service/alertmanager 9093:9093
EOF
fi

echo "Grafana login: user admin, credential stored in k8s/grafana-secret.yaml (admin-password)."
