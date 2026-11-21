"""Unit tests for scripts/sync_skills.py and canonical AI-agnostic skills/agents."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import sync_skills  # noqa: E402


def test_skills_and_agents_in_sync():
    ok, issues = sync_skills.check_sync()
    assert ok, f"Sync check failed with issues: {issues}"
    assert issues == []


def test_canonical_skills_exist_and_have_frontmatter():
    skills = sync_skills.list_canonical_skills()
    assert "lab" in skills
    assert "incident-triage" in skills

    for name, path in skills.items():
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert content.startswith("---"), f"Skill {name} missing YAML frontmatter start"
        parts = content.split("---", 2)
        assert len(parts) >= 3, f"Skill {name} missing closing frontmatter delimiter"
        frontmatter = parts[1]
        assert "name:" in frontmatter
        assert "description:" in frontmatter


def test_canonical_agents_exist_and_have_frontmatter():
    agents = sync_skills.list_canonical_agents()
    assert "sre-triage.md" in agents
    assert "postmortem-writer.md" in agents

    for name, path in agents.items():
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert content.startswith("---"), f"Agent {name} missing YAML frontmatter start"
        parts = content.split("---", 2)
        assert len(parts) >= 3, f"Agent {name} missing closing frontmatter delimiter"
        frontmatter = parts[1]
        assert "name:" in frontmatter
        assert "description:" in frontmatter


def test_sync_cli_check(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["sync_skills.py", "--check"])
    assert sync_skills.main() == 0
