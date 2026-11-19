# Sends a burst of failing requests to /error and waits until the HighErrorRate alert fires (Windows PowerShell).
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\trigger-alert.ps1
$ErrorActionPreference = "Stop"

kubectl get service kube-prometheus-stack-alertmanager -n monitoring *> $null
$amService = if ($LASTEXITCODE -eq 0) { "kube-prometheus-stack-alertmanager" } else { "alertmanager" }
$alertsUrl = "/api/v1/namespaces/monitoring/services/${amService}:9093/proxy/api/v2/alerts"

# A short-lived pod inside the cluster calls /error about 1,000 times (~4 minutes), then stops by itself.
kubectl delete pod errload -n application --ignore-not-found *> $null
kubectl run errload -n application --image=curlimages/curl:8.10.1 --restart=Never --command -- `
    sh -c 'i=0; while [ $i -lt 1000 ]; do curl -s -o /dev/null http://sre-metrics-app:5000/error; i=$((i+1)); sleep 0.2; done' | Out-Null
Write-Host "Sending failing requests to the app. The HighErrorRate alert needs about 2-3 minutes to fire..."

for ($i = 1; $i -le 36; $i++) {
    $alerts = kubectl get --raw $alertsUrl 2>$null
    if ($alerts -match '"alertname":"HighErrorRate"') {
        Write-Host "HighErrorRate is FIRING after about $($i * 10) seconds."
        Write-Host "See it in Alertmanager (http://localhost:9093) and in Grafana's Error rate panel."
        Write-Host "If Slack/email are configured, a notification is on its way."
        exit 0
    }
    Start-Sleep -Seconds 10
}
Write-Error "The alert has not fired yet. Check 'kubectl get pods -A' and try again."
