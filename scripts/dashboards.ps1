# Opens Grafana, Prometheus, Alertmanager, the app and Jaeger in your browser with one command (Windows PowerShell).
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dashboards.ps1              # keep the window open
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dashboards.ps1 -Background  # start and return (IBM Bob)
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dashboards.ps1 -Stop        # close background tunnels
# The lab login is admin / admin. A password you set yourself is copied to the clipboard, never printed.
param([switch]$Background, [switch]$Stop)
# "Continue": in Windows PowerShell 5.1 a kubectl check that fails on purpose must not stop the script.
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)
$pidFile = Join-Path (Get-Location) ".lab\tunnels.pid"

function Stop-Tunnels {
    if (-not (Test-Path $pidFile)) { Write-Host "No background tunnels are recorded."; return }
    foreach ($id in Get-Content $pidFile) {
        $p = Get-Process -Id $id -ErrorAction SilentlyContinue
        # Only stop the kubectl processes this script started.
        if ($p -and $p.ProcessName -eq "kubectl") { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }
    }
    Remove-Item $pidFile -ErrorAction SilentlyContinue
    Write-Host "Background tunnels closed."
}

if ($Stop) { Stop-Tunnels; exit 0 }
if (Test-Path $pidFile) { Stop-Tunnels }  # never leave two sets of tunnels fighting for the same ports

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
$forwards += , @("opentelemetry", "service/jaeger", "16686:16686")
# The Grafana MCP server for AI assistants exists only after scripts/ai_setup.py has run.
kubectl get service mcp-grafana -n monitoring *> $null
$hasMcp = ($LASTEXITCODE -eq 0)
if ($hasMcp) { $forwards += , @("monitoring", "service/mcp-grafana", "8000:8000") }

$processes = @()
try {
    foreach ($f in $forwards) {
        $common = @{ FilePath = "kubectl"; ArgumentList = @("port-forward", "-n", $f[0], $f[1], $f[2]); PassThru = $true
            RedirectStandardOutput = [System.IO.Path]::GetTempFileName(); RedirectStandardError = [System.IO.Path]::GetTempFileName() }
        if ($Background) { $processes += Start-Process @common -WindowStyle Hidden }
        else { $processes += Start-Process @common -NoNewWindow }
    }
    Start-Sleep -Seconds 3

    $encoded = kubectl get secret grafana-admin-credentials -n monitoring -o jsonpath='{.data.admin-password}' 2>$null
    $passwordNote = "see k8s/grafana-secret.yaml"
    if ($encoded) {
        $plain = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($encoded))
        if ($plain -eq "admin") { $passwordNote = "admin" }
        else { $plain | Set-Clipboard; $passwordNote = "copied to your clipboard: paste it with Ctrl+V" }
    }

    Write-Host ""
    Write-Host "  Grafana       http://localhost:3000   (user: admin, password $passwordNote)"
    Write-Host "  Prometheus    http://localhost:9090"
    Write-Host "  Alertmanager  http://localhost:9093"
    Write-Host "  The app       http://localhost:5000"
    Write-Host "  Jaeger        http://localhost:16686"
    if ($hasMcp) { Write-Host "  MCP (AI)      http://localhost:8000/mcp  (IBM Bob and Claude Code, see docs/AI-SRE.md)" }
    Write-Host ""
    Start-Process "http://localhost:3000"

    if ($Background) {
        New-Item -ItemType Directory -Force (Split-Path $pidFile) | Out-Null
        $processes | ForEach-Object { $_.Id } | Set-Content $pidFile
        $processes = @()  # keep them running after this script returns
        Write-Host "The tunnels run in the background. Close them with:"
        Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\dashboards.ps1 -Stop"
        exit 0
    }
    Write-Host "Keep this window open while you use them. Press Ctrl+C to close the tunnels."
    while ($true) { Start-Sleep -Seconds 1 }
}
finally {
    $processes | Where-Object { -not $_.HasExited } | Stop-Process -Force -ErrorAction SilentlyContinue
}
