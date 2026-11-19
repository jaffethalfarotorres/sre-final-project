# One-command setup kit for Windows (PowerShell 5.1 or 7): installs only the lab tools that are missing.
# Usage (from the sre-final-project folder):
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-tools.ps1 -DryRun    # only show what is missing
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-tools.ps1 -Engine rancher
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-tools.ps1 -Engine docker
# -Engine picks the container engine when none is installed: "rancher" (Rancher Desktop, free) or "docker"
# (Docker Desktop, needs a company licence). Without -Engine the script installs everything else and tells you.
#
# With winget it installs per user where possible. Many IBM laptops have no winget: then kubectl, minikube, helm and gh
# are downloaded as single programs into %USERPROFILE%\tools\bin (no admin rights; each file is checked against its
# published SHA-256) and that folder is added to your user PATH. Git, Python and the container engine need an installer:
# the script prints the official download page. It never changes security settings, and ends with the preflight check.
param(
    [ValidateSet("", "rancher", "docker")][string]$Engine = "",
    [switch]$DryRun
)
# "Continue": a failing check must not stop the script in Windows PowerShell 5.1.
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"   # Invoke-WebRequest is very slow with the progress bar in PowerShell 5.1
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Set-Location (Split-Path $PSScriptRoot -Parent)

$ToolsBin = Join-Path $env:USERPROFILE "tools\bin"
$HelmVersion = "v3.16.2"
$GhVersion = "2.105.0"

function Update-SessionPath {
    # Installers change PATH for new terminals only; reload it so the next commands find the new tools.
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
    if ((Test-Path $ToolsBin) -and ($env:Path -notlike "*$ToolsBin*")) { $env:Path += ";$ToolsBin" }
}

function Test-Tool([string]$Command) {
    $found = Get-Command $Command -ErrorAction SilentlyContinue
    if (-not $found) { return $false }
    # The Microsoft Store "python" alias is not a real Python.
    if ($Command -eq "python" -and $found.Source -like "*WindowsApps*") { return $false }
    return $true
}

function Add-ToolsBinToUserPath {
    New-Item -ItemType Directory -Force $ToolsBin | Out-Null
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notlike "*$ToolsBin*") {
        [Environment]::SetEnvironmentVariable("Path", (($userPath.TrimEnd(";") + ";" + $ToolsBin).TrimStart(";")), "User")
        Write-Host "Added $ToolsBin to your user PATH."
    }
}

function Get-Text([string]$Url) {
    # PowerShell 5.1 returns bytes, not text, when the server does not say the file is text.
    $content = (Invoke-WebRequest -UseBasicParsing -Uri $Url).Content
    if ($content -is [byte[]]) { return [Text.Encoding]::ASCII.GetString($content) }
    return [string]$content
}

function Get-Verified([string]$Url, [string]$OutFile, [string]$ExpectedSha256) {
    Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $OutFile
    $actual = (Get-FileHash -Algorithm SHA256 $OutFile).Hash.ToLower()
    if ($actual -ne $ExpectedSha256.Trim().ToLower()) {
        Remove-Item $OutFile -Force
        throw "Checksum mismatch for $Url (the download was deleted)."
    }
}

function Install-Portable([string]$Name) {
    # Downloads one single-file tool into $ToolsBin and checks its SHA-256. Returns $true on success.
    Add-ToolsBinToUserPath
    $tmp = Join-Path $env:TEMP ("sre-kit-" + [Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force $tmp | Out-Null
    try {
        switch ($Name) {
            "kubectl" {
                $version = (Get-Text "https://dl.k8s.io/release/stable.txt").Trim()
                $url = "https://dl.k8s.io/release/$version/bin/windows/amd64/kubectl.exe"
                $sha = Get-Text "$url.sha256"
                Get-Verified $url (Join-Path $ToolsBin "kubectl.exe") $sha
            }
            "minikube" {
                $url = "https://github.com/kubernetes/minikube/releases/latest/download/minikube-windows-amd64.exe"
                $sha = (Get-Text "$url.sha256").Trim().Split(" ")[0]
                Get-Verified $url (Join-Path $ToolsBin "minikube.exe") $sha
            }
            "helm" {
                $file = "helm-$HelmVersion-windows-amd64.zip"
                $sha = (Get-Text "https://get.helm.sh/$file.sha256sum").Trim().Split(" ")[0]
                Get-Verified "https://get.helm.sh/$file" (Join-Path $tmp $file) $sha
                Expand-Archive (Join-Path $tmp $file) $tmp -Force
                Copy-Item (Join-Path $tmp "windows-amd64\helm.exe") $ToolsBin -Force
            }
            "gh" {
                $file = "gh_${GhVersion}_windows_amd64.zip"
                $base = "https://github.com/cli/cli/releases/download/v$GhVersion"
                $sums = Get-Text "$base/gh_${GhVersion}_checksums.txt"
                $line = ($sums -split "`n" | Where-Object { $_ -like "*$file" }) | Select-Object -First 1
                Get-Verified "$base/$file" (Join-Path $tmp $file) ($line.Split(" ")[0])
                Expand-Archive (Join-Path $tmp $file) $tmp -Force
                Copy-Item (Join-Path $tmp "bin\gh.exe") $ToolsBin -Force
            }
            default { return $false }
        }
        return $true
    }
    catch {
        Write-Host "  Download failed: $($_.Exception.Message)"
        return $false
    }
    finally {
        Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
    }
}

# command | winget package id | extra winget arguments | plain description | page to install by hand
$tools = @(
    @("git", "Git.Git", "", "Git: downloads and saves the project", "https://git-scm.com/download/win (PortableGit needs no admin)"),
    @("gh", "GitHub.cli", "", "GitHub CLI: makes your own copy (fork) of the project", ""),
    @("python", "Python.Python.3.12", "--scope user", "Python 3.10+: runs the lab scripts",
        "https://www.python.org/downloads/windows/ (choose 'Install for me only' and tick 'Add python.exe to PATH')"),
    @("kubectl", "Kubernetes.kubectl", "", "kubectl: talks to Kubernetes", ""),
    @("minikube", "Kubernetes.minikube", "", "Minikube: a small Kubernetes on your laptop", ""),
    @("helm", "Helm.Helm", "", "Helm: installs packaged apps on Kubernetes (optional, not needed for your first shift)", "")
)

Update-SessionPath
$missing = @()
foreach ($t in $tools) {
    if (Test-Tool $t[0]) { Write-Host ("  OK       {0}" -f $t[3]) }
    else { Write-Host ("  MISSING  {0}" -f $t[3]); $missing += , $t }
}
$hasEngine = Test-Tool "docker"
if ($hasEngine) { Write-Host "  OK       Container engine (docker command found)" }
else { Write-Host "  MISSING  Container engine: Rancher Desktop (free) or Docker Desktop (licence)" }
$hasWinget = [bool](Get-Command winget -ErrorAction SilentlyContinue)
if (-not $hasWinget) { Write-Host "`nwinget is not available here: single-file tools go to $ToolsBin, the rest needs an installer." }

if ($DryRun) {
    Write-Host "`nDry run: nothing was installed."
    exit 0
}

$failed = @()
foreach ($t in $missing) {
    Write-Host ("`nInstalling {0} ..." -f $t[3])
    if ($hasWinget) {
        $arguments = @("install", "-e", "--id", $t[1], "--silent", "--accept-package-agreements", "--accept-source-agreements")
        if ($t[2]) { $arguments += $t[2].Split(" ") }
        & winget @arguments
        if ($LASTEXITCODE -ne 0) { $failed += $t[3] }
    }
    elseif ($t[4]) {
        Write-Host "  Install it from $($t[4]), then run this script again."
        $failed += $t[3]
    }
    elseif (-not (Install-Portable $t[0])) { $failed += $t[3] }
    else { Write-Host "  Installed into $ToolsBin" }
}

if (-not $hasEngine) {
    if ($Engine -and -not $hasWinget) {
        Write-Host "`nInstall the container engine by hand: https://rancherdesktop.io (free) or https://www.docker.com/products/docker-desktop (licence)."
        $failed += "Container engine"
    }
    elseif ($Engine -eq "rancher") {
        Write-Host "`nInstalling Rancher Desktop (free) ..."
        & winget install -e --id SUSE.RancherDesktop --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) { $failed += "Rancher Desktop" }
        Write-Host "First start of Rancher Desktop: choose the 'dockerd (moby)' engine and turn Kubernetes OFF (Minikube provides it)."
    }
    elseif ($Engine -eq "docker") {
        Write-Host "`nInstalling Docker Desktop (needs a company licence) ..."
        & winget install -e --id Docker.DockerDesktop --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) { $failed += "Docker Desktop" }
    }
    else {
        Write-Host "`nNo container engine was installed. Run this script again with -Engine rancher (free) or -Engine docker (licence)."
        Write-Host "Not sure which one IBM allows on your laptop? See docs/IT-REQUEST.md."
    }
}

Update-SessionPath
if ($failed.Count -gt 0) {
    Write-Host "`nStill to do: $($failed -join ', ')"
    Write-Host "If an install needs admin rights or an approval, see docs/IT-REQUEST.md."
}

Write-Host "`nChecking the laptop (read-only):"
if (Test-Tool "python") { & python scripts\preflight.py }
else { Write-Host "Python is not ready yet. Install it, open a new PowerShell window and run: python scripts\preflight.py" }

# This script refreshed PATH only for itself. Terminals that were already open still have the old PATH.
Write-Host "`nClose this terminal and open a new one (in your AI coding agent too) before the next step, so the new tools are found."
