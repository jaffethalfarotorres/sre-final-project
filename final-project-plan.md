# SRE Final Project — Validation, Smoke Test & Repository Readiness Plan

## Top-Level Overview
This plan establishes a rigorous evaluation and validation checklist acting as the course instructor/grader using IBM Bob. The objective is to verify that the personal repository (`https://github.com/jaffethalfarotorres/sre-final-project`) meets 100% of the 6 mandatory SRE competency requirements and all 3 bonus opportunities, performs a complete smoke test suite (unit tests, security scans, rule validations, manifest lints), and ensures pristine documentation and GitHub repository readiness for final submission.

---

## Sub-Tasks

### Sub-Task 1: Code Quality, Unit Testing & Static Analysis Smoke Test
- **Intent**: Verify that the application code, lab framework, security scans, and syntax checks pass cleanly without regressions.
- **Expected Outcomes**:
  - `pytest tests -q --cov=app` passes 100% of unit tests.
  - `flake8 app tests scripts .claude/hooks --max-line-length=120` produces 0 lint errors.
  - `bandit` and `pip-audit` pass security criteria without high/critical vulnerabilities.
- **Todo List**:
  1. [ ] Run unit test suite covering app endpoints, metric increments, distributed trace generation, and structured JSON logging.
  2. [ ] Validate code style and linting standards across Python modules.
  3. [ ] Run security static analysis (`bandit`) on Python source code.
- **Relevant Context**: [`app/app.py`](app/app.py), [`tests/test_app.py`](tests/test_app.py), [`tests/test_lab.py`](tests/test_lab.py), [`requirements-dev.txt`](requirements-dev.txt).
- **Status**: [ ] pending

---

### Sub-Task 2: Kubernetes Manifests & Monitoring Configuration Validation
- **Intent**: Validate that all declarative Kubernetes, Prometheus, Alertmanager, and Grafana configurations are syntactically valid and compliant with SRE production standards.
- **Expected Outcomes**:
  - `kubectl kustomize k8s` renders clean YAML without errors.
  - Prometheus alert rules (`alerts.yml`) and SLO recording rules (`slo.yml`) pass unit testing with `promtool`.
  - Alertmanager routing configuration (`alertmanager.yaml`) is validated with `amtool`.
  - All 4 Grafana JSON dashboards (`sre-metrics.json`, `golden-signals.json`, `slo.json`, `llm-observability.json`) have valid JSON structure and unique UIDs.
- **Todo List**:
  1. [ ] Verify Kustomize manifests for namespace separation (`application`, `monitoring`, `opentelemetry`), 2-replica Deployment, resource limits, security context, and probes.
  2. [ ] Execute Prometheus rule unit tests in `tests/rules/` (`alerts.test.yml`, `slo.test.yml`).
  3. [ ] Verify Alertmanager routing tree, inhibition rules, and receiver configurations.
  4. [ ] Validate Grafana dashboard JSON models and datasource bindings.
- **Relevant Context**: [`k8s/application.yaml`](k8s/application.yaml), [`k8s/kustomization.yaml`](k8s/kustomization.yaml), [`k8s/config/prometheus/`](k8s/config/prometheus/), [`k8s/alertmanager.yaml`](k8s/alertmanager.yaml), [`k8s/config/grafana/dashboards/`](k8s/config/grafana/dashboards/).
- **Status**: [ ] pending

---

### Sub-Task 3: Infrastructure as Code (IaC) & Alternative Stacks Verification (Bonus 2)
- **Intent**: Validate that all Infrastructure as Code assets (Terraform, Ansible, Helm) are structured properly, formatted, and pass linting.
- **Expected Outcomes**:
  - Terraform staging configuration passes `terraform fmt -check` and `terraform validate`.
  - Ansible playbooks and runbooks pass syntax check and `ansible-lint`.
  - Helm chart (`helm/sre-metrics-app/`) passes `helm lint` and `helm template`.
- **Todo List**:
  1. [ ] Check Terraform configuration files in `terraform/`.
  2. [ ] Check Ansible playbooks in `ansible/site.yml` and runbooks in `ansible/runbooks/`.
  3. [ ] Check Helm chart definition and values in `helm/`.
- **Relevant Context**: [`terraform/main.tf`](terraform/main.tf), [`ansible/site.yml`](ansible/site.yml), [`helm/sre-metrics-app/Chart.yaml`](helm/sre-metrics-app/Chart.yaml).
- **Status**: [ ] pending

---

### Sub-Task 4: Notification Integrations & External Alert Routing (Bonus 1)
- **Intent**: Verify external alerting configurations (ntfy phone push, Slack, Email, AWX webhook) and incident runbooks.
- **Expected Outcomes**:
  - Alertmanager configuration contains operational routes and inhibition chains for external receivers.
  - Setup script [`scripts/notify_setup.py`](scripts/notify_setup.py) correctly generates secrets for ntfy.
  - Runbooks in [`docs/runbooks/`](docs/runbooks/) map 1-to-1 to all alert annotations.
- **Todo List**:
  1. [ ] Verify ntfy phone push webhook configuration and test script.
  2. [ ] Verify Slack, Email (SMTP), and AWX webhook routing configuration in `k8s/alertmanager.yaml`.
  3. [ ] Verify runbooks (`service-down.md`, `high-error-rate.md`, `high-latency.md`, `error-budget-burn.md`).
- **Relevant Context**: [`k8s/alertmanager.yaml`](k8s/alertmanager.yaml), [`scripts/notify_setup.py`](scripts/notify_setup.py), [`docs/runbooks/`](docs/runbooks/).
- **Status**: [ ] pending

---

### Sub-Task 5: CI/CD Pipeline & Supply Chain Security (Bonus 3)
- **Intent**: Validate continuous integration and deployment workflows in GitHub Actions.
- **Expected Outcomes**:
  - `.github/workflows/ci.yml` (8 jobs) executes comprehensive testing, security scans, manifest validation, IaC checks, and multi-platform script checks.
  - `.github/workflows/cd.yml` (4 jobs) handles container publishing, SBOM generation, Trivy vulnerability scanning, cosign signatures, provenance attestations, and smoke tests.
- **Todo List**:
  1. [ ] Inspect `.github/workflows/ci.yml` and `.github/workflows/cd.yml` workflow triggers, permissions, and job dependencies.
  2. [ ] Ensure GitHub status badges and action links match the student's repository URL.
- **Relevant Context**: [`.github/workflows/ci.yml`](.github/workflows/ci.yml), [`.github/workflows/cd.yml`](.github/workflows/cd.yml).
- **Status**: [ ] pending

---

### Sub-Task 6: Documentation, Rubric Mapping & GitHub Repository Final Review (Req 6)
- **Intent**: Confirm that the repository presents complete, professional documentation suitable for direct instructor evaluation.
- **Expected Outcomes**:
  - `README.md` includes the Rubric Mapping table linking every requirement/bonus to source files and screenshot evidence.
  - `LICENSE.md` (MIT) and `CONTRIBUTING.md` are present and complete.
  - Evidence screenshots in `docs/screenshots/` reflect functional deployments.
  - Git remote is configured to the student's GitHub repo with clean history.
- **Todo List**:
  1. [ ] Audit `README.md` for grader view table completeness and accurate file links.
  2. [ ] Verify `LICENSE.md`, `CONTRIBUTING.md`, `docs/FAQ.md`, `docs/GUIDE.md`, and `docs/SLO.md`.
  3. [ ] Confirm evidence screenshots and drill postmortems in `docs/postmortems/`.
  4. [ ] Validate git tracking and remote setup for final push.
- **Relevant Context**: [`README.md`](README.md), [`LICENSE.md`](LICENSE.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), [`docs/FAQ.md`](docs/FAQ.md), [`docs/screenshots/`](docs/screenshots/).
- **Status**: [ ] pending
