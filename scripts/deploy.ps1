$ErrorActionPreference = "Stop"

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is required. Install it and retry."
    }
}

Require-Command minikube
Require-Command kubectl
Require-Command docker

if ((minikube status -p minikube --format='{{.Host}}' 2>$null) -ne 'Running') {
    minikube start --driver=docker
}

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

Write-Host "Deployment complete. Use separate terminals for:"
Write-Host "  kubectl port-forward -n monitoring service/grafana 3000:3000"
Write-Host "  kubectl port-forward -n monitoring service/prometheus 9090:9090"
Write-Host "  kubectl port-forward -n monitoring service/alertmanager 9093:9093"
