#!/usr/bin/env python3
"""
SRE Academy Lab Game: missions, XP, levels, achievements and a shareable proof.

Theme: the Road to Junior SRE. With Bob, your AI pair, you climb camp by camp from "Career Changer" to On-Call
Ready (the lab's last camp: you completed its on-call missions; it is practice, not a job certification). Each
camp teaches one SRE principle. A CV skill is listed only when the mission that proves it is done.
A mission is only marked done when a read-only check finds the evidence on your cluster or repository. The
progress file and the passport stay on your own laptop, so professors confirm them with "lab.py verify" or a
short live demo. IBM Bob (mode "SRE Lab Guide") and Claude Code (/lab) use this script as the game engine,
and you can run it yourself:

    python3 scripts/lab.py status              # level, XP, next mission
    python3 scripts/lab.py missions            # every mission and whether it is done
    python3 scripts/lab.py show M05            # what to do, where the guide is, the quiz questions
    python3 scripts/lab.py check M05           # check a mission on your cluster (read-only)
    python3 scripts/lab.py check --all         # check everything that can be checked now
    python3 scripts/lab.py answer M05 1 b      # answer quiz question 1 of M05 (2 attempts)
    python3 scripts/lab.py cv                  # the skills you have earned, ready for your CV
    python3 scripts/lab.py play                # open Mission Control, the visual dashboard
    python3 scripts/lab.py verify              # re-run the checks of every recorded mission (professors)
    python3 scripts/lab.py proof --name "Ada"  # write lab-proof/: passport, badge and evidence

On Windows use "python" instead of "python3" ("python3" opens the Microsoft Store there).
Progress is kept in .lab/progress.json.
"""

import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "lab" / "missions.json"
PROGRESS = ROOT / ".lab" / "progress.json"
PROOF_DIR = ROOT / "lab-proof"
PY = "python" if os.name == "nt" else "python3"
COURSE_REPO = "jaffethalfarotorres/sre-final-project"
ORIGINAL_DASHBOARDS = {"golden-signals.json", "llm-observability.json", "slo.json", "sre-metrics.json"}
ORIGINAL_RUNBOOKS = {"error-budget-burn.md", "high-error-rate.md", "high-latency.md", "service-down.md"}
ORIGINAL_POLICIES = {"workload-baseline.yaml"}


# ---------------------------------------------------------------------------------------------- helpers
def run(*args, timeout=30):
    """Run a command and return (exit code, stdout). Never raises for a missing tool."""
    try:
        result = subprocess.run(list(args), capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""


def kubectl_json(*args):
    code, out = run("kubectl", *args, "-o", "json")
    if code != 0 or not out:
        return None
    try:
        return json.loads(out)
    except ValueError:
        return None


def proxy(namespace, service, path):
    """GET through the Kubernetes API server proxy (no port-forward needed)."""
    code, out = run("kubectl", "get", "--raw", f"/api/v1/namespaces/{namespace}/services/{service}/proxy{path}")
    return out if code == 0 else None


def prom(query):
    """Instant PromQL query; returns a list of float values (empty when no data)."""
    out = proxy("monitoring", "prometheus:9090", "/api/v1/query?query=" + urllib.parse.quote(query))
    try:
        return [float(r["value"][1]) for r in json.loads(out)["data"]["result"]]
    except (TypeError, ValueError, KeyError):
        return []


def evidence(ok, detail):
    return {"ok": bool(ok), "detail": detail}


# ---------------------------------------------------------------------------------------------- checks
def check_stack_ready():
    pods = []
    for namespace in ("application", "monitoring", "opentelemetry"):
        data = kubectl_json("get", "pods", "-n", namespace)
        if data is None:
            return evidence(False, f"cannot list pods in {namespace}: is Minikube running and the stack deployed?")
        pods += [p for p in data["items"] if p["status"].get("phase") != "Succeeded"]
    not_ready = [p["metadata"]["name"] for p in pods
                 if not all(c.get("ready") for c in p["status"].get("containerStatuses", []) or [{}])]
    detail = f"{len(pods) - len(not_ready)}/{len(pods)} pods ready"
    if not_ready:
        detail += f"; waiting: {', '.join(not_ready[:4])}"
    return evidence(len(pods) >= 9 and not not_ready, detail)


def check_app_signals():
    series = prom('count(http_requests_total{namespace="application"})')
    services = proxy("opentelemetry", "jaeger:16686", "/api/services") or ""
    ok = bool(series and series[0] > 0) and "sre-metrics-app" in services
    return evidence(ok, f"metric series: {int(series[0]) if series else 0}; "
                        f"trace service in Jaeger: {'yes' if 'sre-metrics-app' in services else 'no'}")


def check_deployment_hardened():
    d = kubectl_json("get", "deployment", "sre-metrics-app", "-n", "application")
    if not d:
        return evidence(False, "deployment sre-metrics-app not found")
    spec = d["spec"]
    pod = spec["template"]["spec"]
    container = pod["containers"][0]
    checks = {
        "2+ replicas available": d["status"].get("availableReplicas", 0) >= 2,
        "maxUnavailable 0": str(spec.get("strategy", {}).get("rollingUpdate", {}).get("maxUnavailable")) == "0",
        "readiness probe": "readinessProbe" in container,
        "memory limit": "memory" in container.get("resources", {}).get("limits", {}),
        "runAsNonRoot": pod.get("securityContext", {}).get("runAsNonRoot") is True,
    }
    missing = [k for k, v in checks.items() if not v]
    return evidence(not missing, "all hardening checks pass" if not missing else "missing: " + ", ".join(missing))


def check_targets_up():
    total = prom("count(up)")
    down = prom("count(up == 0)")
    total_n, down_n = int(total[0]) if total else 0, int(down[0]) if down else 0
    return evidence(total_n >= 6 and down_n == 0, f"{total_n - down_n}/{total_n} scrape targets up")


def _provisioned_dashboards():
    """Dashboard files in the ConfigMap Grafana actually mounts (Kustomize keeps old hashed copies around)."""
    grafana = kubectl_json("get", "deployment", "grafana", "-n", "monitoring") or {}
    mounted = [v["configMap"]["name"] for v in grafana.get("spec", {}).get("template", {}).get("spec", {})
               .get("volumes", []) if v.get("name") == "dashboards" and "configMap" in v]
    cm = kubectl_json("get", "configmap", mounted[0], "-n", "monitoring") if mounted else None
    running = grafana.get("status", {}).get("availableReplicas", 0) >= 1
    return sorted((cm or {}).get("data", {}).keys()), running


def check_dashboards_provisioned():
    names, running = _provisioned_dashboards()
    return evidence(len(names) >= 4 and running, f"{len(names)} dashboards provisioned: {', '.join(names)}")


def check_dashboards_custom():
    names, running = _provisioned_dashboards()
    own = [n for n in names if n not in ORIGINAL_DASHBOARDS]
    return evidence(bool(own) and running, f"your own dashboard(s) in Grafana: {', '.join(own)}" if own else
                    "no new dashboard yet: add a JSON to k8s/config/grafana/dashboards/ and to k8s/kustomization.yaml, "
                    "then redeploy")


def check_alert_fired(alertname):
    fired = prom(f'max_over_time(ALERTS{{alertname="{alertname}",alertstate="firing"}}[24h])')
    return evidence(bool(fired), f"{alertname} {'fired' if fired else 'has not fired'} in the last 24 hours")


def check_logs_and_traces():
    query = urllib.parse.quote('sum(count_over_time({service_name="sre-metrics-app"} | severity_text="ERROR" [24h]))')
    out = proxy("opentelemetry", "loki:3100", f"/loki/api/v1/query?query={query}")
    try:
        errors = int(float(json.loads(out)["data"]["result"][0]["value"][1]))
    except (TypeError, ValueError, KeyError, IndexError):
        errors = 0
    failed_spans = prom('sum(otel_collector_span_metrics_calls_total{status_code="STATUS_CODE_ERROR"})')
    ok = errors > 0 and bool(failed_spans and failed_spans[0] > 0)
    spans = int(failed_spans[0]) if failed_spans else 0
    return evidence(ok, f"ERROR log lines in Loki (24 h): {errors}; failed spans: {spans}")


def check_synthetic_probes():
    probes = prom('probe_success{job="blackbox-http"}')
    return evidence(len(probes) >= 2, f"{len(probes)} synthetic probes reporting")


TIME_RE = re.compile(r"\bTT[DAR]\b[^\n|]*\|?[^\n]*\d", re.IGNORECASE)


def _postmortems():
    return [p for p in glob.glob(str(ROOT / "docs" / "postmortems" / "*.md")) if not p.endswith("README.md")]


def check_postmortem_written():
    for path in _postmortems():
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        found = {k for k in ("TTD", "TTA", "TTR") if re.search(rf"{k}\s*[=:|]?\s*[^\n]*\d", text)}
        if found == {"TTD", "TTA", "TTR"}:
            return evidence(True, f"{Path(path).name} has TTD, TTA and TTR")
    return evidence(False, "no postmortem in docs/postmortems/ with TTD, TTA and TTR numbers yet")


def check_diagnostics_report():
    reports = sorted(glob.glob(str(ROOT / "reports" / "incident-*.md")))
    return evidence(bool(reports), f"{len(reports)} diagnostics report(s) in reports/")


def check_awx_configured():
    code, _ = run("kubectl", "get", "secret", "awx-webhook-token", "-n", "monitoring")
    web = kubectl_json("get", "deployment", "awx-web", "-n", "awx") or {}
    ok = code == 0 and web.get("status", {}).get("availableReplicas", 0) >= 1
    return evidence(ok, "AWX running and wired to Alertmanager" if ok else f"run {PY} scripts/awx_setup.py first")


def check_terraform_applied():
    for state in (ROOT / "terraform" / "terraform.tfstate", ROOT / "terraform" / "terraform.tfstate.backup"):
        if state.exists():
            try:
                data = json.loads(state.read_text(encoding="utf-8"))
            except ValueError:
                continue
            if data.get("serial", 0) > 0:
                return evidence(True, f"Terraform state serial {data['serial']} (apply was run)")
    return evidence(False, "no Terraform state yet: run terraform apply in terraform/")


def check_terraform_dev_workspace():
    state = ROOT / "terraform" / "terraform.tfstate.d" / "dev" / "terraform.tfstate"
    try:
        serial = json.loads(state.read_text(encoding="utf-8")).get("serial", 0) if state.exists() else 0
    except ValueError:
        serial = 0
    return evidence(serial > 0, f"dev workspace state serial {serial} (apply was run in workspace dev)" if serial
                    else "run in terraform/: terraform workspace new dev, then terraform apply")


def check_runbook_custom():
    rules = "".join(Path(p).read_text(encoding="utf-8", errors="replace")
                    for p in glob.glob(str(ROOT / "k8s" / "config" / "prometheus" / "*.yml")))
    new = [Path(p).name for p in glob.glob(str(ROOT / "docs" / "runbooks" / "*.md"))
           if Path(p).name not in ORIGINAL_RUNBOOKS and Path(p).name.lower() != "readme.md"]
    linked = [name for name in new if re.search(r"runbook_url:.*" + re.escape(name), rules)]
    if linked:
        return evidence(True, f"new runbook {linked[0]} is linked from an alert rule")
    if new:
        return evidence(False, f"{new[0]} exists but no alert rule links it in runbook_url yet")
    return evidence(False, "no new runbook in docs/runbooks/ yet")


def check_policy_custom():
    for path in sorted(glob.glob(str(ROOT / "policy" / "*.y*ml"))):
        name = Path(path).name
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        if name in ORIGINAL_POLICIES or not re.search(r"kind:\s*ClusterPolicy", text):
            continue
        policy = re.search(r"metadata:\s*\n\s+name:\s*([\w.-]+)", text)
        live = kubectl_json("get", "clusterpolicy", policy.group(1)) if policy else None
        state = "active in the cluster" if live else "written but not applied yet"
        return evidence(bool(live), f"policy {name} is {state}")
    return evidence(False, "no new ClusterPolicy in policy/ yet")


def _origin_repo():
    code, url = run("git", "-C", str(ROOT), "remote", "get-url", "origin")
    match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url) if code == 0 else None
    return match.group(1) if match else None


def check_fork_origin():
    repo = _origin_repo()
    if not repo:
        return evidence(False, "no GitHub origin remote yet")
    if repo.lower() == COURSE_REPO:
        return evidence(False, "origin is still the course repository: run gh repo fork --remote (mission M09b)")
    code, parent = run("gh", "repo", "view", repo, "--json", "parent", "--jq", ".parent.nameWithOwner")
    if code == 0 and parent.strip().lower() == COURSE_REPO:
        return evidence(True, f"origin is your fork {repo}")
    return evidence(False, f"{repo} is not a fork of {COURSE_REPO} (or gh is not logged in: gh auth login)")


def check_fork_ci_green():
    repo = _origin_repo()
    if not repo:
        return evidence(False, "no GitHub origin remote (fork the repo first, mission M09b)")
    if repo.lower() == COURSE_REPO:
        return evidence(False, "origin is the course repository: fork it first (mission M09b)")
    code, out = run("gh", "run", "list", "--repo", repo, "--workflow", "ci.yml", "--status", "success",
                    "--limit", "1", "--json", "databaseId")
    ok = code == 0 and out not in ("", "[]")
    return evidence(ok, f"successful CI run on {repo}" if ok else f"no successful CI run on {repo} yet (gh logged in?)")


def check_argocd_synced():
    app = kubectl_json("get", "application", "sre-metrics-app-staging", "-n", "argocd") or {}
    status = app.get("status", {})
    ok = status.get("sync", {}).get("status") == "Synced" and status.get("health", {}).get("status") == "Healthy"
    return evidence(ok, f"ArgoCD application: sync={status.get('sync', {}).get('status')}, "
                        f"health={status.get('health', {}).get('status')}")


def check_rollback_done():
    rs = kubectl_json("get", "replicasets", "-n", "application", "-l", "app=sre-metrics-app") or {"items": []}
    images = [c.get("image", "") for r in rs["items"] for c in r["spec"]["template"]["spec"]["containers"]]
    broken = any("broken" in image for image in images)
    d = kubectl_json("get", "deployment", "sre-metrics-app", "-n", "application") or {}
    healthy = "broken" not in json.dumps(d.get("spec", {})) and d.get("status", {}).get("availableReplicas", 0) >= 2
    return evidence(broken and healthy, "a broken release was rolled back and the app is healthy" if broken and healthy
                    else f"run {PY} scripts/rollout_demo.py")


def check_chaos_passed():
    result = kubectl_json("get", "chaosresult", "sre-metrics-app-pod-delete-pod-delete", "-n", "litmus") or {}
    verdict = result.get("status", {}).get("experimentStatus", {}).get("verdict")
    return evidence(verdict == "Pass", f"chaos verdict: {verdict or 'none yet'}")


def check_dora_report():
    path = ROOT / "reports" / "dora.md"
    ok = path.exists() and "Deployment frequency" in path.read_text(encoding="utf-8", errors="replace")
    return evidence(ok, "reports/dora.md found" if ok
                    else f"run: {PY} scripts/dora_metrics.py <you>/sre-final-project > reports/dora.md")


def _ai_reports():
    return [Path(p).read_text(encoding="utf-8", errors="replace")
            for p in glob.glob(str(ROOT / "reports" / "ai-triage-*.md"))]


def check_ai_triage_report():
    good = [t for t in _ai_reports() if re.search(r"evidence", t, re.I) and re.search(r"runbook", t, re.I)]
    return evidence(bool(good), f"{len(good)} AI triage report(s) with evidence and a runbook step")


def check_injection_flagged():
    flagged = [t for t in _ai_reports() if "INJECTION-DRILL" in t and re.search(r"suspicious", t, re.I)]
    kubeconfig = Path.home() / ".kube" / "sre-ai-readonly.config"
    code, out = run("kubectl", "--kubeconfig", str(kubeconfig), "auth", "can-i", "delete", "pods", "-n", "application")
    safe = kubeconfig.exists() and out.strip() == "no"
    return evidence(bool(flagged) and safe, f"injection flagged in a report: {'yes' if flagged else 'no'}; "
                                            f"AI identity can delete pods: {out.strip() or 'unknown'}")


def check_release_attested():
    repo = _origin_repo()
    if not repo or repo.lower() == COURSE_REPO:
        return evidence(False, "needs your own fork as origin")
    code, tag = run("gh", "release", "view", "--repo", repo, "--json", "tagName", "--jq", ".tagName")
    if code != 0 or not tag:
        return evidence(False, f"no release on {repo} yet")
    image = f"oci://ghcr.io/{repo.split('/')[0].lower()}/sre-metrics-app:{tag.lstrip('v')}"
    code, _ = run("gh", "attestation", "verify", image, "--owner", repo.split("/")[0], timeout=120)
    return evidence(code == 0, f"{image}: provenance {'verified' if code == 0 else 'not verified'}")


def check_policy_active():
    policy = kubectl_json("get", "clusterpolicy", "sre-workload-baseline") or {}
    ready = any(c.get("type") == "Ready" and c.get("status") == "True"
                for c in policy.get("status", {}).get("conditions", []))
    return evidence(ready, "Kyverno policy sre-workload-baseline is ready" if ready
                    else f"run {PY} scripts/policy_setup.py")


def check_canary_gated():
    runs = (kubectl_json("get", "analysisrun", "-n", "progressive") or {"items": []})["items"]
    phases = {r.get("status", {}).get("phase") for r in runs}
    ok = {"Successful", "Failed"} <= phases
    return evidence(ok, f"analysis runs: {sorted(p for p in phases if p)}" if runs
                    else f"run {PY} scripts/canary_demo.py")


def check_genai_metrics():
    tokens = prom("sum(genai_tokens_total)")
    return evidence(bool(tokens and tokens[0] > 0), f"GenAI tokens recorded: {int(tokens[0]) if tokens else 0}")


def check_gameday_postmortem():
    for path in _postmortems():
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        if re.search(r"\bAI\b", text) and re.search(r"human", text, re.I) and re.search(r"TTR", text):
            return evidence(True, f"{Path(path).name} separates AI suggestions from human decisions")
    return evidence(False, "no game-day postmortem with AI vs human decisions yet")


def check_quiz_complete(mission_id):
    catalog, progress = load_catalog(), load_progress()
    mission = next(m for m in catalog["missions"] if m["id"] == mission_id)
    keys = [f"{mission_id}:{n}" for n in range(1, len(mission["quiz"]) + 1)]
    settled = sum(1 for key in keys if quiz_settled(catalog, progress, key))
    return evidence(settled == len(keys), f"{settled}/{len(keys)} quiz questions answered")


CHECKS = {name[len("check_"):]: fn for name, fn in globals().items() if name.startswith("check_")}


def run_check(spec):
    name, _, arg = spec.partition(":")
    fn = CHECKS[name]
    try:
        return fn(arg) if arg else fn()
    except Exception as error:  # a check must never crash the game
        return evidence(False, f"check error: {error}")


# ---------------------------------------------------------------------------------------------- game state
def load_catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def load_progress():
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text(encoding="utf-8"))
    return {"missions": {}, "quiz": {}, "attempts": {}}


def save_progress(progress):
    PROGRESS.parent.mkdir(exist_ok=True)
    PROGRESS.write_text(json.dumps(progress, indent=2), encoding="utf-8")


def quiz_points(catalog, value):
    """A quiz entry is True (old format, full XP) or the XP it earned (full first try, half second try)."""
    if value is True:
        return catalog["quiz_xp"]
    return int(value) if isinstance(value, (int, float)) else 0


def quiz_settled(catalog, progress, key):
    """A question is settled when it was answered correctly or every attempt was used."""
    used = progress.get("attempts", {}).get(key, 0)
    return bool(progress["quiz"].get(key)) or used >= catalog.get("quiz_attempts", 2)


def mission_xp(catalog, progress, mission):
    return mission["xp"]


def xp_of(catalog, progress):
    by_id = {m["id"]: m for m in catalog["missions"]}
    earned = sum(mission_xp(catalog, progress, by_id[mid]) for mid in progress["missions"] if mid in by_id)
    return earned + sum(quiz_points(catalog, v) for v in progress["quiz"].values())


def zone_skills(zone):
    """A zone's skills as {"skill", "proof"} dicts. An older catalog lists plain strings: proof is then None and
    the skill counts when the whole camp is cleared."""
    return [s if isinstance(s, dict) else {"skill": s, "proof": None} for s in zone.get("skills", [])]


def zone_questions(zone):
    """A zone's interview questions as {"kind", "question"} dicts (an older catalog has one plain string)."""
    items = zone.get("interview") or []
    items = [items] if isinstance(items, (str, dict)) else items
    return [q if isinstance(q, dict) else {"kind": "concept", "question": q} for q in items]


def proof_label(catalog, ids):
    """'M14' or 'M13 (add-on)': the mission ids that prove a skill, marking the optional add-ons."""
    kinds = {m["id"]: m["kind"] for m in catalog["missions"]}
    return ", ".join(f"{i} (add-on)" if kinds.get(i) == "addon" else i for i in ids or [])


def skills_earned(catalog, progress):
    """CV skills, in climb order: a skill counts only when every mission that proves it is done, whether or not
    its camp is cleared. Returns (zone, [skill dicts]) for each zone with at least one earned skill."""
    done = set(progress["missions"])
    cleared = set(zones_cleared(catalog, progress))
    earned = []
    for zone in sorted(catalog.get("zones", []), key=lambda z: z["part"]):
        won = [s for s in zone_skills(zone)
               if (set(s["proof"]) <= done if s["proof"] else s["proof"] is None and zone["part"] in cleared)]
        if won:
            earned.append((zone, won))
    return earned


def level_of(catalog, xp):
    current, following = catalog["levels"][0], None
    for level in catalog["levels"]:
        if xp >= level["xp"]:
            current = level
        elif following is None:
            following = level
    return current, following


def zones_cleared(catalog, progress):
    """Zones cleared on the climb, in order: a zone counts when every core mission in it is done AND every zone
    below it is cleared (you cannot reach camp 3 without passing camp 2). Returns the cleared zone parts."""
    cleared = []
    for zone in sorted(catalog.get("zones", []), key=lambda z: z["part"]):
        core = [m for m in catalog["missions"] if m["part"] == zone["part"] and m["kind"] in ("core", "capstone")]
        if not core or not all(m["id"] in progress["missions"] for m in core):
            break
        cleared.append(zone["part"])
    return cleared


def climb(catalog, progress):
    """Bob's climb to the On-Call Ready summit: (level number, current zone or None at the summit, total camps)."""
    zones = catalog.get("zones", [])
    cleared = set(zones_cleared(catalog, progress))
    current = next((z for z in zones if z["part"] not in cleared), None)
    return len(cleared), current, len(zones)


def next_mission(catalog, progress):
    missions = catalog["missions"]
    for kinds in (("core",), ("capstone", "portfolio"), ("addon",)):
        for mission in missions:
            if mission["id"] not in progress["missions"] and mission["kind"] in kinds:
                return mission
    return None


def bar(value, total, width=24):
    filled = int(width * min(value, total) / total) if total else width
    return "#" * filled + "-" * (width - filled)


# ---------------------------------------------------------------------------------------------- commands
def cmd_status(args):
    catalog, progress = load_catalog(), load_progress()
    xp = xp_of(catalog, progress)
    level, following = level_of(catalog, xp)
    missions = catalog["missions"]
    done, total = sum(1 for m in missions if m["id"] in progress["missions"]), len(missions)
    camp_level, camp, camps = climb(catalog, progress)
    print(catalog.get("theme", {}).get("name", "SRE Academy lab"))
    where = f"Camp {camp['part']}: {camp['name']}" if camp else "the On-Call Ready summit"
    print(f"Your climb to On-Call Ready: Level {camp_level}/{camps}   [{bar(camp_level, camps, 16)}]   "
          f"now at {where}")
    print(f"Rank: {level['name']}   XP: {xp}")
    if following:
        progress_bar = bar(xp - level["xp"], following["xp"] - level["xp"])
        print(f"Next level: {following['name']} at {following['xp']} XP  [{progress_bar}]")
    print(f"Missions: {done}/{total}  [{bar(done, total)}]")
    badges = [m["achievement"] for m in catalog["missions"] if m["id"] in progress["missions"] and m["achievement"]]
    print("Achievements: " + (", ".join(badges) if badges else "none yet"))
    mission = next_mission(catalog, progress)
    if mission:
        xp_next = mission_xp(catalog, progress, mission)
        print(f"\nNext mission: {mission['id']} {mission['title']} (+{xp_next} XP)\n  {mission['goal']}")
        print(f"  Guide: {mission['guide']}   Check: {PY} scripts/lab.py check {mission['id']}")
    else:
        print(f"\nEvery mission is complete. Run: {PY} scripts/lab.py proof --name \"Your Name\"")


def cmd_missions(args):
    catalog, progress = load_catalog(), load_progress()
    for mission in catalog["missions"]:
        mark = "x" if mission["id"] in progress["missions"] else " "
        extra = f" [add-on: {mission['needs']}]" if mission["kind"] == "addon" else ""
        extra += " [portfolio project, optional]" if mission["kind"] == "portfolio" else ""
        xp = mission_xp(catalog, progress, mission)
        print(f"[{mark}] {mission['id']:<9} Camp {mission['part']}  +{xp:<4} {mission['title']}{extra}")


def find(catalog, mission_id):
    for mission in catalog["missions"]:
        if mission["id"].lower() == mission_id.lower():
            return mission
    sys.exit(f"Unknown mission {mission_id}. See: {PY} scripts/lab.py missions")


def cmd_show(args):
    catalog, progress = load_catalog(), load_progress()
    mission = find(catalog, args.mission)
    xp = mission_xp(catalog, progress, mission)
    print(f"{mission['id']} {mission['title']}  (+{xp} XP, Camp {mission['part']}, {mission['kind']})")
    print(f"Goal: {mission['goal']}\nGuide: {mission['guide']}")
    if mission["kind"] == "addon":
        print(f"Add-on: {mission['needs']} (run one add-on at a time; remove it after the check)")
    limit = catalog.get("quiz_attempts", 2)
    for n, q in enumerate(mission["quiz"], 1):
        key = f"{mission['id']}:{n}"
        used = progress.get("attempts", {}).get(key, 0)
        state = " (correct)" if progress["quiz"].get(key) else " (locked)" if used >= limit else \
            f" ({limit - used} attempt(s) left)"
        options = "  ".join(f"{k}) {v}" for k, v in q["options"].items())
        print(f"Quiz {n}{state}: {q['q']}\n   {options}")


def cmd_check(args):
    catalog, progress = load_catalog(), load_progress()
    missions = catalog["missions"] if args.all else [find(catalog, args.mission)]
    cleared_before = set(zones_cleared(catalog, progress))
    newly = []
    for mission in missions:
        result = run_check(mission["check"])
        mark = "PASS" if result["ok"] else "----"
        print(f"{mark} {mission['id']:<9} {mission['title']}: {result['detail']}")
        if result["ok"] and mission["id"] not in progress["missions"]:
            progress["missions"][mission["id"]] = {
                "completed": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "evidence": result["detail"]}
            newly.append(mission)
    save_progress(progress)
    for mission in newly:
        line = f"\n+{mission['xp']} XP  Mission complete: {mission['title']}"
        if mission["achievement"]:
            line += f"\nAchievement unlocked: {mission['achievement']}"
        print(line)
    if newly:
        xp = xp_of(catalog, progress)
        print(f"\nTotal XP: {xp}  Rank: {level_of(catalog, xp)[0]['name']}")
    zones = sorted(catalog.get("zones", []), key=lambda z: z["part"])
    cleared_now = zones_cleared(catalog, progress)
    for part in [p for p in cleared_now if p not in cleared_before]:
        step = cleared_now.index(part) + 1
        zone = zones[step - 1]
        following = zones[step] if step < len(zones) else None
        print("\n" + "=" * 60)
        print(f"  LEVEL UP!  Camp {part} cleared: {zone['name']}")
        print(f"  You and Bob reach level {step}/{len(zones)} on the way to the On-Call Ready summit.")
        if zone.get("principle"):
            print(f"  SRE principle you practised: {zone['principle']}")
        done_ids = set(progress["missions"])
        won = [s for s in zone_skills(zone) if s["proof"] is None or set(s["proof"]) <= done_ids]
        if won:
            print("  Skills for your CV (proved by): " + "; ".join(
                s["skill"] + (f" ({proof_label(catalog, s['proof'])})" if s["proof"] else "") for s in won))
        questions = zone_questions(zone)
        if questions:
            print(f"  Interview practice: \"{questions[0]['question']}\" ({PY} scripts/lab.py cv shows all "
                  f"{len(questions)}; type /interview to Bob to rehearse them)")
        print(f"  Next camp: {following['name']} - {following['story']}" if following else
              "  SUMMIT REACHED: On-Call Ready. You completed the lab's on-call missions (practice, not a job "
              f"certification).\n  Run: {PY} scripts/lab.py proof --name \"Your Name\"")
        print("=" * 60)
    write_mission_control()  # keep the visual dashboard current
    return 0 if all(m["id"] in progress["missions"] for m in missions) else 1


def write_mission_control():
    """Write .lab/mission-control.html (the visual dashboard) and return its path."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import lab_ui
    catalog, progress = load_catalog(), load_progress()
    xp = xp_of(catalog, progress)
    level, following = level_of(catalog, xp)
    page = lab_ui.render(catalog, progress, xp, level, following, next_mission(catalog, progress),
                         datetime.now().strftime("%Y-%m-%d %H:%M"), zones_cleared(catalog, progress))
    out = PROGRESS.parent / "mission-control.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out


def cmd_play(args):
    path = write_mission_control()
    print(f"Mission Control: {path}")
    if not args.no_open:
        import webbrowser
        webbrowser.open(path.as_uri())
    print("In IBM Bob you can also open it with: Command Palette > Simple Browser: Show, then paste the file:/// link.")


def cmd_answer(args):
    catalog, progress = load_catalog(), load_progress()
    mission = find(catalog, args.mission)
    if not 1 <= args.number <= len(mission["quiz"]):
        sys.exit(f"{mission['id']} has {len(mission['quiz'])} quiz question(s)")
    key = f"{mission['id']}:{args.number}"
    if progress["quiz"].get(key):
        print("Already answered correctly.")
        return 0
    progress.setdefault("attempts", {})
    limit, used = catalog.get("quiz_attempts", 2), progress["attempts"].get(key, 0)
    if used >= limit:
        print("This question is locked (no attempts left). Ask Bob to explain the idea; it does not block your "
              "missions. Quizzes are for learning, not for grades.")
        return 1
    progress["attempts"][key] = used + 1
    expected = mission["quiz"][args.number - 1]["answer"]
    given = hashlib.sha256(f"{catalog['salt']}:{mission['id']}:{args.number}:{args.choice.lower()}".encode())
    if given.hexdigest()[:16] == expected:
        points = catalog["quiz_xp"] if used == 0 else catalog["quiz_xp"] // 2
        progress["quiz"][key] = points
        save_progress(progress)
        print(f"Correct! +{points} XP" + ("" if used == 0 else " (second try)"))
        return 0
    save_progress(progress)
    left = limit - used - 1
    hint = (f"Re-read the guide section and try once more ({left} attempt left)." if left
            else "That question is now locked; ask Bob to explain the right idea.")
    print("Not quite. " + hint)
    return 1


def cmd_cv(args):
    """The skills earned so far, written so a student can paste them into a CV or a LinkedIn profile."""
    catalog, progress = load_catalog(), load_progress()
    earned = skills_earned(catalog, progress)
    if not earned:
        print("No skill earned yet. Finish mission B00 (Orientation Day) to earn your first skills.")
        return 0
    print("Skills you practised hands-on in the SRE Academy lab. Each one is listed only because the mission in "
          "brackets passed its check:\n")
    for zone, skills in earned:
        for skill in skills:
            proof = f" (proved by {proof_label(catalog, skill['proof'])})" if skill["proof"] else ""
            print(f"- {skill['skill']}{proof}")
    done = [m for m in catalog["missions"] if m["id"] in progress["missions"] and m["kind"] == "portfolio"]
    for mission in done:
        print(f"Portfolio project: {mission['title']} ({mission['goal']}) (proved by {mission['id']})")
    cleared = set(zones_cleared(catalog, progress))
    won = [z for z in sorted(catalog.get("zones", []), key=lambda z: z["part"]) if z["part"] in cleared]
    if not won:
        print("\nClear a whole camp (every core mission in it) to unlock its SRE principle and interview questions.")
        return 0
    print("\nSRE principles you can explain with your own examples:")
    for zone in won:
        if zone.get("principle"):
            print(f"- {zone['principle']}")
    print("\nInterview practice for the camps you cleared (ask Bob to play the interviewer with /interview):")
    for zone in won:
        for item in zone_questions(zone):
            cite = f" Answer with: {', '.join(item['evidence'])}." if item.get("evidence") else ""
            print(f"- {zone['name']} [{item['kind']}]: {item['question']}{cite}")
    return 0


def cmd_verify(args):
    """Re-run the check of every recorded mission now (for professors). It never removes progress."""
    catalog, progress = load_catalog(), load_progress()
    by_id = {m["id"]: m for m in catalog["missions"]}
    still = gone = 0
    print("Live re-check of recorded missions. Some evidence is time-limited (alerts: 24 hours), so an older mission "
          "can show 'not visible now' and still be genuine: ask for a live demo of those.\n")
    for mid, record in progress["missions"].items():
        mission = by_id.get(mid)
        if not mission:
            continue
        result = run_check(mission["check"])
        still, gone = still + result["ok"], gone + (not result["ok"])
        print(f"{'OK  ' if result['ok'] else 'GONE'} {mid:<9} recorded {record.get('completed', '?')[:10]}: "
              f"{result['detail']}")
    print(f"\n{still} confirmed now, {gone} not visible now.")
    return 0


BADGE = """<svg xmlns="http://www.w3.org/2000/svg" width="320" height="64" role="img" aria-label="{label}">
<rect width="320" height="64" rx="10" fill="#0b3d2e"/><rect x="4" y="4" width="312" height="56" rx="8" fill="#12694f"/>
<text x="16" y="28" font-family="Verdana,Arial" font-size="15" font-weight="bold"
 fill="#ffffff">SRE Academy Lab: {level}</text>
<text x="16" y="49" font-family="Verdana,Arial" font-size="12"
 fill="#d9f2e8">{xp} XP | {done}/{total} missions | {badges} achievements</text>
</svg>
"""


SUMMIT_NOTE = ("**On-Call Ready** means the student completed the lab's on-call missions (AI triage, the "
               "prompt-injection drill and a practice game day). It is a lab milestone, not a statement of job "
               "readiness.\n\n")

VERIFY_NOTE = (
    "## How a reviewer can verify this\n\n"
    f"- Live: on the student's laptop, run `{PY} scripts/lab.py verify`. It re-runs the read-only check of every "
    "mission above. Some evidence is time-limited (fired alerts: 24 hours), so ask for a short live demo of those.\n"
    "- Files: postmortems (M09, M27) are in `docs/postmortems/` and can be committed to the student's fork. "
    "Reports stay on the laptop, because Git ignores `reports/`: ask the student to show `reports/incident-*.md` "
    "(M10), `reports/ai-triage-*.md` (M17, M18) and `reports/dora.md` (M16).\n"
    "- `evidence.json` holds the data behind this page. Remove the `sha256` field, hash the rest with "
    "SHA-256 (Python: `json.dumps(data, sort_keys=True)`) and compare it with the fingerprint below.\n\n")

PRIVACY_NOTE = (
    "## Privacy\n\n"
    "If you commit `lab-proof/` to a public fork, everyone can read: the name you typed, your fork's URL, your "
    "XP, level and achievements, and the date and evidence line of each mission. lab.py does not put passwords, "
    "tokens or cluster secrets here, but read the files before you commit. Use a name you are happy to show, or "
    "keep `lab-proof/` out of Git and share it privately.\n")


def cmd_proof(args):
    catalog, progress = load_catalog(), load_progress()
    xp = xp_of(catalog, progress)
    level = level_of(catalog, xp)[0]["name"]
    done = [m for m in catalog["missions"] if m["id"] in progress["missions"]]
    earned = [skill for _, won in skills_earned(catalog, progress) for skill in won]
    skills = [skill["skill"] for skill in earned]
    summit = len(zones_cleared(catalog, progress)) == len(catalog.get("zones", []))
    badges = [m["achievement"] for m in done if m["achievement"]]
    PROOF_DIR.mkdir(exist_ok=True)
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record = {"name": args.name, "level": level, "xp": xp,
              "generated": generated, "skills": skills,
              "skills_proof": {skill["skill"]: skill["proof"] for skill in earned if skill["proof"]},
              "repository": _origin_repo(), "missions": {m["id"]: progress["missions"][m["id"]] for m in done},
              "quiz_correct": sum(1 for v in progress["quiz"].values() if v),
              "summit": summit}
    record["sha256"] = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
    (PROOF_DIR / "evidence.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    badge = BADGE.format(label=f"{level}, {xp} XP", level=level, xp=xp, done=len(done),
                         total=len(catalog["missions"]), badges=len(badges))
    (PROOF_DIR / "badge.svg").write_text(badge, encoding="utf-8")
    rows = "\n".join(f"| {m['id']} | {m['title']} | {progress['missions'][m['id']]['completed'][:10]} | "
                     f"{progress['missions'][m['id']]['evidence']} |" for m in done)
    (PROOF_DIR / "PASSPORT.md").write_text(
        f"# SRE Lab Passport: {args.name}\n\n![badge](badge.svg)\n\n"
        f"**Level:** {level} · **XP:** {xp} · **Missions:** {len(done)}/{len(catalog['missions'])} · "
        f"**Quiz answers correct:** {record['quiz_correct']}\n\n"
        f"**Achievements:** {', '.join(badges) or 'none yet'}\n\n"
        + (SUMMIT_NOTE if summit else "") +
        "## Skills practised hands-on\n\n"
        "A skill is listed only when every mission that proves it (in brackets) passed its check.\n\n" +
        ("".join(f"- {s['skill']}" + (f" ({proof_label(catalog, s['proof'])})" if s["proof"] else "") + "\n"
                 for s in earned) or "- none yet\n") +
        "\n## Missions and evidence\n\n"
        "Each mission below was marked done only when a read-only check in `scripts/lab.py` found the evidence on "
        "the student's own Kubernetes cluster or repository (SRE Academy lab). This passport is generated on the "
        "student's laptop, so it is a record, not a certificate.\n\n| Mission | Title | Date | Evidence |\n"
        f"| --- | --- | --- | --- |\n{rows}\n\n" + VERIFY_NOTE + PRIVACY_NOTE +
        f"\nFingerprint (SHA-256 of evidence.json without this field; it shows accidental edits, it is not a "
        f"signature): `{record['sha256']}`\n",
        encoding="utf-8")
    print(f"Wrote {PROOF_DIR / 'PASSPORT.md'}, badge.svg and evidence.json ({level}, {xp} XP).")
    print("Share it: commit lab-proof/ to your fork and link PASSPORT.md, or add the badge to your profile README.")
    print("Privacy: once committed to a public fork, your name, fork URL and mission evidence are public. "
          "Read PASSPORT.md first (its Privacy section says what it holds).")


def main():
    sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(description="SRE Academy Lab Game")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status")
    sub.add_parser("missions")
    show = sub.add_parser("show")
    show.add_argument("mission")
    check = sub.add_parser("check")
    check.add_argument("mission", nargs="?")
    check.add_argument("--all", action="store_true")
    answer = sub.add_parser("answer")
    answer.add_argument("mission")
    answer.add_argument("number", type=int)
    answer.add_argument("choice")
    proof = sub.add_parser("proof")
    proof.add_argument("--name", required=True)
    sub.add_parser("cv", help="the skills you have earned, ready for your CV")
    sub.add_parser("verify", help="re-run the checks of every recorded mission (professors)")
    play = sub.add_parser("play", help="open Mission Control, the visual dashboard")
    play.add_argument("--no-open", action="store_true", help="only write the HTML file")
    args = parser.parse_args()
    if args.command == "check" and not (args.mission or args.all):
        parser.error("give a mission id or --all")
    handler = {"status": cmd_status, "missions": cmd_missions, "show": cmd_show, "check": cmd_check,
               "answer": cmd_answer, "proof": cmd_proof, "play": cmd_play,
               "cv": cmd_cv, "verify": cmd_verify}.get(args.command or "status")
    return handler(args) or 0


if __name__ == "__main__":
    sys.exit(main())
