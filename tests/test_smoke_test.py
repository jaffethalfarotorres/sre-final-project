"""Unit tests for scripts/smoke_test.py. Every external command is faked: nothing runs, nothing changes."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import smoke_test as st  # noqa: E402


def fake_run(table):
    """Return a fake run() that answers by the first matching command prefix in table."""
    def _run(cmd, timeout=900):
        joined = " ".join(cmd)
        for prefix, answer in table.items():
            if prefix in joined:
                return answer
        return 127, ""
    return _run


def pod(name, ns, phase="Running", ready=True):
    return {"metadata": {"name": name, "namespace": ns},
            "status": {"phase": phase, "containerStatuses": [{"ready": ready}]}}


def test_tail_and_last_line():
    assert st.last_line("a\n\nb\n  \n") == "b"
    assert st.tail("1\n2\n3", lines=2) == "2\n3"


def test_pytest_skips_without_module(monkeypatch):
    monkeypatch.setattr(st, "has_module", lambda name: False)
    assert st.check_pytest().status == "SKIP"


def test_pytest_pass_and_fail(monkeypatch):
    monkeypatch.setattr(st, "has_module", lambda name: True)
    monkeypatch.setattr(st, "run", fake_run({"pytest": (0, "....\n135 passed in 3s\n")}))
    assert st.check_pytest() == st.Result("PASS", "Unit tests (pytest)", "135 passed in 3s", "")
    monkeypatch.setattr(st, "run", fake_run({"pytest": (1, "FAILED tests/x.py\n1 failed\n")}))
    assert st.check_pytest().status == "FAIL"


def test_kustomize_counts_objects(monkeypatch):
    monkeypatch.setattr(st.shutil, "which", lambda name: "/bin/" + name)
    out = "kind: Deployment\n---\nkind: Service\n---\nkind: Deployment\n"
    monkeypatch.setattr(st, "run", fake_run({"kustomize": (0, out)}))
    r = st.check_kustomize()
    assert r.status == "PASS" and "3 objects" in r.detail and "2 Deployments" in r.detail


def test_kustomize_skips_without_kubectl(monkeypatch):
    monkeypatch.setattr(st.shutil, "which", lambda name: None)
    assert st.check_kustomize().status == "SKIP"


def test_promtool_quick_and_no_docker(monkeypatch):
    assert st.check_promtool(quick=True).status == "SKIP"
    monkeypatch.setattr(st, "docker_running", lambda: False)
    assert st.check_promtool(quick=False).status == "SKIP"


def test_promtool_pass(monkeypatch):
    monkeypatch.setattr(st, "docker_running", lambda: True)
    out = ("Checking k8s/config/prometheus/alerts.yml\n  SUCCESS: 6 rules found\n\n"
           "Checking k8s/config/prometheus/slo.yml\n  SUCCESS: 21 rules found\n\n"
           "Unit Testing:  tests/rules/alerts.test.yml\n  SUCCESS\n\n"
           "Unit Testing:  tests/rules/slo.test.yml\n  SUCCESS\n")
    monkeypatch.setattr(st, "run", fake_run({"docker run": (0, out)}))
    r = st.check_promtool(quick=False)
    assert r.status == "PASS" and r.detail == "2 rule files checked, 2 rule test files passed"


def test_context_must_be_minikube(monkeypatch):
    monkeypatch.setattr(st, "run", fake_run({"current-context": (0, "prod-cluster\n")}))
    assert st.check_context().status == "FAIL"
    monkeypatch.setattr(st, "run", fake_run({"current-context": (0, "minikube\n")}))
    assert st.check_context().status == "PASS"


def test_part_b_stops_on_wrong_context(monkeypatch):
    monkeypatch.setattr(st.shutil, "which", lambda name: "/bin/" + name)
    monkeypatch.setattr(st, "run", fake_run({"current-context": (0, "prod-cluster\n")}))
    results = st.part_b()
    assert len(results) == 1 and results[0].status == "FAIL"


@pytest.mark.parametrize("pods,status", [
    ([pod("sre-metrics-app-1", "application"), pod("sre-metrics-app-2", "application"),
      pod("errload", "application", phase="Succeeded"), pod("kube-proxy", "kube-system", phase="Pending")], "PASS"),
    ([pod("sre-metrics-app-1", "application"), pod("sre-metrics-app-2", "application"),
      pod("errload", "application", phase="Failed", ready=False)], "PASS"),
    ([pod("sre-metrics-app-1", "application")], "FAIL"),
    ([pod("sre-metrics-app-1", "application"), pod("sre-metrics-app-2", "application"),
      pod("grafana-1", "monitoring", ready=False)], "FAIL"),
    ([], "FAIL"),
])
def test_pods(monkeypatch, pods, status):
    monkeypatch.setattr(st, "run", fake_run({"get pods": (0, json.dumps({"items": pods}))}))
    assert st.check_pods().status == status


def test_targets(monkeypatch):
    up = {"labels": {"job": "kubernetes-pods"}, "health": "up"}
    down = {"labels": {"job": "blackbox-http"}, "health": "down"}
    body = {"data": {"activeTargets": [up, up]}}
    monkeypatch.setattr(st, "run", fake_run({"--raw": (0, json.dumps(body))}))
    assert st.check_targets().status == "PASS"
    body["data"]["activeTargets"].append(down)
    monkeypatch.setattr(st, "run", fake_run({"--raw": (0, json.dumps(body))}))
    r = st.check_targets()
    assert r.status == "FAIL" and "blackbox-http" in r.detail
    monkeypatch.setattr(st, "run", fake_run({"--raw": (1, "error: no service")}))
    assert st.check_targets().status == "FAIL"


def test_rules(monkeypatch):
    rules = [{"name": n, "state": "inactive"} for n in st.KEY_ALERTS]
    rules[0]["state"] = "firing"
    body = {"data": {"groups": [{"rules": rules}]}}
    monkeypatch.setattr(st, "run", fake_run({"--raw": (0, json.dumps(body))}))
    r = st.check_rules()
    assert r.status == "PASS" and "HighErrorRate" in r.detail
    body["data"]["groups"][0]["rules"] = rules[1:]
    monkeypatch.setattr(st, "run", fake_run({"--raw": (0, json.dumps(body))}))
    assert st.check_rules().status == "FAIL"


def test_markdown_escapes_pipes(monkeypatch):
    monkeypatch.setattr(st, "run", fake_run({"rev-parse": (0, "abc1234\n")}))
    text = st.markdown([st.Result("FAIL", "x", "a | b", "do c")], cluster=False)
    assert "`abc1234`" in text and "a \\| b" in text and "(fix: do c)" in text


def test_main_exit_code_and_report(monkeypatch, tmp_path):
    passing = st.Result("PASS", "x", "ok", "")
    for name in ("check_python", "check_pytest", "check_flake8", "check_kustomize", "check_helm"):
        monkeypatch.setattr(st, name, lambda: passing)
    monkeypatch.setattr(st, "check_promtool", lambda quick: passing)
    monkeypatch.setattr(st, "run", fake_run({"rev-parse": (0, "abc1234\n")}))
    report = tmp_path / "out" / "report.md"
    assert st.main(["--report", str(report)]) == 0
    assert report.read_text(encoding="utf-8").startswith("# Smoke test report")
    monkeypatch.setattr(st, "check_helm", lambda: st.Result("FAIL", "h", "bad", "fix"))
    assert st.main([]) == 1
