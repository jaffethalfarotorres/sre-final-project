# Part 6: GitOps, resilience and guardrails

This part is about changing a running system safely. You deploy from Git with ArgoCD, ship a broken release and roll it back, kill pods on purpose to test a hypothesis, block unsafe workloads with policies, and let an SLO decide whether a canary release goes on. Every module uses the core stack from [`../../scripts/deploy.sh`](../../scripts/deploy.sh) plus at most one add-on.

> **Road to Junior SRE, camp 6: The Proving Grounds.** You break things on purpose and prove Nimbus Store survives: GitOps, chaos, canaries and policies. **SRE principle:** release engineering: changes are gradual, reversible and tested by breaking things on purpose. **Skills for your CV:** rollbacks, GitOps with ArgoCD, chaos engineering, canary releases, policy as code (Kyverno).

| Module | Topic | Main files |
| --- | --- | --- |
| [M13](#m13-gitops-with-argocd) | GitOps with ArgoCD | [`gitops/`](../../gitops), [`scripts/gitops_setup.py`](../../scripts/gitops_setup.py) |
| [M14](#m14-rolling-updates-and-rollbacks) | Rolling updates and rollbacks | [`k8s/application.yaml`](../../k8s/application.yaml), [`scripts/rollout_demo.py`](../../scripts/rollout_demo.py) |
| [M15](#m15-chaos-engineering) | Chaos engineering | [`chaos/`](../../chaos), [`scripts/chaos_test.py`](../../scripts/chaos_test.py) |
| [M20](#m20-policy-as-code-with-kyverno) | Policy as code with Kyverno | [`policy/workload-baseline.yaml`](../../policy/workload-baseline.yaml), [`scripts/policy_setup.py`](../../scripts/policy_setup.py) |
| [M21](#m21-progressive-delivery-with-argo-rollouts) | Progressive delivery with Argo Rollouts | [`progressive/rollout.yaml`](../../progressive/rollout.yaml), [`scripts/canary_demo.py`](../../scripts/canary_demo.py) |

**Core path:** only **M14** (30 min, no add-on). M13, M15, M20 and M21 are optional add-ons: do them on a 16 GB laptop, one at a time, or watch the instructor demo. See the [core path](README.md#official-core-path-about-35-hours).

**Before you start (all modules).** Run every command from the project folder (`cd ~/sre-final-project`), in the Mac Terminal or the Ubuntu window on Windows. The core stack must be running (`./scripts/deploy.sh`, see [`../GUIDE.md`](../GUIDE.md)). On Windows with Docker Desktop and PowerShell, use `scripts\*.ps1` where this page says `./scripts/*.sh`, and type `python` instead of `python3`. A few inspection commands (`grep`, jsonpath with `\n`) are written for bash. Run them in the Ubuntu window.

**Memory rule.** The core stack uses about 3.2-3.8 GiB. The add-ons in this part were measured in a 6 GiB Minikube, created as in Part 1, step 4 (run `minikube delete` first if a 4 GB cluster already exists; `minikube start --driver=docker --memory=6144` before `./scripts/deploy.sh`). The deploy script's default is 4096 MB, which is not enough for these add-ons. Run **one add-on at a time** (ArgoCD, chaos tools, Kyverno, Argo Rollouts) and use its **Clean up** section before you start the next module. Before each add-on module, run `kubectl get namespaces` and check that none of `argocd`, `litmus`, `argo`, `kyverno`, `argo-rollouts`, `progressive` or `awx` is left over (except the one for the module you are in).

**Problems that can happen in any module**

| Symptom | Fix |
| --- | --- |
| Pods stay `Pending`, or a sync or rollout stays `Progressing` | Not enough memory. Remove the other add-ons (their Clean up sections) and try again. |
| Pods show `ErrImageNeverPull` (outside the M14 demo) | The image is built inside Minikube by the deploy script. Run `./scripts/deploy.sh` once. |

---

### M13 GitOps with ArgoCD

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| 2026 exercise 17 (and the rollback part of 18) | 45 min | core stack + ArgoCD only | Intermediate | Core stack running; Helm chart from exercise 14; Git basics (topic 4) |

**Learning objectives**
- Install ArgoCD and register an `AppProject` and an `Application` that deploy the Helm chart from Git.
- Demonstrate self-healing by changing the cluster by hand and timing how fast ArgoCD reverts it.
- Compare a rollback by `git revert` with a rollback from the ArgoCD UI, and state which one keeps Git as the source of truth.

**Concepts in 5 minutes**

In GitOps, Git holds the desired state of the cluster. A controller inside the cluster (ArgoCD) keeps comparing Git with what is running. If they differ, the app is **OutOfSync** and ArgoCD fixes it.

- [`gitops/project.yaml`](../../gitops/project.yaml) is an `AppProject` named `sre-project`. It is a fence: only this GitHub repo, only namespaces that match `gitops-*`, and only Deployments, Services, ConfigMaps and Namespaces.
- [`gitops/application.yaml`](../../gitops/application.yaml) is the `Application` `sre-metrics-app-staging`. Its source is the Helm chart in `helm/sre-metrics-app` on branch `main`. The `valuesObject` block sets 2 replicas, image `sre-metrics-app:1.0.0` with `pullPolicy: Never`, and turns off the ServiceMonitor and the traffic generator.
- `syncPolicy.automated` turns on `prune` and `selfHeal` (self-check 1 asks what each one does).

Why this matters for SRE: every change has a commit, an author and a review. A rollback is a `git revert`, so the audit trail and the cluster never disagree. A rollback from the UI is fast, but the cluster then differs from Git until someone fixes Git.

**Lab steps**

1. Install ArgoCD v2.13.2 and register the project and the app.
   ```bash
   python3 scripts/gitops_setup.py
   ```
   What you should see: "Installing ArgoCD v2.13.2 (about 2-3 minutes)...", then `Application sre-metrics-app-staging: sync=Synced, health=Healthy` and two `Running` pods in `gitops-staging`. The script installs with `kubectl apply --server-side --force-conflicts` because the ApplicationSet CRD is too large for a normal apply.

2. Check the Application from the command line.
   ```bash
   kubectl get application -n argocd
   kubectl get deployment -n gitops-staging
   ```
   What you should see: `sre-metrics-app-staging` with `Synced` and `Healthy`, and a Deployment `sre-metrics-app-staging` with `2/2` ready.

3. Open the ArgoCD UI (keep this window open).
   ```bash
   kubectl port-forward -n argocd service/argocd-server 8080:443
   ```
   What you should see: at <https://localhost:8080>, after you accept the self-signed certificate warning, a login page. The user is `admin`. The setup script printed the password. The app card shows a tree: Deployment, ReplicaSet, Pods, Service.

4. Self-heal demo: change the cluster by hand. Use a second window.
   ```bash
   kubectl scale deployment -n gitops-staging --all --replicas=5
   kubectl get deployment -n gitops-staging
   ```
   What you should see: the first `get` may show `5` desired replicas. Run the `get` again after about 5 seconds: it is back to `2/2`. The UI briefly shows OutOfSync, then Synced. (Measured on this project: back to 2 within about 5 s.)

5. Look at the sync history.
   ```bash
   kubectl get application sre-metrics-app-staging -n argocd -o jsonpath='{range .status.history[*]}{.id}{"  "}{.revision}{"  "}{.deployedAt}{"\n"}{end}'
   ```
   What you should see: one line per sync, with the Git commit it deployed.

6. Optional, only if you have your own fork on GitHub: roll back with `git revert`.
   First point both files to your fork: change `repoURL` in `gitops/application.yaml` and `sourceRepos` in `gitops/project.yaml`, then run `python3 scripts/gitops_setup.py` again. Your clone still points at the original repo, so point it at your fork and check it:
   ```bash
   git remote set-url origin https://github.com/<your-user>/sre-final-project.git
   git remote -v
   ```
   Then make a change that `valuesObject` does not override, for example the memory limit in `helm/sre-metrics-app/values.yaml` (`256Mi` to `300Mi`):
   ```bash
   git commit -am "test: raise memory limit"
   git push
   git revert --no-edit HEAD
   git push
   ```
   What you should see: within about 3 minutes (ArgoCD checks Git on a timer, or click **Refresh** in the UI) a new sync with the new limit, and after the revert another sync back to `256Mi`. Both commits are in Git history. (`git commit -am` also commits your edited `gitops/*.yaml` files, which is fine.)

7. Compare with a UI rollback. In the UI open the app, then **History and Rollback**, pick an older entry, **Rollback**.
   What you should see: ArgoCD refuses while automated sync is on. To roll back from the UI you must first turn off auto-sync, and then the app shows OutOfSync because the cluster no longer matches Git. That is the point of the comparison.

**Self-check**
1. What is the difference between `prune` and `selfHeal`?
2. Why does changing `replicaCount` in `helm/sre-metrics-app/values.yaml` not change the number of pods in `gitops-staging`?
3. Which object stops this Application from deploying into the `application` namespace?
4. After a UI rollback, what does Git say about the running version? Why is that a problem during an incident review?

<details><summary>Answers (try first)</summary>

1. `prune` deletes cluster objects that were removed from Git. `selfHeal` reverts manual changes to objects that are still in Git.
2. `valuesObject` in `gitops/application.yaml` sets `replicaCount: 2`, and it wins over the chart's `values.yaml`.
3. The `AppProject` `sre-project`: its `destinations` only allow `gitops-*` namespaces.
4. Git still describes the newer version, so Git and the cluster disagree. Reviewers cannot trust Git as the record of what ran. `git revert` keeps both in step and leaves a commit with author and reason.
</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| Install fails on `applicationsets.argoproj.io` with `metadata.annotations: Too long: may not be more than 262144 bytes` | Use server-side apply (`--server-side --force-conflicts`). [`gitops_setup.py`](../../scripts/gitops_setup.py) already does this; add the flags if you install by hand (course TROUBLESHOOTING Pattern N). |
| Browser blocks `https://localhost:8080` | ArgoCD uses a self-signed certificate. Click **Advanced** and continue. Scripts cannot click this for you (Pattern P). |
| `This site can't be reached` on port 8080 | The port-forward window was closed. Run the port-forward again and keep the window open. |
| `argocd app sync` fails with "another operation is already in progress" | Auto-sync started first. It is a race, not a bug (Pattern T). Check the status again. |

**Instructor notes**
- Demo live: step 4 is the moment that lands. Keep the UI on screen while a student runs the `scale` command.
- Timing: 10 min install, 15 min UI tour and self-heal, 20 min for the revert vs UI comparison and discussion.
- Students without a fork do steps 1-5 and 7, and describe step 6 in writing.
- Grading idea: ask for a short paragraph that names who changed what, and when, for each sync in the history.
- Evidence to submit: screenshot of the app tree in the UI (Synced/Healthy); terminal output of step 4 showing 5 then 2 replicas; output of step 5; (fork only) links to the change commit and the revert commit.

**Clean up**
```bash
kubectl delete -f gitops/application.yaml --wait=true
kubectl delete -f gitops/project.yaml
kubectl delete namespace gitops-staging --ignore-not-found
kubectl delete namespace argocd
```
Delete the Application first. Its finalizer removes the app's resources; if you delete the `argocd` namespace first, the Application can get stuck.

---

### M14 Rolling updates and rollbacks

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| 2026 exercise 18 | 30 min | core stack only (no add-on) | Beginner | Core stack running; exercise 4 (Kubernetes basics) |

**Learning objectives**
- Explain how `maxSurge: 1` and `maxUnavailable: 0` keep the service up during a bad release.
- Use `kubectl rollout history` and `kubectl rollout undo` to recover from a broken image.
- Measure the time from a bad release to recovery (the MTTR of a bad deploy) and the share of health checks that passed.

**Concepts in 5 minutes**

A Deployment replaces pods in steps. [`k8s/application.yaml`](../../k8s/application.yaml) sets:

- `replicas: 2`
- `maxSurge: 1`: start at most one extra pod during an update.
- `maxUnavailable: 0`: never go below 2 ready pods.
- `revisionHistoryLimit: 5`: keep old ReplicaSets so you can roll back.

So a new pod must become **Ready** before an old one is removed. If the new version cannot start, the rollout stops and the old pods keep serving. Users do not notice. The release is still broken, though, and someone must roll it back. How fast that happens is part of your MTTR (topic 1).

The demo uses the tag `sre-metrics-app:broken`, which does not exist. Because the app uses `imagePullPolicy: Never`, the new pod shows `ErrImageNeverPull` (with a normal registry you would see `ImagePullBackOff`).

**Lab steps**

1. Look at the current history.
   ```bash
   kubectl rollout history deployment/sre-metrics-app -n application
   ```
   What you should see: a list of revisions. `CHANGE-CAUSE` may be `<none>` for older ones.

2. Run the demo. It releases the broken image, checks the app 10 times, then rolls back.
   ```bash
   python3 scripts/rollout_demo.py
   ```
   What you should see:
   - Step 1 lists 2 healthy pods.
   - Step 2 lists a third pod with reason `ErrImageNeverPull`, and "During the bad rollout the app answered 10/10 health checks".
   - "The rollout is stuck, as expected".
   - Step 3 runs `kubectl rollout undo` and prints the rollout history, with `demo: release broken image` as a change cause.
   - Last line, for example: "Rollback took 1 s; bad release to recovery: 34 s, with 10/10 successful health checks during the incident." (measured on this project: about 1 s and about 34 s).

3. Do the same by hand to see each part. Release the broken image:
   ```bash
   kubectl set image deployment/sre-metrics-app app=sre-metrics-app:broken -n application
   kubectl get pods -n application -l app=sre-metrics-app
   ```
   What you should see: 2 `Running` pods and 1 new pod that is not ready, with `ErrImageNeverPull`.

4. Check the rollout status (it times out because it is stuck).
   ```bash
   kubectl rollout status deployment/sre-metrics-app -n application --timeout=20s
   ```
   What you should see: "Waiting for deployment ... 1 out of 2 new replicas have been updated..." and then a timeout error.

5. Roll back and confirm.
   ```bash
   kubectl rollout undo deployment/sre-metrics-app -n application
   kubectl rollout status deployment/sre-metrics-app -n application
   kubectl get deployment sre-metrics-app -n application -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
   ```
   What you should see: "successfully rolled out" and the image `sre-metrics-app:1.0.0`.

**Self-check**
1. What would users see if `maxUnavailable` were `1` and the new image was broken?
2. Why did the app answer 10/10 checks even though the release failed?
3. Which command shows which revision you can go back to?
4. In the demo, what is the difference between "rollback took" and "bad release to recovery"? Which one is closer to MTTR?

<details><summary>Answers (try first)</summary>

1. Kubernetes could remove one old pod before the new one is ready. Only one pod would serve traffic, so capacity is halved. With 1 replica it would be an outage.
2. `maxUnavailable: 0` keeps both old pods until a new pod is Ready, and the broken pod never becomes Ready, so the Service never sends it traffic.
3. `kubectl rollout history deployment/sre-metrics-app -n application`.
4. "Rollback took" is the undo plus waiting until the old version is fully rolled out again. "Bad release to recovery" starts at the bad release and also includes the detection part, which the script simulates (about 30 s of health checks and a stuck-rollout check). MTTR corresponds to the second one. In real life the detection part (TTD) is done by people and alerts, and it is usually the longest.
</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| The script stops at the first `rollout status` | The app was not healthy before the demo. Run `kubectl get pods -n application` and fix that first (for example run `./scripts/deploy.sh` again). |
| You see `ImagePullBackOff` instead of `ErrImageNeverPull` | You changed `imagePullPolicy`. Both mean "image not available"; the lesson is the same. |
| A third pod with `ErrImageNeverPull` is still there after the undo | Wait a few seconds; the ReplicaSet of the broken release scales to 0 and the pod is removed. |
| The app answered fewer than 10/10 checks | Check `maxUnavailable` in `k8s/application.yaml`. It must be `0`. |

**Instructor notes**
- This module needs no add-on, so it is a good first live demo of the day.
- Demo live: run the script while a second window shows `kubectl get pods -n application -l app=sre-metrics-app -w`.
- Grading idea: ask students to change `maxUnavailable` to `1` in a copy of the manifest and predict, then explain, the result (without running it if memory is short).
- Evidence to submit: full output of `rollout_demo.py` (with the 10/10 line and the timing line); output of `kubectl rollout history` after the undo.

**Clean up**

No add-on to remove. Check that the app is healthy:
```bash
kubectl rollout status deployment/sre-metrics-app -n application
```

---

### M15 Chaos engineering

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| 2026 exercise 19 | 45 min | core stack + Argo Workflows + LitmusChaos only | Intermediate | M14; topic 0 (SLOs); remove other add-ons first |

**Learning objectives**
- Write a chaos hypothesis with a steady state, a fault and an expected result.
- Run a LitmusChaos pod-delete experiment through an Argo Workflow and read its verdict and probe status.
- Explain which settings of the app (replicas, readiness probe, rolling strategy) made the hypothesis hold.

**Concepts in 5 minutes**

Chaos engineering is a controlled experiment, not random damage. You state a hypothesis first:

- **Steady state:** the app answers HTTP 200 on `/`.
- **Fault:** delete 50% of the app pods every 10 s for 30 s (`PODS_AFFECTED_PERC=50`, `CHAOS_INTERVAL=10`, `TOTAL_CHAOS_DURATION=30`).
- **Expected:** Kubernetes replaces the pods, 2 replicas and readiness probes keep the Service up, the probe never fails, verdict **Pass**.

The tools:

- **LitmusChaos 3.0.0** runs the fault. A `ChaosExperiment` defines pod-delete, a `ChaosEngine` aims it at `app=sre-metrics-app` in namespace `application`, and a `ChaosResult` holds the verdict.
- The `httpProbe` named `app-keeps-answering` calls `http://sre-metrics-app.application.svc.cluster.local:5000/` every 2 s during the whole experiment (`mode: Continuous`). If it fails, the verdict is Fail.
- **Argo Workflows v3.5.11** runs the steps in order. [`chaos/pod-delete-workflow.yaml`](../../chaos/pod-delete-workflow.yaml) uses only **resource templates** (it applies, creates, reads and deletes Kubernetes objects): `install-experiment`, `run-chaos`, `check-verdict`, `cleanup`.
- [`chaos/rbac.yaml`](../../chaos/rbac.yaml) creates two ServiceAccounts in `litmus`: `chaos-runner` (deletes the app pods) and `chaos-workflow` (runs the workflow). Both are bound to the ClusterRole `sre-chaos`.

**Lab steps**

1. Free memory first (see "Before you start"). Run `kubectl get namespaces`.
   What you should see: no `argocd`, `kyverno`, `argo-rollouts`, `progressive` or `awx` namespace.

2. Write down your hypothesis in your notes (steady state, fault, expected result) before you run anything.
   What you should see: three short lines in your notes, for example "Steady state: / answers 200. Fault: 50% of pods deleted every 10 s for 30 s. Expected: probe never fails, verdict Pass."

3. Run the experiment. The script installs Argo Workflows and LitmusChaos if needed.
   ```bash
   python3 scripts/chaos_test.py
   ```
   What you should see: the app pods before the test, "Started Argo Workflow pod-delete-chaos-xxxxx", and after about 4-5 minutes in total:
   ```
   Workflow phase        : Succeeded
   Chaos verdict         : Pass
   Pods replaced         : 1 of 2
   ```
   plus a probe line for `app-keeps-answering` and "Hypothesis confirmed". (Measured on this project: Succeeded, Pass, probe 200 throughout, 1 of 2 pods replaced, about 4-5 min.)

4. Watch the pods during the run, in a second window.
   ```bash
   kubectl get pods -n application -l app=sre-metrics-app -w
   ```
   What you should see: a pod goes to `Terminating`, a new one appears and becomes `1/1 Running`. Press Ctrl + C to stop watching.

5. Read the result in detail.
   ```bash
   kubectl get workflow -n litmus
   kubectl describe chaosresult sre-metrics-app-pod-delete-pod-delete -n litmus
   ```
   What you should see: the workflow `Succeeded`, and in the ChaosResult `Verdict: Pass` and the probe status.

6. Open Grafana (`./scripts/dashboards.sh`, <http://localhost:3000>), dashboard **Golden Signals**, panels **Error ratio (5xx / all requests)** and **Requests per second by endpoint**, for the time of the experiment.
   What you should see: the error ratio stays at its normal level (about 5% of `/store` calls fail by design), with no extra spike during the 30 s of chaos.

**Self-check**
1. Name the three parts of the hypothesis used here.
2. Which object decides Pass or Fail, and what makes it Fail?
3. What would likely happen with `replicas: 1`?
4. Why does the workflow end with a `cleanup` step?
5. Why must you remove other add-ons before this test?

<details><summary>Answers (try first)</summary>

1. Steady state (HTTP 200 on `/`), fault (delete 50% of pods every 10 s for 30 s), expected result (probe never fails, verdict Pass).
2. The `ChaosResult` `sre-metrics-app-pod-delete-pod-delete`. It fails when the continuous `httpProbe` fails (after its retries).
3. When the only pod is deleted, nothing serves traffic until a new pod is Ready. The probe fails and the verdict is Fail: the hypothesis is rejected, which is a useful finding.
4. It deletes the `ChaosEngine` so the experiment can run again with the same name.
5. Pods that are replaced need memory to start. On a full node the new pod stays `Pending`, and the test fails for the wrong reason.
</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| The script seems to hang for minutes | The full install, chaos and cleanup take several minutes. Wait for the final summary before you assume a failure (course TROUBLESHOOTING Pattern AA). |
| Verdict `Fail` or phase `Failed` | Run the two inspect commands the script prints (`kubectl get workflow ... -o yaml`, `kubectl describe chaosresult ...`). Check that the app has 2 ready pods before you start. |
| "already exists" for the ChaosEngine | A previous run was interrupted. The script deletes the leftover engine at the start; run it again. |

**Instructor notes**
- Demo live: split screen with `kubectl get pods -w` on one side and the script on the other. Pause to ask the class to predict the verdict before it prints.
- Variation for strong groups: in a copy of the workflow, change `PODS_AFFECTED_PERC` to `"100"` in the ChaosEngine section (experiments > spec > components > env), and ask for a new hypothesis first. `chaos_test.py` always runs the original file, so start the copy with `kubectl create -f <your-copy>.yaml`, then read the result with `kubectl get workflow -n litmus` and `kubectl describe chaosresult sre-metrics-app-pod-delete-pod-delete -n litmus`. Discuss the result, do not grade the verdict.
- Grading idea: grade the written hypothesis and the explanation, not just a Pass.
- Evidence to submit: written hypothesis; full script output; output of `kubectl describe chaosresult ...`; a Grafana screenshot of the error rate during the experiment.

**Clean up**
```bash
kubectl delete workflow -n litmus --all
kubectl delete chaosengine,chaosresult -n litmus --all --ignore-not-found
kubectl delete -f chaos/rbac.yaml --ignore-not-found
kubectl delete -f https://litmuschaos.github.io/litmus/litmus-operator-v3.0.0.yaml --ignore-not-found
kubectl delete -n argo -f https://github.com/argoproj/argo-workflows/releases/download/v3.5.11/install.yaml --ignore-not-found
kubectl delete namespace litmus argo --ignore-not-found
```
Delete the engine and the results while the operator still runs, so their finalizers are removed. Otherwise the `litmus` namespace can get stuck in `Terminating`.

---

### M20 Policy as code with Kyverno

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| New in 2027 (turns topic 3 ORR checks into admission rules) | 40 min | core stack + Kyverno only | Intermediate | M14; topic 3 (ORR); remove other add-ons first |

**Learning objectives**
- Read a Kyverno `ClusterPolicy` and list what each rule requires.
- Compare Audit mode (report only) with Enforce mode (reject at admission) using a real rejected pod.
- Interpret a `PolicyReport` and fix a workload that fails the baseline.

**Concepts in 5 minutes**

The ORR checklist (topic 3) asks questions like "does it have resource limits?" and "does it run as root?". Humans forget to ask. A policy engine asks every time, automatically, when a pod is created.

Kyverno v1.13.4 runs as an admission webhook. [`policy/workload-baseline.yaml`](../../policy/workload-baseline.yaml) is the `ClusterPolicy` `sre-workload-baseline`. It applies to pods in the namespaces `application`, `gitops-*`, `sre-metrics-app-*` and `progressive`:

| Rule | Requires |
| --- | --- |
| `require-requests-and-limits` | CPU and memory requests and a memory limit on every container |
| `require-run-as-non-root` | `spec.securityContext.runAsNonRoot: true` |
| `disallow-latest-tag` | a pinned image tag, never `:latest` |
| `require-readiness-probe` | an HTTP readiness probe on pods labelled `app: sre-metrics-app` |

- **Audit** (`validationFailureAction: Audit`, the default here): violations are allowed but written to `PolicyReport` objects. Use it first, to find what would break.
- **Enforce**: the API server rejects the pod. Switch only when the reports are clean.

A real finding from this project: the first alert drill pod (created with `kubectl run errload ...`) violated the baseline. It had no limits and no `runAsNonRoot`. The fix was a proper manifest, [`k8s/drills/errload-pod.yaml`](../../k8s/drills/errload-pod.yaml), with `runAsNonRoot`, requests and limits, and `curlimages/curl:8.10.1`. [`trigger-alert.sh`](../../scripts/trigger-alert.sh) now uses it. Even test tools must follow the rules, or they hide real violations in the report.

**Lab steps**

1. Install Kyverno, apply the policy in Audit mode and run the enforcement demo.
   ```bash
   python3 scripts/policy_setup.py
   ```
   What you should see:
   - "Installing Kyverno v1.13.4 (about 2 minutes)..."
   - `PolicyReport for namespace application: {'pass': 12, 'fail': 0, ...}` (12 was measured on this project; the number depends on how many pods are running).
   - "Rejected by the admission webhook, as expected:" followed by three rule messages for the test pod (`nginx:latest`, no limits, root).
   - "The policy is back in Audit mode."
   The test pod is sent with `--dry-run=server`, so nothing is created.

2. Read the policy status and the reports yourself.
   ```bash
   kubectl get clusterpolicy sre-workload-baseline
   kubectl get policyreport -n application
   ```
   What you should see: the policy Ready (`READY` `True`), and one report per resource (pods, and also their Deployments and ReplicaSets, because Kyverno copies Pod rules to the controllers that create pods) with `PASS` counts and `FAIL` at 0.

3. See which rules a pod passed.
   ```bash
   kubectl get policyreport -n application -o yaml | grep -E "policy:|rule:|result:"
   ```
   What you should see: lines such as `rule: require-requests-and-limits` (or `autogen-require-requests-and-limits` for a Deployment) with `result: pass`.

4. Run the alert drill and confirm the drill pod is compliant.
   ```bash
   ./scripts/trigger-alert.sh
   kubectl get policyreport -n application
   ```
   What you should see: a report for the `errload` pod with no failures. After about 140-150 s `HighErrorRate` fires, as in the alerting module.

5. Compare with the old drill command (Audit mode only lets it through and records it). Create it under a different name, read the report, then delete it.
   ```bash
   kubectl run errload-old -n application --image=curlimages/curl:8.10.1 --restart=Never --command -- sleep 60
   kubectl get policyreport -n application
   kubectl delete pod errload-old -n application
   ```
   What you should see: after a few seconds, a report for `errload-old` with `FAIL` greater than 0 (limits and non-root). In Enforce mode this pod would have been rejected.

**Self-check**
1. What is the difference between Audit and Enforce?
2. Why does the policy start in Audit mode?
3. Which rules did the `nginx:latest` test pod break?
4. Why was the drill pod changed, even though it is only a test tool?

<details><summary>Answers (try first)</summary>

1. Audit allows the pod and records the violation in a PolicyReport. Enforce rejects the pod at the API server.
2. To find existing violations without breaking running workloads. You switch to Enforce once the reports are clean.
3. `require-requests-and-limits`, `require-run-as-non-root` and `disallow-latest-tag`. (It has no `app: sre-metrics-app` label, so the readiness rule does not apply.)
4. Its failures made the report noisy, so real violations would be easy to miss. In Enforce mode it would have been blocked and the alert drill would not run.
</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| Install fails because the CRDs are too large | Use `kubectl apply --server-side --force-conflicts`. The script already does this. |
| `kubectl apply` of the policy fails right after install | The webhook is not ready yet. The script retries for up to 60 s; run it again if it still fails. |
| The report shows 0 pass and 0 fail | The background scan takes up to about 2 minutes. Run `kubectl get policyreport -n application` again. |
| The bad pod was NOT rejected | Check the Kyverno logs: `kubectl logs deployment/kyverno-admission-controller -n kyverno --tail=30`. |
| Alert drill fails or the report shows `errload` failing | You used the old `kubectl run errload` command from an older guide. Use `./scripts/trigger-alert.sh`. |

**Instructor notes**
- Demo live: show the rejection message in step 1, then open [`policy/workload-baseline.yaml`](../../policy/workload-baseline.yaml) and match each message to a rule.
- Discussion: map each rule to an ORR question in [`../ORR.md`](../ORR.md).
- Grading idea: students write one new rule (for example "containers must drop ALL capabilities") in a copy of the policy, explain it, and show a pod that passes and one that fails.
- Evidence to submit: output of `policy_setup.py` with the rejection; output of `kubectl get policyreport -n application`; the report line for `errload-old` showing FAIL.

**Clean up**
```bash
kubectl delete -f policy/workload-baseline.yaml
kubectl delete -f https://github.com/kyverno/kyverno/releases/download/v1.13.4/install.yaml
kubectl delete validatingwebhookconfiguration,mutatingwebhookconfiguration -l webhook.kyverno.io/managed-by=kyverno
```
Remove the policy first. Then remove Kyverno and its webhooks, so the API server does not keep calling a webhook that no longer exists.

---

### M21 Progressive delivery with Argo Rollouts

| Course mapping | Time | Memory | Level | Prerequisites |
| --- | --- | --- | --- | --- |
| New in 2027 (builds on exercise 18 and topic 0) | 45 min | core stack + Argo Rollouts only | Advanced | M14; topic 0 (SLI/SLO); Prometheus (exercise 5); remove other add-ons first |

**Learning objectives**
- Describe how a canary release shifts traffic in steps (25%, 50%, 100%).
- Configure an `AnalysisTemplate` that asks Prometheus for the canary's success rate and gates the release on it.
- Show that a good release is promoted and a bad release is aborted and rolled back automatically.

**Concepts in 5 minutes**

A rolling update (M14) only checks "does the pod start?". A pod can start and still return errors. A **canary** sends a small share of real traffic to the new version, measures it, and only goes on if the numbers are good.

[`progressive/rollout.yaml`](../../progressive/rollout.yaml) creates the namespace `progressive` with:

- A `Rollout` `sre-metrics-app` with 4 replicas. Traffic is split by pod count: 1 of 4 pods = 25%.
- Steps: `setWeight: 25`, pause 120 s, `setWeight: 50`, pause 60 s, `setWeight: 100`.
- An `AnalysisTemplate` `canary-success-rate`. From step 1 it runs in the background: wait 45 s, then measure every 20 s, 6 times, and allow at most 1 failure. Success means the rate is at least 0.90 (or there is no data yet).
- The PromQL query computes the share of non-5xx requests to `http_requests_total` for **only the canary pods**. It filters on `rollouts_pod_template_hash`, a pod label Argo Rollouts adds and Prometheus copies into the metric.
- A `traffic-generator` Deployment that calls `/store` about 5 times per second, so there is data to judge.

The app reads `STORE_ERROR_RATE` (see [`app/app.py`](../../app/app.py)). The stable version uses `0.05` (5% errors). The bad release in the demo uses `0.5` (half of the `/store` calls fail).

**Lab steps**

1. Free memory first (see "Before you start"). Run `kubectl get namespaces`.
   What you should see: none of `argocd`, `litmus`, `argo`, `kyverno`, `awx`.

2. Run the demo (about 10 minutes). It installs Argo Rollouts v1.8.0, deploys the stable version, then releases a good and a bad version.
   ```bash
   python3 scripts/canary_demo.py
   ```
   What you should see:
   - Progress lines like `phase=Paused step=1 canary-weight=- message=CanaryPauseStep`. `canary-weight` stays `-` because this Rollout splits traffic by pod count, not with a traffic router. The step number tells you where it is: `step=1` means 25% (1 of 4 pods).
   - Release 1.1.0 (good): ends `Result: Healthy` with success-rate samples near 0.95.
   - Release 1.2.0 (bad): ends `Result: Degraded, aborted=True` with samples near 0.5. It is stopped at 25% and all pods return to the stable version.
   - The stable spec is restored, and the final line "Canary gate worked: good release promoted, bad release stopped at 25% and rolled back."

3. Watch the Rollout and the analysis runs in a second window while the demo runs.
   ```bash
   kubectl get rollout,analysisrun -n progressive
   kubectl get pods -n progressive -L rollouts-pod-template-hash
   ```
   What you should see: during a canary, two different values in the `ROLLOUTS-POD-TEMPLATE-HASH` column (stable and canary pods), and an AnalysisRun with phase `Running`, then `Successful` or `Failed`.

4. Run the gate query yourself in Prometheus. Open <http://localhost:9090> (`./scripts/dashboards.sh`) and run:
   ```
   sum by (rollouts_pod_template_hash) (rate(http_requests_total{namespace="progressive", status!~"5.."}[1m]))
   /
   sum by (rollouts_pod_template_hash) (rate(http_requests_total{namespace="progressive"}[1m]))
   ```
   What you should see: one line per version. During the bad release the canary line drops to about 0.5 while the stable line stays near 0.95.

5. Read why the bad release was aborted.
   ```bash
   kubectl describe rollout sre-metrics-app -n progressive
   ```
   What you should see: in `Status` and `Events`, the abort and the failed AnalysisRun.

**Self-check**
1. Why does the analysis filter on `rollouts_pod_template_hash` instead of the whole namespace?
2. With 4 replicas, how many users were exposed to the bad version before the abort?
3. What does `len(result) == 0 || result[0] >= 0.90` allow, and why?
4. What is the difference between this gate and `maxUnavailable: 0` in M14?
5. Why is the gate (90%) below the app's normal success rate (about 95%)?

<details><summary>Answers (try first)</summary>

1. Without it, the stable pods' good traffic would hide the canary's errors. The hash selects only the new pods.
2. About 25% of requests, and only for the analysis window (around a minute), because the abort happened at the first step.
3. It passes when there is no data yet (new pods not scraped) and when the success rate is at least 90%. `initialDelay: 45s` also gives Prometheus time to scrape.
4. `maxUnavailable: 0` protects against pods that do not start or become Ready. The canary gate protects against pods that run but return errors, using an SLI.
5. The stable version already has 5% errors by design. A gate at 95% would fail good releases due to normal noise. The gap lets real regressions (50% errors) stand out.
</details>

**Common problems**

| Symptom | Fix |
| --- | --- |
| The good release ends `Degraded` | The analysis had too few samples or the node was overloaded. Check `kubectl get pods -n progressive` and that no other add-on is running; run the demo again. |
| AnalysisRun shows errors about Prometheus | The address `prometheus.monitoring.svc.cluster.local:9090` comes from the raw stack. If you deployed with `./scripts/deploy.sh --helm`, the Prometheus service name is different; use the default deploy. |
| The script prints "Timed out waiting for ..." | Usually memory. Remove other add-ons, then run it again; it reuses what is already installed. |

**Instructor notes**
- Demo live: run the script on the projector and keep the step 4 Prometheus graph next to it. The moment the canary line drops and the abort prints is the key learning.
- Link back to M14: same broken idea, but now the version starts fine and only the SLI shows the problem.
- Grading idea: students change the gate to 0.97 in a copy of the template and predict what happens to the good release, with reasons based on the 5% background error rate.
- Evidence to submit: full output of `canary_demo.py`; a Prometheus screenshot from step 4 during the bad release; output of `kubectl get rollout,analysisrun -n progressive`.

**Clean up**
```bash
kubectl delete namespace progressive
kubectl delete -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/download/v1.8.0/install.yaml
kubectl delete namespace argo-rollouts --ignore-not-found
```

---

### Portfolio project P-POLICY: a new guardrail policy

Optional and open to everyone. It is worth 250 XP. A guardrail policy stops unsafe deployments before they run, so nobody has to remember the rule. It needs Kyverno from M20 (16 GB profile).

**What you build:** a new Kyverno `ClusterPolicy` of your own in `policy/`.

1. Do M20 first, so Kyverno is installed. Read [`policy/workload-baseline.yaml`](../../policy/workload-baseline.yaml) with Bob and ask him to explain each rule in plain words.
2. Pick one rule a team would want, for example "every pod in `application` must have an `owner` label". Write it as a new file, for example `policy/require-owner-label.yaml`, with `kind: ClusterPolicy` and its own `metadata.name`. Start in `Audit` mode, so it reports but does not block.
3. Apply it and check (Windows: `python scripts/lab.py check P-POLICY`):
   ```bash
   kubectl apply -f policy/require-owner-label.yaml
   kubectl get clusterpolicy
   python3 scripts/lab.py check P-POLICY
   ```
   What you should see: your policy in the list, and the check says "policy ... is active in the cluster".
4. Optional, to go further: find a pod that breaks your rule in `kubectl get policyreport -n application`. Keep the policy in `Audit` mode, so the other labs keep working.

**For the interview:** be ready to say what your policy prevents and why a policy is safer than a checklist.

> **Interview corner: The Proving Grounds.** A question you can expect: *"A release breaks production. What do you do in the first five minutes?"* Answer with what you did here: you shipped a broken release and rolled it back with one command (M14), and, if you did the add-ons, ArgoCD restored the state from Git (M13), you killed pods on purpose (M15) and an SLO stopped a bad canary (M21). In plain words: first stop the harm (roll back), tell people, then find the cause. Rehearse it with Bob: type `/interview`.
