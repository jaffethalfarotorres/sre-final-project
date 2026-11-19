# Opens Grafana, Prometheus, Alertmanager and the app in your browser with one command (Windows PowerShell).
# Keep this window open; press Ctrl+C to close the tunnels.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dashboards.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

# Raw manifests and Helm use different Service names; detect which one is installed.
kubectl get service kube-prometheus-stack-grafana -n monitoring *> $null
if ($LASTEXITCODE -eq 0) {
    $forwards = @(
        @("monitoring", "service/kube-prometheus-stack-grafana", "3000:80"),
        @("monitoring", "service/kube-prometheus-stack-prometheus", "9090:9090"),
        @("monitoring", "service/kube-prometheus-stack-alertmanager", "9093:9093")
    )
} else {
    $forwards = @(
        @("monitoring", "service/grafana", "3000:3000"),
        @("monitoring", "service/prometheus", "9090:9090"),
        @("monitoring", "service/alertmanager", "9093:9093")
    )
}
$forwards += , @("application", "service/sre-metrics-app", "5000:5000")

$processes = @()
try {
    foreach ($f in $forwards) {
        $processes += Start-Process kubectl -ArgumentList "port-forward", "-n", $f[0], $f[1], $f[2] -NoNewWindow -PassThru `
            -RedirectStandardOutput ([System.IO.Path]::GetTempFileName()) -RedirectStandardError ([System.IO.Path]::GetTempFileName())
    }
    Start-Sleep -Seconds 3

    $encoded = kubectl get secret grafana-admin-credentials -n monitoring -o jsonpath='{.data.admin-password}' 2>$null
    $password = if ($encoded) { [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($encoded)) } else { "see k8s/grafana-secret.yaml" }

    Write-Host ""
    Write-Host "  Grafana       http://localhost:3000   (user: admin, password: $password)"
    Write-Host "  Prometheus    http://localhost:9090"
    Write-Host "  Alertmanager  http://localhost:9093"
    Write-Host "  The app       http://localhost:5000"
    Write-Host ""
    Write-Host "Keep this window open while you use them. Press Ctrl+C to close the tunnels."
    Start-Process "http://localhost:3000"

    while ($true) { Start-Sleep -Seconds 1 }
}
finally {
    $processes | Where-Object { -not $_.HasExited } | Stop-Process -Force -ErrorAction SilentlyContinue
}
