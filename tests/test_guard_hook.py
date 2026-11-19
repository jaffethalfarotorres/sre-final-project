"""Tests for the Claude Code PreToolUse guard (.claude/hooks/guard_mutations.py) and its settings wiring."""

import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
HOOK = os.path.join(ROOT, ".claude", "hooks", "guard_mutations.py")
SETTINGS = os.path.join(ROOT, ".claude", "settings.json")


def run_hook(command):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    return subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True).returncode


@pytest.mark.parametrize("command", [
    "kubectl get pods -n application",
    "kubectl describe deployment sre-metrics-app -n application",
    "kubectl logs deployment/sre-metrics-app -n application --tail=50",
    "kubectl rollout status deployment/sre-metrics-app -n application",
    "kubectl rollout history deployment/sre-metrics-app -n application",
    "kubectl describe chaosresult sre-metrics-app-pod-delete-pod-delete -n litmus",
    "kubectl get workflow -n litmus -o yaml pod-delete-chaos-abc",
    "kubectl logs job/nightly-run -n application",
    "kubectl get pods -l app=secret-store",
    "kubectl describe secret grafana-admin-credentials -n monitoring",
    "kubectl kustomize k8s",
    "cat k8s/grafana-secret.example.yaml",
    "helm lint helm/sre-metrics-app",
    "terraform plan",
    "pytest tests -q",
    "git status",
    "python -m venv .venv",
])
def test_read_only_commands_are_allowed(command):
    assert run_hook(command) == 0


@pytest.mark.parametrize("command", [
    "kubectl delete pod x",
    "kubectl delete namespace monitoring",
    "kubectl -n application scale deployment/sre-metrics-app --replicas=0",
    "kubectl rollout restart deployment/sre-metrics-app -n application",
    "kubectl rollout undo deployment/sre-metrics-app",
    "/usr/local/bin/kubectl apply -f k8s/",
    "C:\\tools\\kubectl.exe delete pod x",
    "sh -c 'kubectl delete pod x'",
    "kubectl get pods && kubectl delete pod x",
    "kube''ctl delete pod x",
    "kubectl --selector 'a;b' delete pod x",
    "kubectl debug node/minikube -it --image=busybox",
    "kubectl proxy --port=8001",
    "helm upgrade sre helm/sre-metrics-app",
    "helm template . --post-renderer ./x.sh",
    "kubectl kustomize k8s --enable-alpha-plugins --enable-exec",
    "kubectl get pods --kubeconfig ./f",
    "terraform destroy -auto-approve",
    "argocd app sync sre-metrics-app-staging",
    "git push origin main",
    "gh workflow run cd.yml",
    "ansible-playbook -i ansible/inventory.ini ansible/runbooks/restart-app.yml",
    "kubectl get secret grafana-admin-credentials -n monitoring -o yaml",
    "kubectl -n monitoring get secrets",
    "kubectl get secret/awx-admin-password -o jsonpath={.data.password}",
    "kubectl get --raw /api/v1/namespaces/monitoring/secrets",
    "kubectl get cm,secret -A",
    "cat k8s/grafana-secret.yaml",
    "grep password k8s/alertmanager-secret.yaml",
    "cat terraform/terraform.tfstate",
    "cat .env",
])
def test_mutating_or_secret_commands_are_blocked(command):
    assert run_hook(command) == 2


def test_unreadable_input_fails_closed():
    result = subprocess.run([sys.executable, HOOK], input="not json", capture_output=True, text=True)
    assert result.returncode == 2


def test_known_limit_runtime_built_commands():
    """Documented limit: a command assembled at run time is invisible to a pattern guard (RBAC covers it)."""
    assert run_hook("K=kubectl; $K delete pod x") == 0


def _bash():
    """The bash that Claude Code would use: Git Bash on Windows (not the WSL launcher in System32)."""
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", shutil.which("bash")):
        if candidate and os.path.exists(candidate) and "system32" not in candidate.lower():
            return candidate
    return None


BASH = _bash()


def _hook_command():
    with open(SETTINGS, encoding="utf-8") as handle:
        settings = json.load(handle)
    return settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]


@pytest.mark.skipif(BASH is None, reason="needs bash (Git Bash on Windows), like Claude Code hooks")
def test_settings_hook_blocks_and_allows():
    env = dict(os.environ, CLAUDE_PROJECT_DIR=os.path.abspath(ROOT))
    for command, expected in (("kubectl -n x delete pod y", 2), ("ls", 0)):
        payload = json.dumps({"tool_input": {"command": command}})
        result = subprocess.run([BASH, "-c", _hook_command()], input=payload, capture_output=True,
                                text=True, env=env)
        assert result.returncode == expected, result.stderr


@pytest.mark.skipif(BASH is None, reason="needs bash (Git Bash on Windows), like Claude Code hooks")
def test_settings_hook_fails_closed_without_python(tmp_path):
    env = {"PATH": str(tmp_path), "CLAUDE_PROJECT_DIR": os.path.abspath(ROOT)}  # no python on PATH
    payload = json.dumps({"tool_input": {"command": "ls"}})
    result = subprocess.run([BASH, "-c", _hook_command()], input=payload, capture_output=True,
                            text=True, env=env)
    assert result.returncode == 2
