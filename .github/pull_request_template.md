## Summary

<!-- What does this change do and why? -->

## Linked issue

Fixes #

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Observability (metrics, logs, traces, dashboards)
- [ ] Alerting or SLO change
- [ ] Infrastructure / deployment (k8s, Helm, Terraform, Ansible, GitOps)
- [ ] CI/CD
- [ ] Documentation
- [ ] Breaking change

## Checklist

- [ ] Tests added or updated, and `pytest tests -q` passes locally
- [ ] `flake8 app tests scripts --max-line-length=120` passes
- [ ] Manifests and chart still render (`kubectl kustomize k8s/`, `helm lint helm/sre-metrics-app`)
- [ ] Runbooks in `docs/runbooks/` updated if alert behavior changed
- [ ] Alert and SLO rules updated and checked with `promtool check rules` if needed
- [ ] No secrets, tokens or webhook URLs committed
- [ ] README / docs updated

## SLO impact

<!-- Does this change any SLI, SLO target, alert threshold or error budget burn? Write "None" if not. -->

## How was this tested?

<!-- Commands run, environment (kind, minikube), results. -->

## Screenshots

<!-- Grafana panels, alerts, traces or UI changes, if relevant. -->
