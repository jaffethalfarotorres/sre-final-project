# Alert drill: sends failing requests to /error and waits until the HighErrorRate alert fires (Windows PowerShell).
# HighErrorRate fires after about 3 minutes; the error budget page ErrorBudgetFastBurn follows a few
# minutes later (about 6-10 minutes after the start).
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\trigger-alert.ps1
# "Continue": in Windows PowerShell 5.1 a kubectl check that fails on purpose must not stop the script.
$ErrorActionPreference = "Continue"

kubectl get service kube-prometheus-stack-alertmanager -n monitoring *> $null
$amService = if ($LASTEXITCODE -eq 0) { "kube-prometheus-stack-alertmanager" } else { "alertmanager" }
$alertsUrl = "/api/v1/namespaces/monitoring/services/${amService}:9093/proxy/api/v2/alerts"

# A short-lived pod inside the cluster calls /error 3,000 times (about 12-14 minutes), then stops by itself.
Set-Location (Split-Path $PSScriptRoot -Parent)
kubectl delete pod errload -n application --ignore-not-found *> $null
kubectl apply -f k8s/drills/errload-pod.yaml | Out-Null
Write-Host "Drill started: the errload pod sends failing requests to the app for about 12-14 minutes."
Write-Host "Waiting for the HighErrorRate alert. It needs about 3 minutes (5-minute window, then 2 minutes of 'for')..."

for ($i = 1; $i -le 48; $i++) {
    $alerts = kubectl get --raw $alertsUrl 2>$null
    if ($alerts -match '"alertname":"HighErrorRate"') {
        Write-Host "HighErrorRate is FIRING after about $($i * 10) seconds."
        Write-Host "See it in Alertmanager (http://localhost:9093) and in Grafana's Error rate panel."
        Write-Host "If Slack/email are configured, a notification is on its way."
        Write-Host ""
        Write-Host "Keep watching: the error budget page ErrorBudgetFastBurn fires later, about 6-10 minutes after"
        Write-Host "the start. It waits until the 1-hour error ratio is above 14.4% (burn rate 14.4x with a 99% SLO)."
        Write-Host "Refresh Alertmanager and the 'SLO and Error Budget' dashboard. The drill pod stops by itself."
        exit 0
    }
    Start-Sleep -Seconds 10
}
Write-Error "HighErrorRate has not fired after 8 minutes. Check 'kubectl get pods -A' and try again."
exit 1
