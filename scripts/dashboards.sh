#!/usr/bin/env bash
# Opens Grafana, Prometheus, Alertmanager and the app in your browser with one command.
# Works on macOS and Windows (WSL2 + Ubuntu). Keep this window open; press Ctrl+C to close the tunnels.
set -euo pipefail
cd "$(dirname "$0")/.."

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

# Stop every tunnel when the user presses Ctrl+C or the script exits.
trap 'kill $(jobs -p) 2>/dev/null || true' EXIT INT TERM

# shellcheck disable=SC2086  # the variables intentionally hold "<service> <ports>"
kubectl port-forward -n monitoring $GRAFANA >/dev/null 2>&1 &
# shellcheck disable=SC2086
kubectl port-forward -n monitoring $PROMETHEUS >/dev/null 2>&1 &
# shellcheck disable=SC2086
kubectl port-forward -n monitoring $ALERTMANAGER >/dev/null 2>&1 &
kubectl port-forward -n application service/sre-metrics-app 5000:5000 >/dev/null 2>&1 &
sleep 3

password="$(kubectl get secret grafana-admin-credentials -n monitoring \
  -o jsonpath='{.data.admin-password}' 2>/dev/null | base64 --decode 2>/dev/null || true)"

cat <<EOF

  Grafana       http://localhost:3000   (user: admin, password: ${password:-see k8s/grafana-secret.yaml})
  Prometheus    http://localhost:9090
  Alertmanager  http://localhost:9093
  The app       http://localhost:5000

Keep this window open while you use them. Press Ctrl+C to close the tunnels.
EOF

# Open Grafana in the default browser (macOS: open; WSL2: the Windows browser).
if command -v open >/dev/null 2>&1; then
  open "http://localhost:3000" || true
elif command -v explorer.exe >/dev/null 2>&1; then
  explorer.exe "http://localhost:3000" || true
fi

wait
