@AGENTS.md

## Claude Code specifics
- Shared rules for every AI assistant live in AGENTS.md (imported above); IBM Bob reads the same file.
- Subagents: `sre-triage` (read-only alert triage) and `postmortem-writer` (drafts in docs/postmortems/ only).
- Skill: `/incident-triage` runs the triage protocol end to end.
- Enforcement does not depend on these instructions: `.claude/settings.json` denies changing commands and secret
  files, and the `guard_mutations.py` PreToolUse hook is a best-effort pattern guard that also catches common
  disguises (`sh -c`, full paths, chains). It only sees the command line, not code that another program runs
  (a test file, a script), so the real backstop is Kubernetes RBAC: start Claude Code with the read-only
  kubeconfig from `scripts/ai_setup.py`. Run `/status` to see which settings are loaded.
- MCP: `.mcp.json` points at the in-cluster Grafana MCP server (http://localhost:8000/mcp, read-only, Viewer
  token). It is available after `python scripts/ai_setup.py` and while `scripts/dashboards.*` runs.
