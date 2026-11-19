#!/usr/bin/env bash
# Opens Grafana, Prometheus, Alertmanager, the app and Jaeger in your browser with one command.
# Works on macOS and Linux/WSL2.
#   ./scripts/dashboards.sh               keep this window open; Ctrl+C closes the tunnels
#   ./scripts/dashboards.sh --background  start the tunnels and return (use this from IBM Bob)
#   ./scripts/dashboards.sh --stop        close the background tunnels
# The lab login is admin / admin. A password you set yourself is copied to the clipboard, never printed.
set -euo pipefail
cd "$(dirname "$0")/.."
PID_FILE=".lab/tunnels.pid"
MODE="${1:-}"

stop_tunnels() {
  if [[ ! -f "$PID_FILE" ]]; then echo "No background tunnels are recorded."; return 0; fi
  while read -r pid; do
    # Only stop the kubectl processes this script started.
    if [[ -n "$pid" ]] && ps -p "$pid" -o comm= 2>/dev/null | grep -q kubectl; then kill "$pid" 2>/dev/null || true; fi
  done < "$PID_FILE"
  rm -f "$PID_FILE"
  echo "Background tunnels closed."
}

case "$MODE" in
  --stop) stop_tunnels; exit 0 ;;
  --background|"") ;;
  *) echo "Usage: $0 [--background|--stop]"; exit 2 ;;
esac
[[ -f "$PID_FILE" ]] && stop_tunnels  # never leave two sets of tunnels fighting for the same ports

# Raw manifests and Helm use different Service names; detect which one is installed.
if kubectl get service kube-prometheus-stack-grafana -n monitoring >/dev/null 2>&1; then
  GRAFANA="service/kube-prometheus-stack-grafana 3000:80"
  PROMETHEUS="service/kube-prometheus-stack-prometheus 9090:9090"
  ALERTMANAGER="service/kube-prometheus-stack-alertmanager 9093:9093"
else
  GRAFANA="service/grafana 3000:3000"
  PROMETHEUS="service/prometheus 9090:9090"
  ALERTMANAGER="service/alertmanager 9093:9093"
fi

PIDS=()
forward() {  # forward <namespace> <service> <ports>
  if [[ "$MODE" == --background ]]; then
    nohup kubectl port-forward -n "$1" "$2" "$3" >/dev/null 2>&1 &
  else
    kubectl port-forward -n "$1" "$2" "$3" >/dev/null 2>&1 &
  fi
  PIDS+=("$!")
}

# Foreground mode: stop every tunnel when the user presses Ctrl+C or the script exits.
[[ "$MODE" == --background ]] || trap 'kill "${PIDS[@]}" 2>/dev/null || true' EXIT INT TERM

# shellcheck disable=SC2086  # the variables intentionally hold "<service> <ports>"
forward monitoring $GRAFANA
# shellcheck disable=SC2086
forward monitoring $PROMETHEUS
# shellcheck disable=SC2086
forward monitoring $ALERTMANAGER
forward application service/sre-metrics-app 5000:5000
# Jaeger exists only in the default install (the Helm demo has no tracing).
JAEGER_LINE=""
if kubectl get service jaeger -n opentelemetry >/dev/null 2>&1; then
  forward opentelemetry service/jaeger 16686:16686
  JAEGER_LINE="  Jaeger        http://localhost:16686"
fi
# The Grafana MCP server for AI assistants exists only after scripts/ai_setup.py has run.
MCP_LINE=""
if kubectl get service mcp-grafana -n monitoring >/dev/null 2>&1; then
  forward monitoring service/mcp-grafana 8000:8000
  MCP_LINE="  MCP (AI)      http://localhost:8000/mcp  (IBM Bob and Claude Code, see docs/AI-SRE.md)"
fi
sleep 3

password="$(kubectl get secret grafana-admin-credentials -n monitoring \
  -o jsonpath='{.data.admin-password}' 2>/dev/null | base64 --decode 2>/dev/null || true)"
note="see k8s/grafana-secret.yaml"
if [[ "$password" == "admin" ]]; then
  note="admin"
elif [[ -n "$password" ]]; then
  for copy in pbcopy clip.exe wl-copy "xclip -selection clipboard"; do
    if command -v "${copy%% *}" >/dev/null 2>&1; then
      # shellcheck disable=SC2086
      printf '%s' "$password" | $copy && note="copied to your clipboard: paste it with Cmd+V or Ctrl+V" && break
    fi
  done
  [[ "$note" == see* ]] && note="print it yourself with: kubectl get secret grafana-admin-credentials -n monitoring \
-o jsonpath='{.data.admin-password}' | base64 --decode"
fi

cat <<EOF

  Grafana       http://localhost:3000   (user: admin, password ${note})
  Prometheus    http://localhost:9090
  Alertmanager  http://localhost:9093
  The app       http://localhost:5000
${JAEGER_LINE}
${MCP_LINE}

EOF

# Open Grafana in the default browser (macOS: open; WSL2: the Windows browser; Linux desktop: xdg-open).
# Do not test for `open` alone: on Ubuntu/WSL it is an alias of openvt and fails silently.
if [[ "$(uname -s)" == Darwin ]]; then
  open "http://localhost:3000" || true
elif command -v explorer.exe >/dev/null 2>&1; then
  explorer.exe "http://localhost:3000" || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://localhost:3000" >/dev/null 2>&1 || true
fi

if [[ "$MODE" == --background ]]; then
  mkdir -p .lab
  printf '%s\n' "${PIDS[@]}" > "$PID_FILE"
  echo "The tunnels run in the background. Close them with: ./scripts/dashboards.sh --stop"
  exit 0
fi
echo "Keep this window open while you use them. Press Ctrl+C to close the tunnels."
wait
