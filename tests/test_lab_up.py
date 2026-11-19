"""Unit tests for scripts/lab_up.py. Every external command is faked: nothing installs, deploys or opens."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import lab_up  # noqa: E402


class Args:
    engine = None
    redeploy = False
    no_install = False
    no_browser = True


def test_script_picks_the_platform_version(monkeypatch):
    monkeypatch.setattr(lab_up, "WINDOWS", True)
    cmd = lab_up.script("deploy")
    assert cmd[0] == "powershell" and cmd[-1].endswith("deploy.ps1")
    monkeypatch.setattr(lab_up, "WINDOWS", False)
    assert lab_up.script("dashboards", "--background") == ["bash", os.path.join("scripts", "dashboards.sh"),
                                                           "--background"]


def test_tools_present_needs_no_install(monkeypatch):
    calls = []
    monkeypatch.setattr(lab_up, "refresh_path", lambda: None)
    monkeypatch.setattr(lab_up, "missing_tools", lambda: [])
    monkeypatch.setattr(lab_up, "stream", lambda cmd: calls.append(cmd) or 0)
    assert lab_up.step_tools(Args()) == 0
    assert calls == []


def test_missing_tools_with_no_install_is_a_human_step(monkeypatch):
    monkeypatch.setattr(lab_up, "refresh_path", lambda: None)
    monkeypatch.setattr(lab_up, "missing_tools", lambda: ["minikube"])
    args = Args()
    args.no_install = True
    assert lab_up.step_tools(args) == 2


def test_kit_runs_then_tools_are_found(monkeypatch):
    state = {"missing": ["minikube", "kubectl"]}
    calls = []

    def fake_stream(cmd):
        calls.append(cmd)
        state["missing"] = []
        return 0
    monkeypatch.setattr(lab_up, "refresh_path", lambda: None)
    monkeypatch.setattr(lab_up, "missing_tools", lambda: list(state["missing"]))
    monkeypatch.setattr(lab_up, "stream", fake_stream)
    assert lab_up.step_tools(Args()) == 0
    assert any("install-tools" in part for part in calls[0])


def test_missing_container_engine_after_kit_is_a_human_step(monkeypatch):
    monkeypatch.setattr(lab_up, "refresh_path", lambda: None)
    monkeypatch.setattr(lab_up, "missing_tools", lambda: ["docker"])
    monkeypatch.setattr(lab_up, "stream", lambda cmd: 0)
    assert lab_up.step_tools(Args()) == 2


def test_deploy_is_skipped_when_healthy(monkeypatch):
    calls = []
    monkeypatch.setattr(lab_up, "lab_healthy", lambda: True)
    monkeypatch.setattr(lab_up, "stream", lambda cmd: calls.append(cmd) or 0)
    assert lab_up.step_deploy(Args()) == 0
    assert calls == []
    args = Args()
    args.redeploy = True
    assert lab_up.step_deploy(args) == 0
    assert len(calls) == 1


def test_deploy_failure_is_reported(monkeypatch):
    monkeypatch.setattr(lab_up, "lab_healthy", lambda: False)
    monkeypatch.setattr(lab_up, "stream", lambda cmd: 1)
    assert lab_up.step_deploy(Args()) == 1


def test_drill_needs_a_running_lab(monkeypatch):
    monkeypatch.setattr(lab_up, "lab_healthy", lambda: False)
    assert lab_up.drill() == 1


def test_main_runs_steps_in_order_and_stops_on_failure(monkeypatch):
    order = []
    monkeypatch.setattr(lab_up, "refresh_path", lambda: None)
    monkeypatch.setattr(lab_up, "step_tools", lambda a: order.append("tools") or 0)
    monkeypatch.setattr(lab_up, "step_deploy", lambda a: order.append("deploy") or 1)
    monkeypatch.setattr(lab_up, "step_connect", lambda a: order.append("connect") or 0)
    monkeypatch.setattr(lab_up, "step_verify", lambda: order.append("verify") or 0)
    assert lab_up.main(["--no-browser"]) == 1
    assert order == ["tools", "deploy"]


def test_refresh_path_keeps_existing_entries(monkeypatch):
    monkeypatch.setenv("PATH", os.pathsep.join(["/a", "/b"]))
    lab_up.refresh_path()
    parts = os.environ["PATH"].split(os.pathsep)
    assert parts[:2] == ["/a", "/b"] and len(parts) == len(set(parts))
