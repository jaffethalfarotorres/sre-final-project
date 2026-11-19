#!/usr/bin/env python3
"""
SRE Academy Lab Game: missions, XP, levels, achievements and a shareable proof.

Every mission is verified against your real cluster or repository by a read-only check: nothing is
self-reported. IBM Bob (mode "SRE Lab Guide") and Claude Code (/lab) use this script as the game engine,
and you can run it yourself:

    python3 scripts/lab.py status              # level, XP, next mission
    python3 scripts/lab.py missions            # every mission and whether it is done
    python3 scripts/lab.py show M05            # what to do, where the guide is, the quiz questions
    python3 scripts/lab.py check M05           # verify a mission on your cluster (read-only)
    python3 scripts/lab.py check --all         # verify everything that can be verified now
    python3 scripts/lab.py answer M05 1 b      # answer quiz question 1 of M05
    python3 scripts/lab.py proof --name "Ada"  # write lab-proof/: passport, badge and evidence

On Windows PowerShell use "python" instead of "python3". Progress is kept in .lab/progress.json.
"""

import argparse
import glob
import hashlib
import json
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


def check_dashboards_provisioned():
    grafana = kubectl_json("get", "deployment", "grafana", "-n", "monitoring") or {}
    # Kustomize keeps old hashed ConfigMaps around: read the one Grafana actually mounts.
    mounted = [v["configMap"]["name"] for v in grafana.get("spec", {}).get("template", {}).get("spec", {})
               .get("volumes", []) if v.get("name") == "dashboards" and "configMap" in v]
    cm = kubectl_json("get", "configmap", mounted[0], "-n", "monitoring") if mounted else None
    names = sorted((cm or {}).get("data", {}).keys())
    ok = len(names) >= 4 and grafana.get("status", {}).get("availableReplicas", 0) >= 1
    return evidence(ok, f"{len(names)} dashboards provisioned: {', '.join(names)}")


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
    return evidence(ok, "AWX running and wired to Alertmanager" if ok else "run python3 scripts/awx_setup.py first")


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


def _origin_repo():
    code, url = run("git", "-C", str(ROOT), "remote", "get-url", "origin")
    match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url) if code == 0 else None
    return match.group(1) if match else None


def check_fork_ci_green():
    repo = _origin_repo()
    if not repo:
        return evidence(False, "no GitHub origin remote (fork the repo first, see Part 3 M09b)")
    if repo.lower() == "jaffethalfarotorres/sre-final-project":
        return evidence(False, "origin is the course repository: fork it and set origin to your fork")
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
                    else "run python3 scripts/rollout_demo.py")


def check_chaos_passed():
    result = kubectl_json("get", "chaosresult", "sre-metrics-app-pod-delete-pod-delete", "-n", "litmus") or {}
    verdict = result.get("status", {}).get("experimentStatus", {}).get("verdict")
    return evidence(verdict == "Pass", f"chaos verdict: {verdict or 'none yet'}")


def check_dora_report():
    path = ROOT / "reports" / "dora.md"
    ok = path.exists() and "Deployment frequency" in path.read_text(encoding="utf-8", errors="replace")
    return evidence(ok, "reports/dora.md found" if ok
                    else "run: python3 scripts/dora_metrics.py <you>/sre-final-project > reports/dora.md")


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
    if not repo or repo.lower() == "jaffethalfarotorres/sre-final-project":
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
                    else "run python3 scripts/policy_setup.py")


def check_canary_gated():
    runs = (kubectl_json("get", "analysisrun", "-n", "progressive") or {"items": []})["items"]
    phases = {r.get("status", {}).get("phase") for r in runs}
    ok = {"Successful", "Failed"} <= phases
    return evidence(ok, f"analysis runs: {sorted(p for p in phases if p)}" if runs
                    else "run python3 scripts/canary_demo.py")


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
    correct = sum(1 for n in range(1, len(mission["quiz"]) + 1) if progress["quiz"].get(f"{mission_id}:{n}"))
    return evidence(correct == len(mission["quiz"]), f"{correct}/{len(mission['quiz'])} quiz answers correct")


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
    return {"missions": {}, "quiz": {}}


def save_progress(progress):
    PROGRESS.parent.mkdir(exist_ok=True)
    PROGRESS.write_text(json.dumps(progress, indent=2), encoding="utf-8")


def xp_of(catalog, progress):
    by_id = {m["id"]: m for m in catalog["missions"]}
    mission_xp = sum(by_id[mid]["xp"] for mid in progress["missions"] if mid in by_id)
    return mission_xp + catalog["quiz_xp"] * sum(1 for v in progress["quiz"].values() if v)


def level_of(catalog, xp):
    current, following = catalog["levels"][0], None
    for level in catalog["levels"]:
        if xp >= level["xp"]:
            current = level
        elif following is None:
            following = level
    return current, following


def next_mission(catalog, progress):
    for mission in catalog["missions"]:
        if mission["id"] not in progress["missions"] and mission["kind"] == "core":
            return mission
    for mission in catalog["missions"]:
        if mission["id"] not in progress["missions"]:
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
    done, total = len(progress["missions"]), len(catalog["missions"])
    print(f"Level: {level['name']}   XP: {xp}")
    if following:
        progress_bar = bar(xp - level["xp"], following["xp"] - level["xp"])
        print(f"Next level: {following['name']} at {following['xp']} XP  [{progress_bar}]")
    print(f"Missions: {done}/{total}  [{bar(done, total)}]")
    badges = [m["achievement"] for m in catalog["missions"] if m["id"] in progress["missions"] and m["achievement"]]
    print("Achievements: " + (", ".join(badges) if badges else "none yet"))
    mission = next_mission(catalog, progress)
    if mission:
        print(f"\nNext mission: {mission['id']} {mission['title']} (+{mission['xp']} XP)\n  {mission['goal']}")
        print(f"  Guide: {mission['guide']}   Check: python3 scripts/lab.py check {mission['id']}")
    else:
        print("\nEvery mission is complete. Run: python3 scripts/lab.py proof --name \"Your Name\"")


def cmd_missions(args):
    catalog, progress = load_catalog(), load_progress()
    for mission in catalog["missions"]:
        mark = "x" if mission["id"] in progress["missions"] else " "
        extra = f" [add-on: {mission['needs']}]" if mission["needs"] else ""
        print(f"[{mark}] {mission['id']:<5} Part {mission['part']}  +{mission['xp']:<4} {mission['title']}{extra}")


def find(catalog, mission_id):
    for mission in catalog["missions"]:
        if mission["id"].lower() == mission_id.lower():
            return mission
    sys.exit(f"Unknown mission {mission_id}. See: python3 scripts/lab.py missions")


def cmd_show(args):
    catalog, progress = load_catalog(), load_progress()
    mission = find(catalog, args.mission)
    print(f"{mission['id']} {mission['title']}  (+{mission['xp']} XP, Part {mission['part']}, {mission['kind']})")
    print(f"Goal: {mission['goal']}\nGuide: {mission['guide']}")
    if mission["needs"]:
        print(f"Add-on: {mission['needs']} (run one add-on at a time; remove it after the check)")
    for n, q in enumerate(mission["quiz"], 1):
        answered = progress["quiz"].get(f"{mission['id']}:{n}")
        options = "  ".join(f"{k}) {v}" for k, v in q["options"].items())
        print(f"Quiz {n}{' (correct)' if answered else ''}: {q['q']}\n   {options}")


def cmd_check(args):
    catalog, progress = load_catalog(), load_progress()
    missions = catalog["missions"] if args.all else [find(catalog, args.mission)]
    newly = []
    for mission in missions:
        result = run_check(mission["check"])
        mark = "PASS" if result["ok"] else "----"
        print(f"{mark} {mission['id']:<5} {mission['title']}: {result['detail']}")
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
        print(f"\nTotal XP: {xp}  Level: {level_of(catalog, xp)[0]['name']}")
    return 0 if all(m["id"] in progress["missions"] for m in missions) else 1


def cmd_answer(args):
    catalog, progress = load_catalog(), load_progress()
    mission = find(catalog, args.mission)
    if not 1 <= args.number <= len(mission["quiz"]):
        sys.exit(f"{mission['id']} has {len(mission['quiz'])} quiz question(s)")
    key = f"{mission['id']}:{args.number}"
    expected = mission["quiz"][args.number - 1]["answer"]
    given = hashlib.sha256(f"{catalog['salt']}:{mission['id']}:{args.number}:{args.choice.lower()}".encode())
    if given.hexdigest()[:16] == expected:
        if not progress["quiz"].get(key):
            progress["quiz"][key] = True
            save_progress(progress)
            print(f"Correct! +{catalog['quiz_xp']} XP")
        else:
            print("Correct (already counted).")
        return 0
    print("Not quite. Re-read the guide section and try again.")
    return 1


BADGE = """<svg xmlns="http://www.w3.org/2000/svg" width="320" height="64" role="img" aria-label="{label}">
<rect width="320" height="64" rx="10" fill="#0b3d2e"/><rect x="4" y="4" width="312" height="56" rx="8" fill="#12694f"/>
<text x="16" y="28" font-family="Verdana,Arial" font-size="15" font-weight="bold"
 fill="#ffffff">SRE Academy Lab: {level}</text>
<text x="16" y="49" font-family="Verdana,Arial" font-size="12"
 fill="#d9f2e8">{xp} XP | {done}/{total} missions | {badges} achievements</text>
</svg>
"""


def cmd_proof(args):
    catalog, progress = load_catalog(), load_progress()
    xp = xp_of(catalog, progress)
    level = level_of(catalog, xp)[0]["name"]
    done = [m for m in catalog["missions"] if m["id"] in progress["missions"]]
    badges = [m["achievement"] for m in done if m["achievement"]]
    PROOF_DIR.mkdir(exist_ok=True)
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record = {"name": args.name, "level": level, "xp": xp, "generated": generated,
              "repository": _origin_repo(), "missions": {m["id"]: progress["missions"][m["id"]] for m in done},
              "quiz_correct": sum(1 for v in progress["quiz"].values() if v)}
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
        "Every mission below was verified automatically against a live Kubernetes cluster or repository by "
        "`scripts/lab.py` (SRE Academy lab).\n\n| Mission | Title | Date | Evidence |\n| --- | --- | --- | --- |\n"
        f"{rows}\n\nEvidence hash (SHA-256 of evidence.json without this field): `{record['sha256']}`\n",
        encoding="utf-8")
    print(f"Wrote {PROOF_DIR / 'PASSPORT.md'}, badge.svg and evidence.json ({level}, {xp} XP).")
    print("Share it: commit lab-proof/ to your fork and link PASSPORT.md, or add the badge to your profile README.")


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
    args = parser.parse_args()
    if args.command == "check" and not (args.mission or args.all):
        parser.error("give a mission id or --all")
    handler = {"status": cmd_status, "missions": cmd_missions, "show": cmd_show, "check": cmd_check,
               "answer": cmd_answer, "proof": cmd_proof}.get(args.command or "status")
    return handler(args) or 0


if __name__ == "__main__":
    sys.exit(main())
