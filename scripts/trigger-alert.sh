#!/usr/bin/env bash
# Alert drill: sends failing requests to /error and waits until the HighErrorRate alert fires.
# Works on macOS and Windows (WSL2 + Ubuntu). HighErrorRate fires after about 3 minutes; the error
# budget page ErrorBudgetFastBurn follows a few minutes later (about 6-10 minutes after the start).
set -euo pipefail

if kubectl get service kube-prometheus-stack-alertmanager -n monitoring >/dev/null 2>&1; then
  AM_SERVICE="kube-prometheus-stack-alertmanager"
else
  AM_SERVICE="alertmanager"
fi
ALERTS_URL="/api/v1/namespaces/monitoring/services/${AM_SERVICE}:9093/proxy/api/v2/alerts"

# A short-lived pod inside the cluster calls /error 3,000 times (about 12-14 minutes), then stops by itself.
cd "$(dirname "$0")/.."
kubectl delete pod errload -n application --ignore-not-found >/dev/null
kubectl apply -f k8s/drills/errload-pod.yaml >/dev/null
echo "Drill started: the errload pod sends failing requests to the app for about 12-14 minutes."
echo "Waiting for the HighErrorRate alert. It needs about 3 minutes (5-minute window, then 2 minutes of 'for')..."

for i in $(seq 1 48); do
  if kubectl get --raw "$ALERTS_URL" 2>/dev/null | grep -q '"alertname":"HighErrorRate"'; then
    echo "HighErrorRate is FIRING after about $((i * 10)) seconds."
    echo "See it in Alertmanager (http://localhost:9093) and in Grafana's Error rate panel."
    echo "If Slack/email are configured, a notification is on its way."
    echo ""
    echo "Keep watching: the error budget page ErrorBudgetFastBurn fires later, about 6-10 minutes after"
    echo "the start. It waits until the 1-hour error ratio is above 14.4% (burn rate 14.4x with a 99% SLO)."
    echo "Refresh Alertmanager and the 'SLO and Error Budget' dashboard. The drill pod stops by itself."
    exit 0
  fi
  sleep 10
done

echo "HighErrorRate has not fired after 8 minutes. Check 'kubectl get pods -A' and try again." >&2
exit 1
