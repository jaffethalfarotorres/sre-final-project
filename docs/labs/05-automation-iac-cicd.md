# Part 5: Automation, infrastructure as code and CI/CD

This part turns manual work into code. You automate the first minutes of an incident with Ansible and AWX, describe environments with Terraform and Helm, and let GitHub Actions test, build, sign and release every change. Then you measure how well that delivery works (DORA) and prove where your images come from (supply chain security).

> **Road to Junior SRE, camp 5: The Robot Workshop.** Nimbus Store is rebuilt from code, tested on every change, and diagnoses itself. **SRE principle:** eliminate toil: automate repetitive work and keep infrastructure in code. **Skills for your CV:** automation with Ansible, infrastructure as code with Terraform, CI/CD with GitHub Actions, DORA delivery metrics.

| Module | Title | Course mapping |
| --- | --- | --- |
| [M10](#m10-runbook-automation-with-ansible-and-awx) | Runbook automation with Ansible and AWX | ex4.1, ex13, topic6 |
| [M11](#m11-infrastructure-as-code-with-terraform-and-helm) | Infrastructure as code with Terraform and Helm | ex14, ex15 |
| [M09b](03-slos-and-incidents.md#m09b-github-issues-pull-requests-and-projects-for-sre-work) | Join the guild (fork the repo): core mission, do it before M12; the steps are in Part 3 | topic4 |
| [M12](#m12-cicd-with-github-actions) | CI/CD with GitHub Actions | ex3, ex16, topic4 |
| [M16](#m16-dora-metrics) | DORA metrics | New in 2027 |
| [M19](#m19-software-supply-chain-security) | Software supply chain security | New in 2027 |

All commands run from the project folder (`cd ~/sre-final-project`) in **Terminal** (Mac) or the **Ubuntu** window (Windows). If you use Docker Desktop and PowerShell on Windows instead, use `scripts\*.ps1` and `python` where this page says `./scripts/*.sh` and `python3`. The core stack must be running first: [`./scripts/deploy.sh`](../../scripts/deploy.sh) (see [GUIDE.md](../GUIDE.md)).

---

### M10 Runbook automation with Ansible and AWX

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| ex4.1 Ansible IaC, ex13 AWX incident automation, topic6 incident management | 90 min | Ansible: none. AWX: about 2.5 GB extra | Intermediate | Core stack running, alert drill done (`./scripts/trigger-alert.sh`) |

**Learning objectives**

- Run an idempotent Ansible playbook and an incident runbook against Minikube, and read the report it writes.
- Configure AWX so that a critical alert launches a read-only diagnostics job without a human.
- Prove with `kubectl auth can-i` that the automation account can restart the app but cannot delete pods.

**Concepts in 5 minutes**

An on-call engineer does the same things in the first minutes of every incident: list pods, read events, read logs, check alerts. That is toil. A **runbook** written as code does it in seconds and the same way every time, so Time To Resolve (TTR) goes down.

[`ansible/site.yml`](../../ansible/site.yml) deploys the whole stack the declarative way (ex4.1). The two runbooks in [`ansible/runbooks/`](../../ansible/runbooks/) use the `kubernetes.core` collection, version 5.5.0 (pinned in [`ansible/requirements.yml`](../../ansible/requirements.yml)), so they talk to the Kubernetes API directly and run the same on your laptop and inside AWX:

- [`collect-diagnostics.yml`](../../ansible/runbooks/collect-diagnostics.yml) only **reads**: pods, events, the Deployment, the last 30 log lines per pod and the firing alerts. It writes `reports/incident-<timestamp>.md`.
- [`restart-app.yml`](../../ansible/runbooks/restart-app.yml) **changes** something: a rolling restart of the app Deployment.

**AWX** is the web UI and API for Ansible. In [`k8s/alertmanager.yaml`](../../k8s/alertmanager.yaml), every `severity = "critical"` alert also calls the AWX API and launches `collect-diagnostics`. The restart is never automatic. A person reads the report and decides. This is the rule for safe automation: **automate reading, keep a human on changing**.

The AWX account follows least privilege. [`awx/rbac.yaml`](../../awx/rbac.yaml) gives the `awx-runbooks` ServiceAccount read access in the `application` namespace and `patch` on one object only, the `sre-metrics-app` Deployment.

**Lab steps**

1. Install Ansible in a Python virtual environment (same commands on Mac and Ubuntu; on Ubuntu run `sudo apt-get install -y python3-venv` first if `venv` is missing).

   Check `python3 --version` first. ansible-core 2.17 needs Python 3.10 to 3.12. If it shows 3.9 (the macOS built-in from the Command Line Tools) or 3.13 or newer, create the environment with Python 3.12 instead: `brew install python@3.12`, then use `python3.12 -m venv ~/.venvs/sre-lab` in place of the first line below. If you already made a venv with the wrong version, delete it first with `rm -rf ~/.venvs/sre-lab`.
   ```bash
   python3 -m venv ~/.venvs/sre-lab
   source ~/.venvs/sre-lab/bin/activate
   pip install ansible-core==2.17.5 kubernetes
   ansible-galaxy collection install -r ansible/requirements.yml
   ```
   What you should see: `kubernetes.core:5.5.0 was installed successfully`. Run the `source` line again in every new window.

2. Run the deployment playbook (ex4.1). It is safe on a running cluster.
   ```bash
   cd ansible
   ansible-playbook -i inventory.ini site.yml
   cd ..
   ```
   What you should see: a `PLAY RECAP` line with `failed=0` and the message `Done. Run ./scripts/dashboards.sh ...`. Run it a second time: most tasks now say `ok` instead of `changed`. That is idempotency. (The image build always reports `changed`.)

3. Run the diagnostics runbook from your laptop. The extra `-e` tells Ansible to use the Python from your virtual environment, where the `kubernetes` library lives.
   ```bash
   ansible-playbook -i ansible/inventory.ini ansible/runbooks/collect-diagnostics.yml -e ansible_python_interpreter="$(command -v python3)"
   ls reports/
   ```
   What you should see: `Diagnostics saved to .../reports/incident-<timestamp>.md`. Open the file. It has sections for Firing alerts, Deployment, Pods, Recent warning events and Recent logs. Under Firing alerts it says `Alertmanager not reachable from here`: the runbook uses the in-cluster address, which only works inside AWX. That is expected.

4. Install AWX. First free memory: delete any other add-on (ArgoCD, chaos, Kyverno, Rollouts). This takes about 10 minutes the first time.
   ```bash
   python3 scripts/awx_setup.py
   ```
   What you should see: `Job template collect-diagnostics (id ...)`, `Job template restart-app (id ...)`, `Alertmanager can now launch collect-diagnostics ...` and finally `Test job <n>: successful`. Read [`scripts/awx_setup.py`](../../scripts/awx_setup.py) while you wait: it applies [`awx/`](../../awx/kustomization.yaml) (AWX Operator 2.19.1), then creates a project from this GitHub repository, an inventory, the Kubernetes credential and the two job templates.

5. Look at the image redirect in [`awx/kustomization.yaml`](../../awx/kustomization.yaml).
   ```bash
   grep -n -B3 -A3 "kube-rbac-proxy" awx/kustomization.yaml
   ```
   What you should see: `gcr.io/kubebuilder/kube-rbac-proxy` redirected to `quay.io/brancz/kube-rbac-proxy:v0.15.0`. The operator manifests point at an image that was removed from gcr.io. Without this redirect the operator pod never starts. You will use this example again in M19.

6. Check least privilege. Ask Kubernetes what the AWX account may do.
   ```bash
   kubectl auth can-i patch deployment/sre-metrics-app -n application --as=system:serviceaccount:awx:awx-runbooks
   kubectl auth can-i delete pods -n application --as=system:serviceaccount:awx:awx-runbooks
   kubectl auth can-i get pods -n monitoring --as=system:serviceaccount:awx:awx-runbooks
   ```
   What you should see: `yes`, then `no`, then `no`.

7. Open AWX. Keep this window open.
   ```bash
   kubectl get secret awx-admin-password -n awx -o jsonpath='{.data.password}' | base64 --decode; echo
   kubectl port-forward -n awx service/awx-service 8052:80
   ```
   What you should see: the password, then `Forwarding from 127.0.0.1:8052`. Log in at <http://localhost:8052> as `admin`. Under **Templates** you see `collect-diagnostics` and `restart-app`.

8. Fire a critical alert in a second window and watch AWX **Jobs**.
   ```bash
   ./scripts/trigger-alert.sh
   ```
   What you should see: `HighErrorRate is FIRING after about 150 seconds` (140 to 150 s is normal). About 14 seconds after the alert fires, a new `collect-diagnostics` job appears in AWX, started by Alertmanager, not by you. Open it: the report is printed in the job output and lists `HighErrorRate (critical)` under Firing alerts.

9. Be the human approver. Read the report. If a restart is justified, open **Templates > restart-app > Launch**.
   What you should see: the job ends `Successful` with `sre-metrics-app restarted: 2 of 2 pods ready.` `kubectl get pods -n application` shows new pod names.

**Self-check**

1. Why is `collect-diagnostics` launched automatically but `restart-app` is not?
2. Which file decides that a critical alert calls AWX, and what does `continue: true` do there?
3. What can the `awx-runbooks` ServiceAccount change, and where?
4. Why do the runbooks use `kubernetes.core` modules instead of calling `kubectl`?
5. What lesson does the `kube-rbac-proxy` redirect teach?

<details><summary>Answers (instructors)</summary>

1. Reading is safe to repeat and cannot make the outage worse. A restart changes production, so a person approves it after reading the evidence.
2. The `severity = "critical"` route in `k8s/alertmanager.yaml` sends to the `awx-collect-diagnostics` webhook receiver. `continue: true` makes Alertmanager also evaluate the next route, so Slack and email still get the alert.
3. Only `patch` on the Deployment named `sre-metrics-app` in the `application` namespace. Everything else is read-only (pods, logs, events, deployments) and only in that namespace.
4. The AWX job runs in a temporary execution environment container without `kubectl`. The modules use the Kubernetes API and the AWX credential, so the same playbook runs on a laptop and in AWX.
5. A pinned image tag does not guarantee the image still exists. Teams mirror the images they depend on, or redirect to a trusted copy, and document why.

</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| `Failed to import the required Python library (kubernetes)` | Activate the virtual environment and keep `-e ansible_python_interpreter="$(command -v python3)"` on the command. |
| AWX pods stay `Pending`, or the whole cluster feels slow, while `kubectl describe node` shows free memory | Course TROUBLESHOOTING Pattern G: the Docker driver's real limit is lower. Delete the other add-ons. If still short, give Colima/WSL more memory and recreate Minikube. |
| `awx-operator-controller-manager` never becomes ready, `ImagePullBackOff` on `kube-rbac-proxy` | The gcr.io image was removed. Use the repo's [`awx/kustomization.yaml`](../../awx/kustomization.yaml), which redirects it to quay.io. |
| Alert fires but no AWX job appears | Check `kubectl logs deployment/alertmanager -n monitoring --tail=30`. Without AWX the webhook just fails and is logged. Re-run `python3 scripts/awx_setup.py` to rewrite the `awx-webhook-token` Secret and restart Alertmanager. |
| Webhook error `connection refused` | Pattern F: run `kubectl get endpoints awx-service -n awx`. `<none>` means the Service matches no pod yet; wait until `awx-web` is ready. |
| A job says `Successful` but did nothing | The course warning from ex13: check that the `minikube` inventory has one host (`localhost`) in the AWX UI. |

**Instructor notes**

- Start `awx_setup.py` at the beginning of the session. Teach steps 1 to 3 and 6 while it installs.
- Demo live: step 8 with AWX **Jobs** and Alertmanager side by side. The moment the job appears "by itself" is the key moment of the module.
- Discussion: which other runbooks are safe to automate? Which must stay human-approved? Link to [INCIDENT-RESPONSE.md](../INCIDENT-RESPONSE.md).
- Grading idea: students write a third read-only runbook (for example, collect Prometheus targets) and add it as a job template by hand.
- Evidence to submit: one `reports/incident-<timestamp>.md` file, the three `kubectl auth can-i` answers, screenshots of the AWX Jobs list (automatic launch) and of the human-launched `restart-app` job.

**Clean up**

```bash
kubectl delete -f awx/awx.yaml
kubectl delete -f awx/rbac.yaml
kubectl delete -k awx
kubectl delete secret awx-webhook-token -n monitoring --ignore-not-found
kubectl rollout restart deployment/alertmanager -n monitoring
```

---

### M11 Infrastructure as code with Terraform and Helm

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| ex14 Helm, ex15 Terraform | 75 min | About 0.3 GB per Terraform environment. The Helm path replaces the core stack | Intermediate | Core stack running (the app image `sre-metrics-app:1.0.0` is built inside Minikube) |

**Learning objectives**

- Create, inspect and destroy a staging environment with `terraform plan`, `apply` and `destroy`.
- Explain how Terraform workspaces map to namespaces and why the state file is never committed.
- Deploy the stack with Helm, then upgrade and roll back a release.

**Concepts in 5 minutes**

Infrastructure as code (IaC) means the environment is described in files, reviewed like code and rebuilt the same way every time. Two tools, two jobs:

- **Terraform** compares the desired state (the `.tf` files) with what exists and shows a **plan** before it changes anything. [`terraform/main.tf`](../../terraform/main.tf) creates 4 resources: a namespace, a ConfigMap, a Deployment with probes and a RollingUpdate strategy, and a Service. Each **workspace** gets its own namespace: the `default` workspace becomes `sre-metrics-app-staging`, a workspace called `dev` becomes `sre-metrics-app-dev`.
- Terraform remembers what it created in a **state file** (`terraform/terraform.tfstate`). The state can contain secrets and must match reality, so it is gitignored. Never edit it by hand. Teams keep it in a remote backend with locking. The provider lock file (`.terraform.lock.hcl`) is committed so everyone uses the same provider version.
- **Helm** packages Kubernetes manifests as a versioned **chart** with values. [`helm/sre-metrics-app`](../../helm/sre-metrics-app/) is our app chart. [`helm/values-monitoring.yaml`](../../helm/values-monitoring.yaml) configures the public `kube-prometheus-stack` chart with our alert rules, Alertmanager and Grafana. Every `helm upgrade` is a numbered revision you can roll back to.

**Lab steps**

1. Install Terraform (one time).
   ```bash
   # Mac
   brew tap hashicorp/tap && brew install hashicorp/tap/terraform
   # Ubuntu (Windows)
   wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor --yes -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
   echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
   sudo apt-get update && sudo apt-get install -y terraform
   ```
   What you should see: `terraform version` prints 1.5 or newer.

2. Initialize and plan.
   ```bash
   cd terraform
   terraform init
   terraform plan
   ```
   What you should see: `Plan: 4 to add, 0 to change, 0 to destroy.` Nothing is created yet.

3. Apply, then plan again.
   ```bash
   terraform apply
   terraform plan
   ```
   What you should see: type `yes`, then `Apply complete! Resources: 4 added`. The outputs show `namespace = "sre-metrics-app-staging"`. The second plan says `No changes. Your infrastructure matches the configuration.`

4. Create drift and let Terraform find it.
   ```bash
   kubectl scale deployment sre-metrics-app -n sre-metrics-app-staging --replicas=3
   terraform plan
   ```
   What you should see: `1 to change`, with `replicas` going from 3 back to 2. Someone changed the cluster by hand; the code is the source of truth. Run `terraform apply` to fix it.

5. Look at the state, the right way.
   ```bash
   terraform state list
   git check-ignore -v terraform.tfstate
   ```
   What you should see: four addresses (`kubernetes_config_map_v1.app`, `kubernetes_deployment_v1.app`, `kubernetes_namespace_v1.app`, `kubernetes_service_v1.app`) and the `.gitignore` rule that keeps the state out of Git.

6. A second environment with a workspace.
   ```bash
   terraform workspace new dev
   terraform apply
   kubectl get pods -n sre-metrics-app-dev
   terraform destroy
   terraform workspace select default
   terraform workspace delete dev
   ```
   What you should see: a new namespace `sre-metrics-app-dev` with 2 pods, then `Destroy complete! Resources: 4 destroyed.` Doing the optional portfolio project [P-ENV](#portfolio-project-p-env-a-second-environment-from-code)? Run its check right after `terraform apply`, before you destroy and delete the `dev` workspace.

7. Destroy staging and go back to the project folder.
   ```bash
   terraform destroy
   cd ..
   ```
   What you should see: `Destroy complete! Resources: 4 destroyed.`

8. Read and lint the Helm chart.
   ```bash
   helm lint helm/sre-metrics-app
   helm template sre helm/sre-metrics-app --namespace application | grep "^kind:"
   ```
   What you should see: `1 chart(s) linted, 0 chart(s) failed` and the kinds the chart renders (Service, Deployment, ServiceMonitor and others).

9. Switch the cluster to the Helm version of the stack. Helm cannot adopt objects that `kubectl apply` created, so remove the raw stack first.
   ```bash
   kubectl delete namespace application monitoring opentelemetry
   ./scripts/deploy.sh --helm
   helm list -A
   ```
   What you should see: `Helm deployment complete.` and two releases, `kube-prometheus-stack` in `monitoring` and `sre-metrics-app` in `application`, both `deployed`. `./scripts/dashboards.sh` detects the Helm Service names by itself.

10. Upgrade and roll back a release.
    ```bash
    helm upgrade sre-metrics-app helm/sre-metrics-app -n application --set replicaCount=2
    helm history sre-metrics-app -n application
    helm rollback sre-metrics-app 1 -n application
    kubectl get pods -n application
    ```
    What you should see: revision 2 with 2 app pods, then revision 3 (`Rollback to 1`) with 1 app pod again.

**Self-check**

1. What does `terraform plan` protect you from?
2. Which namespace does the workspace `qa` use, and why?
3. Why is `terraform.tfstate` gitignored but `.terraform.lock.hcl` committed?
4. Why did step 9 delete the namespaces before `deploy.sh --helm`?
5. What is the difference between a Helm chart version and a release revision?

<details><summary>Answers (instructors)</summary>

1. From surprises. It shows exactly what will be added, changed or destroyed before anything happens, so a reviewer can stop a bad change.
2. `sre-metrics-app-qa`. `main.tf` sets `environment` to the workspace name (or `staging` for `default`) and builds the namespace from it.
3. State can hold secrets and changes on every apply; committing it causes conflicts and leaks. The lock file pins provider versions so every machine and CI resolve the same provider.
4. Helm refuses to manage objects it did not create (`invalid ownership metadata`, course Pattern H). Two monitoring stacks would also not fit in memory.
5. The chart version (in `Chart.yaml`, 0.1.0) identifies the package. A revision is one install, upgrade or rollback of a release in one cluster, counted by Helm.

</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| Terraform pods `ErrImageNeverPull` | `image_pull_policy` is `Never`, so the image must exist in Minikube. Run `./scripts/deploy.sh` (or `minikube image build -t sre-metrics-app:1.0.0 .`) first. |
| Pods `CrashLoopBackOff` with `exec format error` | Pattern A: a public image for the wrong CPU. Use the locally built `sre-metrics-app:1.0.0`. |
| A `sed` edit to `variables.tf` changed more than one value | Pattern I: an unanchored pattern also matched inside `5000`. Edit by hand and check with `terraform plan`. |
| `INSTALLATION FAILED: ... invalid ownership metadata` | Pattern H: delete the objects (or namespaces) created by `kubectl apply`, then install with Helm. |
| `terraform plan -var replicas=8` (or apply) fails with `replicas must be between 1 and 5 on a laptop cluster.` | The `replicas` variable has a validation rule for laptop clusters. Use a value from 1 to 5. |

**Instructor notes**

- Demo live: steps 3 and 4. Drift is the concept students remember.
- Step 9 to 10 takes about 10 minutes because kube-prometheus-stack downloads several images. Start it before the break.
- Grading idea: add a variable (for example a label or a second ConfigMap key), show the plan, apply it, and explain the plan in two sentences.
- Evidence to submit: text output of the first `terraform plan`, the drift plan, `terraform state list`, and `helm history sre-metrics-app -n application`.

**Clean up**

```bash
helm uninstall sre-metrics-app -n application
helm uninstall kube-prometheus-stack -n monitoring
kubectl delete namespace application monitoring
./scripts/deploy.sh
```

The last command returns the cluster to the raw-manifest stack that the other parts use. If Terraform environments are still there, run `terraform -chdir=terraform destroy` for each workspace.

---

### M12 CI/CD with GitHub Actions

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| ex3 Docker Hub push, ex16 GitHub Actions CI/CD, topic4 GitHub fundamentals | 60 min | None (runs on GitHub) | Beginner to intermediate | [M09b](03-slos-and-incidents.md#m09b-github-issues-pull-requests-and-projects-for-sre-work) steps 0 and 1 done (your fork is `origin`, Issues are on, the `incident` label exists, `gh` is logged in); git with a Personal Access Token |

**Learning objectives**

- Trace every job in [`ci.yml`](../../.github/workflows/ci.yml) to the risk it removes.
- Break the build on purpose with a vulnerable dependency and read the failing `pip-audit` report.
- Publish a release with [`cd.yml`](../../.github/workflows/cd.yml) and find the image, the smoke test and the Helm chart it produced.

**Concepts in 5 minutes**

**CI** (continuous integration) checks every push and pull request automatically. **CD** (continuous delivery) builds and publishes a release in the same way every time. For an SRE, a pipeline is a reliability tool: most outages start with a change, and the pipeline catches bad changes before users do.

`ci.yml` runs on every push to `main` and every pull request:

| Job | What it checks |
| --- | --- |
| Lint and unit tests | flake8 and pytest with coverage |
| Security scan (bandit, pip-audit) | Insecure code patterns, and known CVEs in `app/requirements.txt` |
| Validate manifests, Helm chart and configs | `helm lint`, Kustomize + kubeconform, `promtool`, `amtool`, Grafana JSON, OpenTelemetry Collector and Loki configs |
| Terraform and Ansible | `terraform fmt`/`validate`, `ansible-playbook --syntax-check`, `ansible-lint --profile production` |
| Docker build (amd64 + arm64) | The image builds for Intel and Apple Silicon (not pushed) |
| `Shell scripts (bash + shellcheck)`, `Shell scripts on macOS (bash 3.2)`, `PowerShell scripts (parser)` | bash -n + shellcheck on Linux, bash 3.2 on macOS, PowerShell parser on Windows |

The security job found real problems: the course pinned Flask 3.0.3 and OpenTelemetry 1.27.0, and `pip-audit` reported known CVEs in both. The app was upgraded to Flask 3.1.3 and OpenTelemetry 1.45.2 (see [`app/requirements.txt`](../../app/requirements.txt)). Dependabot ([`.github/dependabot.yml`](../../.github/dependabot.yml)) proposes such upgrades every week.

`cd.yml` runs on a version tag (`v1.0.0`) or by hand. Job **Build and push image** pushes a multi-arch image to GitHub Container Registry (GHCR) with the built-in `GITHUB_TOKEN`, and to Docker Hub only if `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets exist. **Smoke test (docker + kind)** builds the image from the same commit, runs it without an OpenTelemetry endpoint, deploys the Helm chart on a throwaway kind cluster and checks `/`, `/store` and `/metrics`. **Package Helm chart and release** attaches the chart `.tgz` to a GitHub Release.

**Lab steps**

1. Run the same checks locally before you push (inside the virtual environment from M10).
   ```bash
   pip install -r requirements-dev.txt bandit==1.7.10 pip-audit==2.7.3
   flake8 app tests scripts .claude/hooks --max-line-length=120
   pytest tests -q
   bandit -r app scripts -ll -ii --skip B104
   pip-audit -r app/requirements.txt
   ```
   What you should see: no flake8 output, all tests `passed`, bandit `No issues identified.` and pip-audit `No known vulnerabilities found`.

2. See the real CVEs the course versions had.
   ```bash
   printf 'flask==3.0.3\nopentelemetry-api==1.27.0\nopentelemetry-sdk==1.27.0\nopentelemetry-exporter-otlp-proto-grpc==1.27.0\nopentelemetry-instrumentation-flask==0.48b0\n' > /tmp/course-requirements.txt
   pip-audit -r /tmp/course-requirements.txt
   ```
   What you should see: a table of vulnerabilities with IDs and `Fix Versions` (at least the Flask CVEs), and a non-zero exit code. This is exactly what makes the CI job fail.

3. Break CI on purpose in your fork. Create a branch, pin Flask back to 3.0.3 and open a pull request.
   ```bash
   git switch -c test/vulnerable-flask
   sed -i.bak 's/^flask==3.1.3$/flask==3.0.3/' app/requirements.txt && rm app/requirements.txt.bak
   grep -n "^flask" app/requirements.txt
   git commit -am "test: pin a vulnerable Flask version"
   git push -u origin test/vulnerable-flask
   ```
   What you should see: `grep` prints `flask==3.0.3`. Open the pull request against your own fork: `gh pr create --fill` (after M09b step 0, `gh` targets your fork). In the browser, check that **base repository** is `<your-user>/sre-final-project` before you click Create. In **Checks**, `Security scan (bandit, pip-audit)` is red and its job summary lists the Flask vulnerabilities. Close the pull request without merging.

4. Publish a release (GUIDE section 7 shows the browser way).
   ```bash
   git switch main
   git tag v1.0.0
   git push origin v1.0.0
   ```
   What you should see: in **Actions**, the **CD** run has three green jobs. Under **Releases**, `v1.0.0` has `sre-metrics-app-1.0.0.tgz` attached. Under your profile **Packages**, `sre-metrics-app` has the tags `1.0.0`, `1.0`, `sha-<commit>` and `latest`.

**Self-check**

1. Which CI job would catch a typo in a Prometheus alert rule?
2. Why does CI build for `linux/arm64` as well?
3. Why does the CD smoke test run the container without `OTEL_EXPORTER_OTLP_ENDPOINT`?
4. Docker Hub secrets are not set. Does CD fail?

<details><summary>Answers (instructors)</summary>

1. Validate manifests, Helm chart and configs (`promtool check rules`).
2. Students on Apple Silicon Macs need an arm64 image; without it they get `exec format error` (course Pattern A).
3. Tracing is optional. The app must still serve traffic and metrics when no OpenTelemetry Collector exists.
4. No. The image is pushed to GHCR only; the Docker Hub login step is skipped.

</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| `git push` rejected although the password is right | Pattern K: GitHub needs a Personal Access Token with `repo` and `workflow` scopes, not your password. |
| `Author identity unknown` on the first commit | Pattern J: run `git config --global user.name` and `user.email` once. |
| `externally-managed-environment` from `pip install` | Use the virtual environment from M10 step 1. |
| `${{ github... }}` text was mangled when you wrote a workflow from the shell | Pattern M: use a quoted heredoc (`cat <<'EOF'`). |
| CI does not run in your fork | Open the **Actions** tab once and enable workflows for the fork. |

**Instructor notes**

- Demo live: step 3. A red pull request with a real CVE is more convincing than any slide.
- Walk through `ci.yml` job by job and ask "what outage does this prevent?" for each.
- Grading idea: students propose one new check for `ci.yml` and justify it. Ask why `terraform plan` is not in CI (it needs a live cluster; `validate` does not).
- Evidence to submit: link to the red pull request, link to the green CD run, screenshot of the Release with the chart attached.

**Clean up**

```bash
git push origin --delete test/vulnerable-flask
git branch -D test/vulnerable-flask
```

---

### M16 DORA metrics

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| New in 2027 (builds on topic1 TTD/TTA/TTR and topic6) | 30 min | None | Beginner | [M09b](03-slos-and-incidents.md#m09b-github-issues-pull-requests-and-projects-for-sre-work) steps 0 and 1 done (your fork is `origin`, Issues are on, the `incident` label exists); M12 done in your fork (at least one CD run) |

**Learning objectives**

- Define the five DORA metrics and sort them into throughput and instability.
- Calculate them for your own repository with [`scripts/dora_metrics.py`](../../scripts/dora_metrics.py).
- Change one input (an incident issue, a patch release) and predict the effect on the numbers.

**Concepts in 5 minutes**

DORA (DevOps Research and Assessment) measures software delivery with five metrics. Fast teams can also be stable teams; these numbers show both sides.

| Group | Metric | How the script measures it |
| --- | --- | --- |
| Throughput | Deployment frequency | Successful `cd.yml` runs per week |
| Throughput | Change lead time | Commit time to finished deployment of that commit (median) |
| Throughput | Failed deployment recovery time | Issue labeled `incident`: opened to closed (median) |
| Instability | Change fail rate | Deployments followed by an `incident` issue within 24 h |
| Instability | Deployment rework rate | Unplanned fix deployments: patch tag (`v1.0.1`) or a release within 24 h of the previous one |

The script uses only the GitHub API and the Python standard library. The heuristics are simple on purpose, so you can read and question them.

**Lab steps**

1. Run it for your fork (it reads `git remote origin` by default).
   ```bash
   python3 scripts/dora_metrics.py --days 90
   ```
   What you should see: `DORA metrics for <owner>/sre-final-project, last 90 days` and a five-row Markdown table. With one CD run, deployment frequency is about `0.08 per week`. If no issue has the `incident` label, the script says so.

2. Record an incident. On GitHub open **Issues > New issue > Incident follow-up** (form in [`.github/ISSUE_TEMPLATE/incident.yml`](../../.github/ISSUE_TEMPLATE/incident.yml), which adds the `incident` label). Describe the M10 alert drill. Close it when the postmortem is done ([POSTMORTEM-TEMPLATE.md](../POSTMORTEM-TEMPLATE.md)).

3. Ship a fix release and measure again.
   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   python3 scripts/dora_metrics.py --days 90
   ```
   What you should see (after the CD run is green): two deployments, a rework rate above 0% (`v1.0.1` is a patch), and a value for failed deployment recovery time if the incident is closed. Change fail rate is above 0% if your incident issue was opened within 24 h after a deployment finished.

**Self-check**

1. Which two metrics would rise if you released a hotfix one hour after a release?
2. Why are change fail rate and recovery time based on issues, not on CI failures?
3. Name one way this script could be gamed, and how a team would notice.

<details><summary>Answers (instructors)</summary>

1. Deployment frequency and deployment rework rate (within 24 h and, with a `.1` tag, a patch).
2. A failed CI run never reached users. DORA counts changes that caused a problem in production, and the incident issue is our record of that.
3. Example: never labeling issues `incident` keeps change fail rate at 0%. Compare with the alert history in Alertmanager or Grafana; metrics are for learning, not for targets.

</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| `HTTP Error 403: rate limit exceeded` | Without a token GitHub allows 60 API calls per hour. Set `GITHUB_TOKEN` (for example `export GITHUB_TOKEN=$(gh auth token)`, which needs `gh` from M09b; otherwise create a fine-grained token with read-only access in GitHub **Settings > Developer settings** and export it; never commit it) and run again. |
| `Give the repository as owner/repo.` | You are not in a git clone with a GitHub `origin`. Pass it: `python3 scripts/dora_metrics.py <owner>/sre-final-project`. |
| `No successful CD runs yet` | Publish a release first (M12 step 4). |
| Incident issue not counted | The `incident` label did not exist when the issue was opened. Create it (M09b step 1) and add it to the issue. |

**Instructor notes**

- Run the script for the class repository on the projector and discuss what each number would look like in a real team.
- Grading idea: students write three sentences interpreting their own table and propose one change that would improve lead time.
- Evidence to submit: the two Markdown tables (before and after step 3) and the link to the incident issue.

**Clean up**

No cluster add-ons. Keep the tags: they are your deployment history.

---

### M19 Software supply chain security

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| New in 2027 (extends ex3 and ex16) | 45 min | None | Intermediate | M12 step 4 done in your fork (a `v1.0.0` CD run; your fork is `origin` after [M09b](03-slos-and-incidents.md#m09b-github-issues-pull-requests-and-projects-for-sre-work) step 0); `cosign` and `gh` 2.49 or newer installed |

**Learning objectives**

- Explain what an SBOM, a vulnerability gate, a keyless signature and build provenance each prove.
- Verify the signature, the SBOM attestation and the SLSA provenance of your own image.
- Show that verification fails for an image signed by a different identity.

**Concepts in 5 minutes**

You run code you did not write: base images, Python packages, actions. Supply chain security answers two questions: **what is inside this image**, and **who built it, from which source**. The `publish` job in [`cd.yml`](../../.github/workflows/cd.yml) adds four steps after the push:

1. **SBOM** (software bill of materials) with Syft: a list of every package in the image, in SPDX JSON.
2. **Trivy gate**: the job fails on a fixable CRITICAL vulnerability. The image is already pushed at this point, but it is never signed, so a cluster that only admits signed images will not run it.
3. **cosign keyless signing**: no private key to lose. GitHub gives the job a short-lived OIDC identity, Sigstore issues a certificate for it, and the signature and the SBOM attestation are stored next to the image.
4. **SLSA build provenance** with `actions/attest-build-provenance`: a signed record of which repository, workflow and commit built this digest.

Everything is tied to the image **digest** (`sha256:...`), not a tag, because tags can be moved. The AWX case in M10 is the other half of the lesson: `gcr.io/kubebuilder/kube-rbac-proxy` disappeared from its registry. Pinning a tag protects you from nothing if the tag is moved; pinning a digest (or, for actions, a full commit SHA) protects you from changes, but not from removal. Mirror what you depend on.

**Lab steps**

1. Install the tools (one time).
   ```bash
   # Mac
   brew install cosign gh
   # Ubuntu (Windows)
   curl -fsSLo cosign https://github.com/sigstore/cosign/releases/download/v2.4.1/cosign-linux-amd64
   sudo install cosign /usr/local/bin/cosign && rm cosign
   # Ubuntu's own gh package is too old for `gh attestation`; use GitHub's apt repository
   (type -p wget >/dev/null || sudo apt-get install -y wget) && sudo mkdir -p -m 755 /etc/apt/keyrings && wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null && sudo apt-get update && sudo apt-get install -y gh
   gh auth login
   ```
   What you should see: `cosign version` prints a version, and `gh --version` prints 2.49 or newer.

2. Set your image. Copy the digest from the **Summary** of your CD run (`Digest: sha256:...`). Replace the two example values with your own. Write `OWNER` exactly as GitHub shows your user name, with any capitals: the signing identity uses that spelling. The image path must be lowercase, so the third line converts it. If the package is private, make it public in **Packages > sre-metrics-app > Package settings**, or run `docker login ghcr.io` first.
   ```bash
   OWNER=your-github-user
   DIGEST=sha256:paste-the-digest-here
   IMAGE=ghcr.io/$(echo "$OWNER" | tr '[:upper:]' '[:lower:]')/sre-metrics-app@$DIGEST
   ```
   What you should see: no output. `echo $IMAGE` prints the full reference.

3. Verify the signature (the same command the CD summary prints; you can also copy it from there, it already has the right case).
   ```bash
   cosign verify "$IMAGE" \
     --certificate-identity-regexp "https://github.com/$OWNER/sre-final-project/.*" \
     --certificate-oidc-issuer https://token.actions.githubusercontent.com
   ```
   What you should see: `The cosign claims were validated`, `Existence of the claims in the transparency log was verified offline` and `The code-signing certificate was verified using trusted certificate authority certificates`, followed by JSON that names your workflow.

4. Verify the SBOM attestation and the build provenance.
   ```bash
   cosign verify-attestation "$IMAGE" --type spdxjson \
     --certificate-identity-regexp "https://github.com/$OWNER/sre-final-project/.*" \
     --certificate-oidc-issuer https://token.actions.githubusercontent.com > /dev/null
   gh attestation verify "oci://$IMAGE" --owner "$OWNER"
   ```
   What you should see: cosign prints the same three "validated / verified" lines, and `gh` prints `Verification succeeded!` with the workflow that built the image.

5. Prove that verification really checks identity. Pretend the image must come from another repository.
   ```bash
   cosign verify "$IMAGE" \
     --certificate-identity-regexp "https://github.com/someone-else/sre-final-project/.*" \
     --certificate-oidc-issuer https://token.actions.githubusercontent.com
   ```
   What you should see: an error saying no matching signatures were found. A signature alone means nothing; a signature **from the expected identity** does.

6. Run the vulnerability gate yourself (optional).
   ```bash
   docker run --rm aquasec/trivy:0.56.2 image --severity CRITICAL --ignore-unfixed "$IMAGE"
   ```
   What you should see: a table with `Total: 0 (CRITICAL: 0)`, the same result that let CD sign the image.

**Self-check**

1. Why does `cd.yml` sign `image@sha256:...` and not `image:1.0.0`?
2. What does "keyless" mean, and what replaces the private key?
3. The Trivy step fails after the push. What protects users from that image?
4. What is the difference between the SBOM attestation and the SLSA provenance?
5. How would you protect the lab from another `kube-rbac-proxy` style removal?

<details><summary>Answers (instructors)</summary>

1. A tag can be moved to other content; a digest is the content. Signing the digest means the signature cannot be reused for a different image.
2. No long-lived key is stored. The job's GitHub OIDC token proves its identity, Sigstore's Fulcio issues a short-lived certificate, and the signature is recorded in the Rekor transparency log.
3. The signing steps never run, so the image has no signature or attestations. A deploy policy that requires a valid signature (for example a Kyverno image verification rule, M20) refuses it.
4. The SBOM says what is inside the image. Provenance says how and where it was built (repository, workflow, commit).
5. Mirror critical images into a registry you control, pin by digest, and document redirects as `awx/kustomization.yaml` does.

</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| `cosign verify` fails with `no matching signatures` for your own image | The image path must be lowercase; the identity must match the repository name exactly as GitHub shows it. Check that `OWNER` keeps its capitals, that `IMAGE` was built with the lowercase line from step 2, and that `DIGEST` comes from the same CD run. |
| `gh attestation verify` fails with `unknown command "attestation"` | Your `gh` is older than 2.49 (Ubuntu's own package). Install it from GitHub's apt repository (step 1). |
| `UNAUTHORIZED` or `denied` when reading from ghcr.io | The package is private. Make it public or run `docker login ghcr.io` with a token that has `read:packages`. |
| CD **Build and push image** is red at the Trivy step | A fixable CRITICAL vulnerability is in the image. Read the table in the job log, upgrade the base image or package, and release again. This is the gate working. |
| Operator pod `ImagePullBackOff` on a gcr.io image | The real AWX case from the verified runs: the image was removed. Redirect it to a trusted copy, as in `awx/kustomization.yaml`. |

**Instructor notes**

- Demo live: steps 3 and 5 back to back. The failure in step 5 is the moment students understand signing.
- Explain the order in `cd.yml`: push, SBOM, Trivy, sign, attest. Ask why signing comes after the gate.
- Grading idea: students write a short policy for the team ("we only deploy images that ..."), then compare it with M20 policy as code.
- Discussion: ask students to find the actions in `cd.yml` that are pinned by a tag rather than a commit SHA (for example `aquasecurity/trivy-action@0.28.0`, `anchore/sbom-action@v0`, `sigstore/cosign-installer@v3`) and to explain the risk: whoever controls the action's repository can move the tag to other code, and the next CD run uses it with the job's permissions. Pinning to a full commit SHA closes that gap.
- Evidence to submit: the output of steps 3, 4 and 5, and the CD run Summary page.

**Clean up**

Nothing runs in the cluster. Optional: `unset OWNER DIGEST IMAGE`.

---

### Portfolio project P-ENV: a second environment from code

Optional and open to everyone. It is worth 250 XP. Real teams try a change in a `dev` environment before it reaches users. Here you build one from the same Terraform code, which is a strong example of infrastructure as code for an interview.

**What you build:** a separate `dev` environment, using a Terraform workspace.

1. Do M11 steps 1-3 first, so Terraform is initialized in `terraform/`.
2. Create the workspace and apply:
   ```bash
   cd terraform
   terraform workspace new dev
   terraform apply
   kubectl get pods -n sre-metrics-app-dev
   cd ..
   ```
   What you should see: type `yes`, then `Apply complete!`, and 2 pods in the namespace `sre-metrics-app-dev`.
3. Check it from the project folder while the workspace still exists (Windows: `python scripts\lab.py check P-ENV`):
   ```bash
   python3 scripts/lab.py check P-ENV
   ```
   What you should see: "dev workspace state serial ...".
4. Optional, to go further: explain to Bob, in your own words, how the namespace name comes from the workspace name in `terraform/main.tf`, and what would change for a third workspace called `qa`.
5. Clean up as in M11 step 6 (`terraform destroy`, `terraform workspace select default`, `terraform workspace delete dev`). The mission stays recorded.

**For the interview:** be ready to explain why the same code can create two environments, and why the state file is never committed.

> **Interview corner: The Robot Workshop.** A question you can expect: *"Why should infrastructure be written as code?"* Answer with what you did here: Terraform created Nimbus Store from `.tf` files and found the drift when you scaled the deployment by hand (M11), the GitHub Actions pipeline in your own fork tested and built every change (M09b, M12), and you measured delivery with DORA metrics (M16). In plain words: code can be reviewed, repeated and rolled back; clicks in a console cannot. Rehearse it with Bob: type `/interview`.
