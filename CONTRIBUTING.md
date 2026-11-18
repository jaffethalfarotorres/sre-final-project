# Contributing

Thanks for helping improve this project. Keep changes small, documented and reproducible on Minikube.

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

## Checks to run before a pull request

```bash
flake8 app tests --max-line-length=120
pytest tests -q
helm lint helm/sre-metrics-app
kubectl apply --dry-run=client -f k8s/application.yaml   # needs a running cluster
```

CI runs the same checks plus `kubeconform`, `promtool check rules` and `amtool check-config`.

## Workflow

1. Fork the repository and create a focused branch, for example `fix/alert-threshold` or `feat/new-panel`.
2. Make your change. Comment non-obvious code and keep the raw manifests in [`k8s/`](k8s/) and the Helm values in [`helm/`](helm/) consistent, especially the alert rules.
3. Update the README when deployment behavior or prerequisites change.
4. Open a pull request that describes what changed and how you verified it. Wait for CI to pass.

## Commit messages

Use short imperative subjects, for example `Raise HighLatency threshold to 500ms`.

## Security

Do not commit credentials, Slack webhooks, SMTP passwords, kubeconfig files, generated artifacts or screenshots with personal information. Real Secrets live in the gitignored `k8s/alertmanager-secret.yaml` and `k8s/grafana-secret.yaml`. Only `*.example.yaml` files are tracked.

## Reporting issues

Open a GitHub issue with the steps to reproduce, the expected and actual behavior, and the output of `kubectl get pods -A`.
