#!/usr/bin/env python3
"""
DORA metrics from this repository's own history (SRE Academy 2027, module M16).

DORA's current five metrics, measured from GitHub data:
  Throughput
    - Deployment frequency            successful CD workflow runs (cd.yml) per week
    - Change lead time                commit time -> successful deployment of that commit (median)
    - Failed deployment recovery time issue labeled "incident": opened -> closed (median)
  Instability
    - Change fail rate                deployments followed by an "incident" issue within 24 h
    - Deployment rework rate          deployments that were unplanned fixes (tag patch > 0 or
                                      release made within 24 h of the previous one)

Works on macOS, Windows and Linux with only the Python standard library. A public repository needs no
token (60 API calls per hour); set GITHUB_TOKEN for more.

    python scripts/dora_metrics.py [owner/repo] [--days 90]
"""

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.github.com"


def github(path, params=None):
    url = f"{API}{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "sre-academy-dora-metrics"}
    if os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310 - fixed https API URL
        return json.loads(response.read().decode())


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def default_repo():
    try:
        url = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True).stdout
        match = re.search(r"github\.com[:/](.+?)(?:\.git)?\s*$", url)
        return match.group(1) if match else None
    except OSError:
        return None


def hours(delta):
    return delta.total_seconds() / 3600


def fmt_hours(value):
    if value is None:
        return "n/a"
    return f"{value / 24:.1f} days" if value >= 48 else f"{value:.1f} h"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("repo", nargs="?", default=default_repo(), help="owner/repo (default: git remote origin)")
    parser.add_argument("--days", type=int, default=90, help="time window in days (default 90)")
    args = parser.parse_args()
    if not args.repo:
        sys.exit("Give the repository as owner/repo.")
    since = datetime.now(timezone.utc) - timedelta(days=args.days)

    runs = github(f"/repos/{args.repo}/actions/workflows/cd.yml/runs",
                  {"status": "success", "per_page": 100}).get("workflow_runs", [])
    deploys = sorted((r for r in runs if parse_time(r["created_at"]) >= since), key=lambda r: r["created_at"])

    incidents = github(f"/repos/{args.repo}/issues", {"labels": "incident", "state": "all", "per_page": 100})
    incidents = [i for i in incidents if "pull_request" not in i and parse_time(i["created_at"]) >= since]

    # Change lead time: commit timestamp of the deployed SHA -> deployment finished.
    lead_times = []
    for run in deploys:
        commit = github(f"/repos/{args.repo}/commits/{run['head_sha']}")
        committed = parse_time(commit["commit"]["committer"]["date"])
        lead_times.append(hours(parse_time(run["updated_at"]) - committed))

    # Change fail rate: an incident opened within 24 h after a deployment.
    failed = 0
    for run in deploys:
        done = parse_time(run["updated_at"])
        if any(timedelta(0) <= parse_time(i["created_at"]) - done <= timedelta(hours=24) for i in incidents):
            failed += 1

    # Rework: patch releases (vX.Y.Z with Z > 0) or a deployment within 24 h of the previous one.
    rework = 0
    for previous, current in zip([None] + deploys[:-1], deploys):
        tag = current.get("head_branch") or ""
        patch = re.match(r"v?\d+\.\d+\.(\d+)", tag)
        gap = parse_time(current["created_at"]) - parse_time(previous["created_at"]) if previous else None
        quick = gap is not None and gap < timedelta(hours=24)
        if (patch and int(patch.group(1)) > 0) or quick:
            rework += 1

    recovery = [hours(parse_time(i["closed_at"]) - parse_time(i["created_at"]))
                for i in incidents if i.get("closed_at")]
    weeks = max(args.days / 7, 1)
    count = len(deploys)

    rows = [
        ("Deployment frequency", f"{count / weeks:.2f} per week ({count} deployments in {args.days} days)"),
        ("Change lead time (median)", fmt_hours(statistics.median(lead_times)) if lead_times else "n/a"),
        ("Failed deployment recovery time (median)", fmt_hours(statistics.median(recovery)) if recovery else "n/a"),
        ("Change fail rate", f"{failed / count:.0%} ({failed} of {count})" if count else "n/a"),
        ("Deployment rework rate", f"{rework / count:.0%} ({rework} of {count})" if count else "n/a"),
    ]
    print(f"DORA metrics for {args.repo}, last {args.days} days\n")
    print("| Metric | Value |\n| --- | --- |")
    for name, value in rows:
        print(f"| {name} | {value} |")
    if not count:
        print("\nNo successful CD runs yet: publish a release (tag v1.0.0) to start measuring.")
    if not incidents:
        print("No issues labeled 'incident' yet: open one with the Incident form after a drill.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
