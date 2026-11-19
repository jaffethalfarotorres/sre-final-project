#!/usr/bin/env bash
# Sends a burst of failing requests to /error and waits until the HighErrorRate alert fires.
# Works on macOS and Windows (WSL2 + Ubuntu). Takes about 3 minutes.
set -euo pipefail

if kubectl get service kube-prometheus-stack-alertmanager -n monitoring >/dev/null 2>&1; then
  AM_SERVICE="kube-prometheus-stack-alertmanager"
else
  AM_SERVICE="alertmanager"
fi
ALERTS_URL="/api/v1/namespaces/monitoring/services/${AM_SERVICE}:9093/proxy/api/v2/alerts"

# A short-lived pod inside the cluster calls /error about 1,000 times (~4 minutes), then stops by itself.
cd "$(dirname "$0")/.."
kubectl delete pod errload -n application --ignore-not-found >/dev/null
kubectl apply -f k8s/drills/errload-pod.yaml >/dev/null
echo "Sending failing requests to the app. The HighErrorRate alert needs about 2-3 minutes to fire..."

for i in $(seq 1 36); do
  if kubectl get --raw "$ALERTS_URL" 2>/dev/null | grep -q '"alertname":"HighErrorRate"'; then
    echo "HighErrorRate is FIRING after about $((i * 10)) seconds."
    echo "See it in Alertmanager (http://localhost:9093) and in Grafana's Error rate panel."
    echo "If Slack/email are configured, a notification is on its way."
    exit 0
  fi
  sleep 10
done

echo "The alert has not fired yet. Check 'kubectl get pods -A' and try again." >&2
exit 1
