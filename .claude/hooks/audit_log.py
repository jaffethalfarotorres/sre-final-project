#!/usr/bin/env python3
"""
PostToolUse hook for Claude Code (SRE Academy 2027, module M18): appends one JSON line per tool call to
.claude/audit.log (gitignored), so every action an AI assistant took during an exercise can be reviewed
and attached as evidence. Never blocks anything. Standard library only.
"""

import json
import os
import sys
from datetime import datetime, timezone


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    tool_input = event.get("tool_input") or {}
    entry = {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session": event.get("session_id"),
        "tool": event.get("tool_name"),
        "summary": str(tool_input.get("command") or tool_input.get("file_path") or tool_input)[:300],
    }
    project = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or "."
    path = os.path.join(project, ".claude", "audit.log")
    try:
        with open(path, "a", encoding="utf-8") as log:
            log.write(json.dumps(entry) + "\n")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
