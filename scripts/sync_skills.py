#!/usr/bin/env python3
"""
Sync canonical skills and agent definitions into agent-specific adapter folders.

    Canonical sources:
        skills/<name>/SKILL.md   -> .agents/skills/<name>/SKILL.md, .claude/skills/<name>/SKILL.md
        agents/<name>.md         -> .agents/agents/<name>.md, .claude/agents/<name>.md

    Usage:
        python scripts/sync_skills.py         (syncs/updates all targets)
        python scripts/sync_skills.py --check (checks for drift, exit 1 if out of sync)
"""

import argparse
import filecmp
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CANONICAL_SKILLS = os.path.join(ROOT, "skills")
CANONICAL_AGENTS = os.path.join(ROOT, "agents")

TARGETS = [
    {
        "name": "Google Antigravity / Open Agent standard (.agents)",
        "skills": os.path.join(ROOT, ".agents", "skills"),
        "agents": os.path.join(ROOT, ".agents", "agents"),
    },
    {
        "name": "Claude Code (.claude)",
        "skills": os.path.join(ROOT, ".claude", "skills"),
        "agents": os.path.join(ROOT, ".claude", "agents"),
    },
]


def list_canonical_skills():
    """Returns dict of skill_name -> SKILL.md path."""
    skills = {}
    if not os.path.exists(CANONICAL_SKILLS):
        return skills
    for entry in os.listdir(CANONICAL_SKILLS):
        full_dir = os.path.join(CANONICAL_SKILLS, entry)
        if os.path.isdir(full_dir):
            skill_md = os.path.join(full_dir, "SKILL.md")
            if os.path.isfile(skill_md):
                skills[entry] = skill_md
    return skills


def list_canonical_agents():
    """Returns dict of agent_file_name -> agent md path."""
    agents = {}
    if not os.path.exists(CANONICAL_AGENTS):
        return agents
    for entry in os.listdir(CANONICAL_AGENTS):
        if entry.endswith(".md"):
            agents[entry] = os.path.join(CANONICAL_AGENTS, entry)
    return agents


def check_sync():
    """Check that all targets match canonical sources. Returns (ok: bool, issues: list)."""
    canonical_skills = list_canonical_skills()
    canonical_agents = list_canonical_agents()
    issues = []

    if not canonical_skills:
        issues.append("No canonical skills found in skills/")
    if not canonical_agents:
        issues.append("No canonical agents found in agents/")

    for target in TARGETS:
        t_name = target["name"]
        t_skills_dir = target["skills"]
        t_agents_dir = target["agents"]

        # Check skills
        for s_name, s_path in canonical_skills.items():
            t_skill_path = os.path.join(t_skills_dir, s_name, "SKILL.md")
            if not os.path.isfile(t_skill_path):
                issues.append(f"[{t_name}] Missing skill: {s_name} (expected {t_skill_path})")
            elif not filecmp.cmp(s_path, t_skill_path, shallow=False):
                issues.append(f"[{t_name}] Drift in skill '{s_name}': {t_skill_path} does not match {s_path}")

        # Check orphan skills in target
        if os.path.exists(t_skills_dir):
            for entry in os.listdir(t_skills_dir):
                if entry not in canonical_skills and os.path.isdir(os.path.join(t_skills_dir, entry)):
                    issues.append(f"[{t_name}] Orphan skill in adapter: {entry}")

        # Check agents
        for a_name, a_path in canonical_agents.items():
            t_agent_path = os.path.join(t_agents_dir, a_name)
            if not os.path.isfile(t_agent_path):
                issues.append(f"[{t_name}] Missing agent: {a_name} (expected {t_agent_path})")
            elif not filecmp.cmp(a_path, t_agent_path, shallow=False):
                issues.append(f"[{t_name}] Drift in agent '{a_name}': {t_agent_path} does not match {a_path}")

        # Check orphan agents in target
        if os.path.exists(t_agents_dir):
            for entry in os.listdir(t_agents_dir):
                if entry not in canonical_agents and entry.endswith(".md"):
                    issues.append(f"[{t_name}] Orphan agent in adapter: {entry}")

    return len(issues) == 0, issues


def apply_sync():
    """Copy canonical skills and agents into all target directories."""
    canonical_skills = list_canonical_skills()
    canonical_agents = list_canonical_agents()
    copied = 0

    for target in TARGETS:
        t_skills_dir = target["skills"]
        t_agents_dir = target["agents"]

        # Sync skills
        for s_name, s_path in canonical_skills.items():
            dest_dir = os.path.join(t_skills_dir, s_name)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, "SKILL.md")
            if not os.path.exists(dest_path) or not filecmp.cmp(s_path, dest_path, shallow=False):
                shutil.copy2(s_path, dest_path)
                copied += 1

        # Remove orphan skills
        if os.path.exists(t_skills_dir):
            for entry in os.listdir(t_skills_dir):
                entry_dir = os.path.join(t_skills_dir, entry)
                if os.path.isdir(entry_dir) and entry not in canonical_skills:
                    shutil.rmtree(entry_dir)

        # Sync agents
        os.makedirs(t_agents_dir, exist_ok=True)
        for a_name, a_path in canonical_agents.items():
            dest_path = os.path.join(t_agents_dir, a_name)
            if not os.path.exists(dest_path) or not filecmp.cmp(a_path, dest_path, shallow=False):
                shutil.copy2(a_path, dest_path)
                copied += 1

        # Remove orphan agents
        if os.path.exists(t_agents_dir):
            for entry in os.listdir(t_agents_dir):
                if entry.endswith(".md") and entry not in canonical_agents:
                    os.remove(os.path.join(t_agents_dir, entry))

    return copied


def main():
    parser = argparse.ArgumentParser(description="Sync canonical skills and agents to adapters")
    parser.add_argument("--check", action="store_true", help="Check for drift without modifying files")
    parser.add_argument("--fix", action="store_true", help="Force synchronize all adapters from canonical sources")
    args = parser.parse_args()

    if args.check:
        ok, issues = check_sync()
        if ok:
            print("PASS: All agent skills and subagents are in sync across adapters.")
            return 0
        else:
            print("FAIL: Agent skills and subagents are out of sync:")
            for issue in issues:
                print(f"  - {issue}")
            print("\nRun 'python scripts/sync_skills.py' to synchronize adapters.")
            return 1

    copied = apply_sync()
    ok, issues = check_sync()
    if ok:
        print(f"PASS: Synchronized skills and agents across adapters ({copied} files updated).")
        return 0
    else:
        print("FAIL: Sync completed with errors:")
        for issue in issues:
            print(f"  - {issue}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
