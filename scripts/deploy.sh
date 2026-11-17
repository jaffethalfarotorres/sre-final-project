#!/usr/bin/env bash
set -euo pipefail

for command in minikube kubectl docker; do
  command -v "$command" >/dev/null || { echo "$command is required." >&2; exit 1; }
done

if [[ "$(minikube status -p minikube --format='{{.Host}}' 2>/dev/null || true)" != "Running" ]]; then
  minikube start --driver=docker
fi

minikube image build -t sre-metrics-app:1.0.0 .
kubectl apply -f k8s/prometheus.yaml
kubectl apply -f k8s/rbac.yaml
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
