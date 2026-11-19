# Contributing

Thanks for helping improve this project. Keep changes small, documented and reproducible on Minikube.

## Development setup

You need Python 3.10 or newer (CI uses 3.12) and Docker. On Windows type `python`, never `python3` (on Windows `python3` opens the Microsoft Store).

Mac and Linux:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
```

Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```
If PowerShell refuses to run `Activate.ps1` (common on managed laptops), skip it and call the venv directly: `.venv\Scripts\python -m pip install -r requirements-dev.txt`, `.venv\Scripts\python -m pytest tests -q`, and so on.

## Checks to run before a pull request

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs these jobs on every push to `main` and on every pull request. The table says how to run each one on your laptop. The commands work the same in a bash terminal (Mac, Linux, WSL) and in PowerShell, unless the table says otherwise.

| CI job | What it checks | Run it locally |
| --- | --- | --- |
| `test` | Python style and unit tests | `flake8 app tests scripts .claude/hooks --max-line-length=120` and `pytest tests -q` |
| `security` | bandit (code) and pip-audit (known CVEs in the app dependencies) | `pip install bandit==1.7.10 pip-audit==2.7.3`, then `bandit -r app scripts -ll -ii --skip B104` and `pip-audit -r app/requirements.txt` |
| `validate` | Helm chart, Kustomize render, kubeconform, Prometheus rules and rule unit tests, Prometheus config, Alertmanager config, Grafana dashboards, Collector and Loki configs | See [Validate the configs](#validate-the-configs) below |
| `iac` | `terraform fmt` and `validate`; `ansible-playbook --syntax-check` and `ansible-lint --profile production` | `terraform -chdir=terraform fmt -check -recursive`, then `terraform -chdir=terraform init -backend=false` and `terraform -chdir=terraform validate`. Ansible runs on Mac, Linux or WSL only: `ansible-galaxy collection install -r ansible/requirements.yml`, then `ansible-playbook -i ansible/inventory.ini --syntax-check ansible/site.yml` (and each file in `ansible/runbooks/`) and `ansible-lint --profile production ansible/site.yml ansible/runbooks/*.yml` |
| `docker-build` | The image builds for amd64 and arm64 | `docker build -t sre-metrics-app:dev .` |
| `scripts-linux` / `scripts-macos` | `bash -n` and shellcheck on `scripts/*.sh` | Mac/Linux: `for f in scripts/*.sh; do bash -n "$f"; done`, then `docker run --rm -v "$PWD:/mnt" -w /mnt koalaman/shellcheck:v0.10.0 --severity=warning scripts/*.sh` |
| `scripts-windows` | Every `scripts/*.ps1` parses | PowerShell: `Get-ChildItem scripts -Filter *.ps1 \| ForEach-Object { $e = $null; [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$null, [ref]$e); if ($e) { $_.Name; $e } }` (no output means OK) |

The tool versions are pinned at the top of `ci.yml` (Prometheus 2.54.1, Alertmanager 0.27.0, kubeconform 0.6.7). Use the same versions locally.

### Validate the configs

These need `kubectl`, `helm` and Docker, but no cluster.

Mac and Linux (bash):
```bash
helm lint helm/sre-metrics-app
kubectl kustomize k8s > /dev/null        # renders the whole stack
# Prometheus rules, rule unit tests and config
docker run --rm -v "$PWD:/w" -w /w --entrypoint sh prom/prometheus:v2.54.1 -c \
  'promtool check rules k8s/config/prometheus/alerts.yml k8s/config/prometheus/slo.yml &&
   promtool test rules tests/rules/*.test.yml &&
   promtool check config --syntax-only k8s/config/prometheus/prometheus.yml'
```

Windows (PowerShell):
```powershell
helm lint helm/sre-metrics-app
kubectl kustomize k8s | Out-Null
docker run --rm -v "${PWD}:/w" -w /w --entrypoint sh prom/prometheus:v2.54.1 -c "promtool check rules k8s/config/prometheus/alerts.yml k8s/config/prometheus/slo.yml && promtool test rules tests/rules/*.test.yml && promtool check config --syntax-only k8s/config/prometheus/prometheus.yml"
```

**Alertmanager config.** `amtool` checks that the secret files named in the config exist, so CI creates dummy files. To do the same locally, install PyYAML (`pip install pyyaml==6.0.2`, as CI does), take the `alertmanager.yml` key out of the ConfigMap in [`k8s/alertmanager.yaml`](k8s/alertmanager.yaml) into a file, put dummy files in a folder, and mount them where Alertmanager expects them:
```bash
mkdir -p /tmp/am/secrets /tmp/am/awx
for f in slack-webhook-url smtp-auth-password ntfy-url; do echo http://x.invalid/ > /tmp/am/secrets/$f; done
echo x > /tmp/am/awx/token
python3 -c "import yaml; d=[x for x in yaml.safe_load_all(open('k8s/alertmanager.yaml')) if x]; open('/tmp/am/alertmanager.yml','w').write(next(x for x in d if x['kind']=='ConfigMap')['data']['alertmanager.yml'])"
docker run --rm -v /tmp/am/alertmanager.yml:/cfg/am.yml -v /tmp/am/secrets:/etc/alertmanager-secrets \
  -v /tmp/am/awx:/etc/awx --entrypoint amtool prom/alertmanager:v0.27.0 check-config /cfg/am.yml
```
On Windows, run the same steps with `python` and a folder of your own (for example `$env:TEMP\am`) in place of `/tmp/am`. The two `kubeconform` steps and the Collector and Loki checks run only in CI; their commands are in `ci.yml`.

## Workflow

1. Fork the repository and create a focused branch, for example `fix/alert-threshold` or `feat/new-panel`.
2. Make your change. Comment non-obvious code. Alert and SLO rules live in `k8s/config/prometheus/` (`alerts.yml`, `slo.yml`), and dashboards in `k8s/config/grafana/dashboards/`. The Helm path in `helm/values-monitoring.yaml` carries only ServiceDown, HighErrorRate, HighLatency and AlwaysFiringDemoAlert; if you change one of those, mirror it there.
3. **When you change an alert threshold,** update the promtool test in `tests/rules/` and the text that explains it: [`docs/SLO.md`](docs/SLO.md), the runbook in [`docs/runbooks/`](docs/runbooks/) that the alert's `runbook_url` points to, and the [FAQ](docs/FAQ.md) if it quotes the number. CI checks the numbers, not the words, so a reviewer must check the words.
4. Update the README when deployment behavior or prerequisites change.
5. Open a pull request that describes what changed and how you verified it. Wait for CI to pass.

## Commit messages

Use short imperative subjects, for example `Raise HighLatency threshold to 500ms`. If an AI assistant helped with a commit, keep its `Co-Authored-By` trailer, so the history stays honest.

## Security

Do not commit credentials, Slack webhooks, SMTP passwords, ntfy topic URLs, kubeconfig files, generated artifacts or screenshots with personal information. Real Secrets live in the gitignored `k8s/alertmanager-secret.yaml` and `k8s/grafana-secret.yaml`. Only `*.example.yaml` files are tracked. Never put IBM, client or personal data in the lab.

## Reporting issues

Open a GitHub issue with the steps to reproduce, the expected and actual behavior, and the output of `kubectl get pods -A`.
