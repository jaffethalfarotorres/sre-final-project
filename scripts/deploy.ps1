param(
    [switch]$Helm
)

$ErrorActionPreference = "Stop"

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is required. Install it and retry."
    }
}

Require-Command minikube
Require-Command kubectl
Require-Command docker

if ($Helm) {
    Require-Command helm
}

# Credentials (Alertmanager Slack/SMTP and Grafana admin) live in gitignored Secrets.
$SecretFile = "k8s/alertmanager-secret.yaml"
$GrafanaSecretFile = "k8s/grafana-secret.yaml"
foreach ($f in $SecretFile, $GrafanaSecretFile) {
    if (-not (Test-Path $f)) {
        $example = $f -replace '\.yaml$', '.example.yaml'
        throw "$f not found. Copy $example to $f, fill in real values, and retry."
    }
}

if ((minikube status -p minikube --format='{{.Host}}' 2>$null) -ne 'Running') {
    minikube start --driver=docker
}

minikube image build -t sre-metrics-app:1.0.0 .

if ($Helm) {
    Write-Host "Deploying via Helm..."
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>$null
    helm repo update

    # The Secret must exist before the chart mounts it into Alertmanager.
    kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
    kubectl apply -f $SecretFile
    kubectl apply -f $GrafanaSecretFile

    helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack `
        --namespace monitoring `
        --create-namespace `
        -f helm/values-monitoring.yaml

    helm upgrade --install sre-metrics-app helm/sre-metrics-app `
        --namespace application `
        --create-namespace

    kubectl rollout status deployment/sre-metrics-app -n application --timeout=180s
    kubectl rollout status deployment/kube-prometheus-stack-operator -n monitoring --timeout=180s

    Write-Host "Helm deployment complete. Use separate terminals for:"
    Write-Host "  kubectl port-forward -n monitoring service/kube-prometheus-stack-grafana 3000:80"
    Write-Host "  kubectl port-forward -n monitoring service/kube-prometheus-stack-prometheus 9090:9090"
    Write-Host "  kubectl port-forward -n monitoring service/kube-prometheus-stack-alertmanager 9093:9093"
    Write-Host "  kubectl port-forward -n application service/sre-metrics-app 5000:5000"
}
else {
    Write-Host "Deploying via raw Kubernetes manifests..."
    kubectl apply -f k8s/prometheus.yaml
    kubectl apply -f k8s/rbac.yaml
    kubectl apply -f $SecretFile
    kubectl apply -f $GrafanaSecretFile
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
}
