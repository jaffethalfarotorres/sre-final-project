#!/usr/bin/env bash
# One-command setup kit for Mac (and Linux with Homebrew): installs only the lab tools that are missing.
#   ./scripts/install-tools.sh --dry-run   # only show what is missing
#   ./scripts/install-tools.sh             # install what is missing, then run the preflight check
# It uses Homebrew. On a Mac without Docker Desktop it installs Colima (free) as the container engine.
# It never changes security settings. Works with macOS bash 3.2.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

# Apple silicon Homebrew lives in /opt/homebrew and is often not on PATH yet in a new terminal.
if ! command -v brew >/dev/null 2>&1 && [[ -x /opt/homebrew/bin/brew ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
fi
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is not installed. Install it from https://brew.sh (it asks for your Mac password),"
  echo "then open a new Terminal and run this script again. On an IBM laptop, see docs/IT-REQUEST.md."
  exit 1
fi

# command | brew formula | plain description
TOOLS="git|git|Git: downloads and saves the project
gh|gh|GitHub CLI: makes your own copy (fork) of the project
python3|python@3.12|Python 3.10+: runs the lab scripts
kubectl|kubectl|kubectl: talks to Kubernetes
minikube|minikube|Minikube: a small Kubernetes on your laptop
helm|helm|Helm: installs packaged apps on Kubernetes (optional, not needed for your first shift)"

python_ok() {
  # Apple's python3 is often 3.9, which is too old for the lab.
  command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'
}

MISSING=""
while IFS='|' read -r cmd formula desc; do
  if [[ "$cmd" == "python3" ]] && ! python_ok; then
    echo "  MISSING  $desc"; MISSING="$MISSING $formula"
  elif [[ "$cmd" != "python3" ]] && ! command -v "$cmd" >/dev/null 2>&1; then
    echo "  MISSING  $desc"; MISSING="$MISSING $formula"
  else
    echo "  OK       $desc"
  fi
done <<EOF
$TOOLS
EOF

ENGINE=""
if command -v docker >/dev/null 2>&1; then
  echo "  OK       Container engine (docker command found)"
else
  echo "  MISSING  Container engine: Colima (free) and the docker command"
  ENGINE="colima docker"
fi

if [[ $DRY_RUN -eq 1 ]]; then
  echo; echo "Dry run: nothing was installed."
  exit 0
fi

FAILED=""
for formula in $MISSING $ENGINE; do
  echo; echo "Installing $formula ..."
  brew install "$formula" || FAILED="$FAILED $formula"
done

if [[ -n "$ENGINE" ]] && command -v colima >/dev/null 2>&1; then
  echo
  echo "Colima is installed. deploy.sh starts it for you. On an 8 GB Mac start it first with less memory:"
  echo "  colima start --cpu 2 --memory 4"
fi

if [[ -n "$FAILED" ]]; then
  echo; echo "These installs did not finish:$FAILED"
  echo "On an IBM laptop this usually needs an IT approval: see docs/IT-REQUEST.md."
fi

echo; echo "Checking the laptop (read-only):"
if python_ok; then
  python3 scripts/preflight.py
else
  echo "Python is not ready yet. Open a new Terminal and run: python3 scripts/preflight.py"
fi

# Homebrew changes PATH for new terminals; terminals that were already open may not find the new tools.
echo; echo "Close this terminal and open a new one (in your AI coding agent too) before the next step, so the new tools are found."
