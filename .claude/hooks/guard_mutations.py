#!/usr/bin/env python3
"""
PreToolUse hook for Claude Code (SRE Academy 2027, module M18): a best-effort pattern guard.

It blocks command lines that change the cluster, Helm releases, Terraform state, ArgoCD, GitHub or Git
remotes, that read secrets, or that use flags which run external code, including common disguises:
`sh -c '...'`, full paths (/usr/local/bin/kubectl, C:\\...\\kubectl.exe), chains with ; && ||, and
split words such as kube''ctl. It CANNOT see commands built at run time (K=kubectl; $K delete ...) or
code executed by another program (a Python script, a test file). That is why it is only one of several
layers: Kubernetes RBAC with the read-only kubeconfig is the control that cannot be talked around.

Claude Code sends the tool call as JSON on stdin. Exit code 2 blocks the call and shows the reason to the
model; exit code 0 allows it. Any problem inside the guard also blocks (fails closed).
Standard library only, so it runs on macOS, Windows and Linux.
"""

import json
import re
import sys

# A verb counts only as a standalone word: "delete" in "pod-delete" or "job/delete-me" is a name, not a verb.
PRE = r"(?<![\w./=:-])"
POST = r"(?![\w./=:-])"
ANY = r"[^|;&\n]*?"  # the rest of the same command (stops at the next command separator)

MUTATING = [
    (r"\bkubectl(?:\.exe)?\b" + ANY + PRE + r"(apply|create|delete|patch|edit|replace|scale|label|annotate|drain|"
     r"cordon|uncordon|taint|set|autoscale|expose|run|cp|exec|port-forward|debug|proxy|attach|certificate)" + POST,
     "kubectl {0}"),
    (r"\bkubectl(?:\.exe)?\b" + ANY + PRE + r"rollout\s+(restart|undo|pause|resume)" + POST, "kubectl rollout {0}"),
    (r"\bhelm(?:\.exe)?\b" + ANY + PRE + r"(install|upgrade|uninstall|delete|rollback)" + POST, "helm {0}"),
    (r"\bterraform(?:\.exe)?\b" + ANY + PRE + r"(apply|destroy|import|taint|untaint|force-unlock|"
     r"state\s+(?:rm|mv|push|replace-provider))" + POST, "terraform {0}"),
    (r"\bargocd(?:\.exe)?\b" + ANY + PRE + r"app\s+(sync|delete|rollback|set|patch|create|terminate-op|actions\s+run)"
     + POST, "argocd app {0}"),
    (r"\bminikube(?:\.exe)?\b" + ANY + PRE + r"(delete|stop)" + POST, "minikube {0}"),
    (r"\bgit(?:\.exe)?\b" + ANY + PRE + r"(push)" + POST, "git {0}"),
    (r"\bgh(?:\.exe)?\b" + ANY + PRE + r"(workflow\s+run|release\s+create|pr\s+merge|secret\s+set)" + POST, "gh {0}"),
    (r"\bansible-playbook\b" + ANY + r"restart-app", "the restart-app runbook"),
]

# Reading secrets is blocked too (AGENTS.md rule 4).
SECRETS = [
    (r"(?:alertmanager|grafana)-secret\.yaml", "a secret manifest"),  # *.example.yaml stays readable
    (r"\.tfstate", "Terraform state"),
    (r"(?:^|[\s/'\"=])\.env(?:\.[\w-]+)?(?!\w)", "a .env file"),
    (r"\bkubectl(?:\.exe)?\b" + ANY + PRE + r"get" + POST + ANY + r"(?<![\w-])secrets?(?![\w-])", "Kubernetes Secrets"),
    (r"\bkubectl(?:\.exe)?\b" + ANY + PRE + r"get" + POST + ANY + r"--raw" + ANY + r"/secrets", "Kubernetes Secrets"),
]

# Flags that make a "read-only" tool execute other programs or use another identity.
EXTERNAL_CODE = re.compile(r"\b(?:kubectl|helm|kustomize)(?:\.exe)?\b" + ANY +
                           r"(--post-renderer|--enable-exec|--enable-alpha-plugins|--helm-command|--kubeconfig)",
                           re.IGNORECASE)


def _forms(command):
    """Normalized versions of the command line to scan."""
    # Separators inside quotes do not end a command: neutralize them so the scan continues.
    s = re.sub(r"'[^']*'|\"[^\"]*\"", lambda m: re.sub(r"[;|&]", "_", m.group(0)), command)
    yield s.replace("\\", "/")           # /usr/local/bin/kubectl, C:\...\kubectl.exe
    yield re.sub(r"[\\'\"]", "", s)       # kube''ctl, kub\ectl


def check(command):
    """Return a reason string if the command must be blocked, else None."""
    for normalized in _forms(command):
        for pattern, label in SECRETS:
            if re.search(pattern, normalized, flags=re.IGNORECASE):
                return f"reading {label} (AGENTS.md rule 4)"
        match = EXTERNAL_CODE.search(normalized)
        if match:
            return f"the flag {match.group(1)}, which runs external code or switches identity"
        for pattern, label in MUTATING:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if match:
                return label.format(*(" ".join(g.split()) for g in match.groups())) if match.groups() else label
    return None


def main():
    try:
        event = json.load(sys.stdin)
        tool_input = event.get("tool_input") or {}
        command = str(tool_input.get("command", "") or "")
    except (ValueError, AttributeError):
        print("guard_mutations: could not read the tool call, blocking to be safe.", file=sys.stderr)
        return 2
    reason = check(command)
    if reason:
        print(f"Blocked by the SRE lab guard: {reason}. AI assistants are read-only here (AGENTS.md). "
              f"Propose the command under 'Proposed human action' for a person to run.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as error:  # any bug in the guard blocks instead of allowing
        print(f"guard_mutations: internal error ({error}), blocking to be safe.", file=sys.stderr)
        sys.exit(2)
