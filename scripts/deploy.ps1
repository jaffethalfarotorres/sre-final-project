# Deploys the whole stack on Minikube from Windows PowerShell with Docker Desktop.
# (Windows users on WSL2 + Ubuntu, and Mac users, run scripts/deploy.sh instead.)
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\deploy.ps1 [-Helm]
param(
    [switch]$Helm
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

# "Stop" does not stop the script when a native program (minikube, kubectl, helm) fails
# in Windows PowerShell 5.1, so check each exit code ourselves and stop on the first failure.
# Kept as a simple function (no param block) so flags like -n and -o pass straight through.
function Invoke-Native {
    $exe = $args[0]
    $rest = @()
    if ($args.Count -gt 1) { $rest = $args[1..($args.Count - 1)] }
    & $exe @rest
    if ($LASTEXITCODE -ne 0) { throw "'$exe $($rest -join ' ')' failed with exit code $LASTEXITCODE" }
}
function Assert-LastExit([string]$What) {
    if ($LASTEXITCODE -ne 0) { throw "$What failed with exit code $LASTEXITCODE" }
}

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is not installed. See docs/GUIDE.md, step 2 (Install the tools)."
    }
}

Require-Command minikube
Require-Command kubectl
Require-Command docker

if ($Helm) {
    Require-Command helm
}

# Docker must be running before Minikube can start. Start Docker Desktop if it is installed.
function Test-Docker {
    # A failing native command must not stop the script here (Windows PowerShell 5.1 behavior).
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    docker info 2>$null | Out-Null
    $ErrorActionPreference = $previous
    return ($LASTEXITCODE -eq 0)
}
if (-not (Test-Docker)) {
    $desktop = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path $desktop)) { $desktop = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\Docker Desktop.exe" }
    if (-not (Test-Path $desktop)) { throw "Docker is not running. Open Docker Desktop and wait for 'Engine running', then retry." }
    Write-Host "Docker is not running. Starting Docker Desktop (up to 3 minutes)..."
    Start-Process $desktop
    $deadline = (Get-Date).AddMinutes(3)
    while (-not (Test-Docker)) {
        if ((Get-Date) -gt $deadline) { throw "Docker Desktop did not start in time. Open it, wait for 'Engine running', then retry." }
        Start-Sleep -Seconds 5
    }
}

# Credentials (Alertmanager Slack/SMTP and Grafana admin) live in gitignored Secrets.
# On a fresh clone they do not exist yet, so create them from the examples:
#  - Grafana gets a random admin credential, readable later from the file.
#  - Alertmanager keeps the placeholders: alerts still route, only delivery to
#    Slack/email fails until real values are pasted into the file.
$SecretFile = "k8s/alertmanager-secret.yaml"
$GrafanaSecretFile = "k8s/grafana-secret.yaml"
if (-not (Test-Path $SecretFile)) {
    Copy-Item k8s/alertmanager-secret.example.yaml $SecretFile
    Write-Host "Created $SecretFile with placeholders (edit it to enable Slack/email)."
}
if (-not (Test-Path $GrafanaSecretFile)) {
    $generated = [guid]::NewGuid().ToString('N').Substring(0, 24)
    $content = (Get-Content k8s/grafana-secret.example.yaml -Raw) -replace 'change-me-before-applying', $generated
    [System.IO.File]::WriteAllText((Join-Path (Get-Location) $GrafanaSecretFile), $content)
    Write-Host "Created $GrafanaSecretFile with a random Grafana admin credential."
}

$ErrorActionPreference = "Continue"
$minikubeHost = minikube status -p minikube --format='{{.Host}}' 2>$null
$ErrorActionPreference = "Stop"
if ($minikubeHost -ne 'Running') {
    # 4 GB is enough for the full observability stack (see docs/GUIDE.md for the add-ons).
    Invoke-Native minikube start --driver=docker --memory=4096
}

Invoke-Native minikube image build -t sre-metrics-app:1.0.0 .

if ($Helm) {
    Write-Host "Deploying via Helm..."
    # Re-adding a repo that already exists must not stop the script (deploy.sh uses '|| true').
    $ErrorActionPreference = "Continue"
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts *> $null
    $ErrorActionPreference = "Stop"
    if ($LASTEXITCODE -ne 0) { Write-Host "helm repo add returned $LASTEXITCODE (repo may already exist with another URL; check 'helm repo list')." }
    Invoke-Native helm repo update

    # The Secret must exist before the chart mounts it into Alertmanager.
    kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
    Assert-LastExit "kubectl apply namespace monitoring"
    Invoke-Native kubectl apply -f $SecretFile
    Invoke-Native kubectl apply -f $GrafanaSecretFile

    Invoke-Native helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack `
        --namespace monitoring `
        --create-namespace `
        -f helm/values-monitoring.yaml

    Invoke-Native helm upgrade --install sre-metrics-app helm/sre-metrics-app `
        --namespace application `
        --create-namespace
    # The image is rebuilt with the same tag (1.0.0), so Kubernetes would keep the old pods running the old code.
    # Restart the app so every deploy runs the image that was just built.
    Invoke-Native kubectl rollout restart deployment/sre-metrics-app -n application

    Invoke-Native kubectl rollout status deployment/sre-metrics-app -n application --timeout=180s
    Invoke-Native kubectl rollout status deployment/kube-prometheus-stack-operator -n monitoring --timeout=180s

    Write-Host "Helm deployment complete. Use separate terminals for:"
    Write-Host "  kubectl port-forward -n monitoring service/kube-prometheus-stack-grafana 3000:80"
    Write-Host "  kubectl port-forward -n monitoring service/kube-prometheus-stack-prometheus 9090:9090"
    Write-Host "  kubectl port-forward -n monitoring service/kube-prometheus-stack-alertmanager 9093:9093"
    Write-Host "  kubectl port-forward -n application service/sre-metrics-app 5000:5000"
}
else {
    Write-Host "Deploying the full stack with Kustomize (kubectl apply -k k8s)..."
    kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
    Assert-LastExit "kubectl apply namespace monitoring"
    Invoke-Native kubectl apply -f $SecretFile
    Invoke-Native kubectl apply -f $GrafanaSecretFile
    Invoke-Native kubectl apply -k k8s
    # The image is rebuilt with the same tag (1.0.0), so Kubernetes would keep the old pods running the old code.
    # Restart the app so every deploy runs the image that was just built.
    Invoke-Native kubectl rollout restart deployment/sre-metrics-app -n application

    foreach ($d in "monitoring/prometheus", "monitoring/alertmanager", "monitoring/grafana", "monitoring/blackbox-exporter",
        "opentelemetry/otel-collector", "opentelemetry/jaeger", "opentelemetry/loki", "application/sre-metrics-app") {
        $ns, $name = $d.Split("/")
        Invoke-Native kubectl rollout status "deployment/$name" -n $ns --timeout=300s
    }

    Write-Host "Deployment complete."
}

Write-Host "Grafana login: user admin, credential stored in k8s/grafana-secret.yaml (admin-password)."
Write-Host "Next: run 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dashboards.ps1' to open the dashboards."
