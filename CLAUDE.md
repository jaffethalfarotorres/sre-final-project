@AGENTS.md

## Claude Code specifics
- Shared rules for every AI coding agent live in AGENTS.md (imported above); IBM Bob and other agents read the same
  file. Claude Code is one adapter: this file, `.claude/` and `.mcp.json`.
- **Students start with `/lab`** (`.claude/skills/lab/SKILL.md`). It runs the same First on-call shift as IBM Bob:
  the same 9 steps (`lab.py journey`), the preflight first, then the setup kit, then a new terminal and a Claude Code
  restart (`claude --continue`) so the new tools are on PATH. Windows: always `python` (never `python3`);
  Mac/Linux: `python3`. The student runs setup, deploy and cluster-changing commands in their own terminal.
- **Teachers and graders**: run `python scripts/smoke_test.py` (add `--cluster` when the lab runs). It only reads.
  Never commit, push or create a repository for anyone (AGENTS.md, Writing).
- Subagents: `sre-triage` (read-only alert triage) and `postmortem-writer` (drafts in docs/postmortems/ only).
- Skill: `/incident-triage` runs the triage protocol end to end.
- Enforcement does not depend on these instructions: `.claude/settings.json` denies changing commands and secret
  files, and the `guard_mutations.py` PreToolUse hook is a best-effort pattern guard that also catches common
  disguises (`sh -c`, full paths, chains). It only sees the command line, not code that another program runs
  (a test file, a script), so the real backstop is Kubernetes RBAC: start Claude Code with the read-only
  kubeconfig from `scripts/ai_setup.py`. Run `/status` to see which settings are loaded.
- MCP: `.mcp.json` points at the in-cluster Grafana MCP server (http://localhost:8000/mcp, read-only, Viewer
  token). It is available after `python scripts/ai_setup.py` and while `scripts/dashboards.*` runs.
