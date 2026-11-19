#!/usr/bin/env python3
"""
Cohort report for professors: summarizes the lab-proof/evidence.json files of a whole class.

Collect each student's lab-proof/evidence.json (for example from their forks, renamed to <student>.json) into one
folder, then run:

    python3 scripts/cohort_report.py path/to/folder            # Markdown report on screen
    python3 scripts/cohort_report.py path/to/folder > cohort.md

It shows for the whole class: how many students reached On-Call Ready, XP and levels, the missions most students
finished and the ones most students skipped (good topics to reteach). The evidence files are
self-generated on each student's laptop: for grading, confirm a sample with "lab.py verify" or a short live demo.
"""

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def fingerprint_ok(record):
    body = {k: v for k, v in record.items() if k != "sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() == record.get("sha256")


def load(folder):
    records = []
    for path in sorted(Path(folder).glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            print(f"skipped {path.name}: not valid JSON", file=sys.stderr)
            continue
        if "missions" in record and "xp" in record:
            record["_file"] = path.name
            records.append(record)
    return records


def report(records, catalog):
    titles = {m["id"]: m["title"] for m in catalog["missions"]}
    core = [m["id"] for m in catalog["missions"] if m["kind"] in ("core", "capstone")]
    lines = [f"# Cohort report: {len(records)} students", ""]
    if not records:
        return "\n".join(lines + ["No evidence.json files found."])

    summit = sum(1 for r in records if r.get("summit"))
    levels = Counter(r.get("level", "?") for r in records)
    lines += [f"- Reached On-Call Ready: {summit} of {len(records)}",
              f"- Average XP: {sum(r['xp'] for r in records) // len(records)}",
              "- Levels: " + ", ".join(f"{name} {count}" for name, count in levels.most_common())]
    portfolio = [m for m in catalog["missions"] if m["kind"] == "portfolio"]
    done = Counter(mid for r in records for mid in r["missions"])
    lines += ["", "## Core missions: how many students finished each one", "",
              "| Mission | Title | Finished | Share |", "| --- | --- | --- | --- |"]
    for mid in core:
        lines.append(f"| {mid} | {titles[mid]} | {done[mid]} | {100 * done[mid] // len(records)}% |")
    weak = sorted(core, key=lambda mid: done[mid])[:3]
    lines += ["", "Topics to reteach (fewest students finished): " + ", ".join(f"{m} {titles[m]}" for m in weak)]
    lines += ["", "Optional portfolio projects: " + ", ".join(f"{m['title']} {done[m['id']]}" for m in portfolio)]

    lines += ["", "## Students", "", "| File | Name | Level | XP | Missions | Fingerprint |",
              "| --- | --- | --- | --- | --- | --- |"]
    for r in sorted(records, key=lambda r: -r["xp"]):
        check = "ok" if fingerprint_ok({k: v for k, v in r.items() if k != "_file"}) else "CHANGED"
        lines.append(f"| {r['_file']} | {r.get('name', '?')} | {r.get('level', '?')} | {r['xp']} "
                     f"| {len(r['missions'])} | {check} |")
    lines += ["", "Fingerprint CHANGED means the file was edited after `lab.py proof` wrote it. "
              "These files are self-generated: confirm grades with `lab.py verify` or a live demo."]
    return "\n".join(lines)


def main():
    sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(description="Summarize a class's lab-proof/evidence.json files")
    parser.add_argument("folder", help="folder with one evidence JSON file per student")
    args = parser.parse_args()
    catalog = json.loads((ROOT / "lab" / "missions.json").read_text(encoding="utf-8"))
    print(report(load(args.folder), catalog))
    return 0


if __name__ == "__main__":
    sys.exit(main())
