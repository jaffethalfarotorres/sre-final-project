# Operational Readiness Review (ORR)

The ORR checklist from SRE Academy topic 3, applied to `sre-metrics-app`. Each item lists the evidence in this repository and an honest result. Run the review again before a new service goes live, after architecture changes, before scaling, after a major incident, and every quarter.

**Result legend:** ✅ Pass · 🟡 Partial · ❌ Fail. Gap priority follows the course: **Critical** must be fixed before production, **Medium** goes in the next sprint, **Low** is tracked.

## 1. Monitoring and alerting: ✅ Pass
| Check | Evidence |
| --- | --- |
| SLIs and SLOs defined | [`SLO.md`](SLO.md), recording rules in [`slo.yml`](../k8s/config/prometheus/slo.yml) |
| Alerts on critical failures, with severity | [`alerts.yml`](../k8s/config/prometheus/alerts.yml): `ServiceDown`, `HighErrorRate`, `HighLatency`, `SyntheticProbeFailing`; burn-rate alerts; Grafana rules in [`alerting.yaml`](../k8s/config/grafana/alerting.yaml) |
| Alert routing configured | Alertmanager routes critical, warning and demo alerts to Slack and email ([`alertmanager.yaml`](../k8s/alertmanager.yaml)) |
| Dashboards | Grafana: *SRE Metrics Demo*, *Golden Signals*, *SLO and Error Budget*, *LLM Observability* (4 dashboards, provisioned as code in [`k8s/config/grafana/dashboards/`](../k8s/config/grafana/dashboards/)) |
| Synthetic monitoring | Blackbox exporter probes `/` and `/store` ([`blackbox.yaml`](../k8s/blackbox.yaml)) |

## 2. Structured logging and storage: ✅ Pass
| Check | Evidence |
| --- | --- |
| Structured JSON logs | `JsonFormatter` in [`app/app.py`](../app/app.py) writes one JSON object per line |
| Centralized storage | Logs are exported over OTLP to the Collector, then to Loki ([`observability.yaml`](../k8s/observability.yaml)) |
| Retention policy | Loki `retention_period: 72h` ([`loki.yaml`](../k8s/config/loki.yaml)) |
| Trace IDs in logs | Every log line has `trace_id` and `span_id`. Grafana links a log line to its trace (derived field) |

## 3. Distributed tracing: ✅ Pass
| Check | Evidence |
| --- | --- |
| End-to-end tracing | OpenTelemetry Flask instrumentation plus manual spans (`store.load_catalog`, `store.process_order`) |
| Trace context propagated | W3C `traceparent` handled by the OpenTelemetry SDK |
| Visible in a tracing UI | Jaeger, and Grafana's Jaeger datasource with trace-to-logs links |
| Metrics from traces | Collector spanmetrics connector, used on the *Golden Signals* dashboard and in a Grafana alert |

## 4. Runbooks and incident response: ✅ Pass
| Check | Evidence |
| --- | --- |
| Runbook for each alert | [`runbooks/`](runbooks/); each alert has a `runbook_url` annotation |
| Incident process | [`INCIDENT-RESPONSE.md`](INCIDENT-RESPONSE.md): severities, roles, TTD/TTA/TTR |
| Automated runbooks | Ansible [`collect-diagnostics.yml`](../ansible/runbooks/collect-diagnostics.yml) and [`restart-app.yml`](../ansible/runbooks/restart-app.yml). They can run as AWX job templates (see [`awx/README.md`](../awx/README.md)) |
| Drills | `scripts/trigger-alert` (alert path), `scripts/rollout_demo.py` (bad release), `scripts/chaos_test.py` (pod loss) |
| Postmortem template | [`POSTMORTEM-TEMPLATE.md`](POSTMORTEM-TEMPLATE.md) |

## 5. Disaster recovery and failover: 🟡 Partial
| Check | Result | Evidence or gap |
| --- | --- | --- |
| Survives the loss of a pod | ✅ | 2 replicas, readiness probes, `maxUnavailable: 0`, verified by the LitmusChaos pod-delete experiment |
| Bad release recovery | ✅ | Rolling update plus `kubectl rollout undo`, and ArgoCD history/rollback for the GitOps copy |
| Rebuild from scratch (RTO) | ✅ | Whole stack re-created from Git with one command (`scripts/deploy`, `ansible/site.yml`, or Terraform for the app). RTO about 10 minutes |
| Monitoring data backups (RPO) | 🟡 Medium | Prometheus and Loki use `emptyDir`; history is lost when their pods restart. Acceptable for a laptop demo. In production use persistent volumes and remote storage |
| Multi-node / multi-region failover | 🟡 Low | Single-node Minikube by design. In production: several nodes, pod anti-affinity and a PodDisruptionBudget |

## Follow-up items
| Gap | Priority | Next step |
| --- | --- | --- |
| Persistent storage for Prometheus and Loki | Medium | PersistentVolumeClaims plus a retention or remote-write plan |
| Multi-node resilience | Low | PodDisruptionBudget and anti-affinity once more than one node exists |
| Automate this ORR | Low | A CI job that checks every alert has a `runbook_url` (the course suggests GitHub Actions) |
