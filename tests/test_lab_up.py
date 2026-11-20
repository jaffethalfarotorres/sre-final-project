"""Unit tests for scripts/lab_up.py. Every external command is faked: nothing installs, deploys or opens."""

import json
import os
import sys
import time
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import lab_up  # noqa: E402


def args(**kw):
    ns = types.SimpleNamespace(engine=None, redeploy=False, no_install=False, no_browser=True, wait=3, tour=None,
                               drill=False, stop=False, status=False, worker=False, mode=None)
    ns.__dict__.update(kw)
    return ns


@pytest.fixture(autouse=True)
def lab_dir(tmp_path, monkeypatch):
    """Keep the status, state, pid and log files of every test in a temporary folder."""
    folder = str(tmp_path / ".lab")
    monkeypatch.setattr(lab_up, "LAB_DIR", folder)
    monkeypatch.setattr(lab_up, "STATUS_FILE", os.path.join(folder, "status.json"))
    monkeypatch.setattr(lab_up, "STATE_FILE", os.path.join(folder, "state.json"))
    monkeypatch.setattr(lab_up, "PID_FILE", os.path.join(folder, "lab_up.pid"))
    monkeypatch.setattr(lab_up, "TUNNEL_PID_FILE", os.path.join(folder, "tunnels.pid"))
    monkeypatch.setattr(lab_up, "LOG_FILE", os.path.join(folder, "lab_up.log"))
    monkeypatch.setattr(lab_up.time, "sleep", lambda seconds: None)
    return folder


# ---------------------------------------------------------------------------------------------- basics
def test_result_line_and_exit_codes():
    assert lab_up.result_line(0, "all good") == "LAB_UP RESULT: DONE - all good"
    assert lab_up.result_line(3, "x").startswith("LAB_UP RESULT: NOT_FINISHED")
    assert lab_up.result_line(2, "x").startswith("LAB_UP RESULT: NEEDS_HUMAN")
    assert lab_up.result_line(1, "x").startswith("LAB_UP RESULT: FAILED")


def test_script_picks_the_platform_version(monkeypatch):
    monkeypatch.setattr(lab_up, "WINDOWS", True)
    cmd = lab_up.script("deploy")
    assert cmd[0] == "powershell" and cmd[-1].endswith("deploy.ps1")
    monkeypatch.setattr(lab_up, "WINDOWS", False)
    assert lab_up.script("dashboards", "--background") == ["bash", os.path.join("scripts", "dashboards.sh"),
                                                           "--background"]


def test_pid_alive():
    assert lab_up.pid_alive(os.getpid())
    assert not lab_up.pid_alive(0) and not lab_up.pid_alive(None) and not lab_up.pid_alive("x")


def test_refresh_path_keeps_existing_entries(monkeypatch):
    monkeypatch.setenv("PATH", os.pathsep.join(["/a", "/b"]))
    lab_up.refresh_path()
    parts = os.environ["PATH"].split(os.pathsep)
    assert parts[:2] == ["/a", "/b"] and len(parts) == len(set(parts))


def test_status_file_round_trip():
    lab_up.set_status(state="running", step="tools")
    lab_up.set_status(step="engine")
    status = lab_up.read_status()
    assert status["state"] == "running" and status["step"] == "engine" and status["updated_at"]


def test_status_exit_mapping():
    assert lab_up.status_exit({"state": "done"})[0] == 0
    assert lab_up.status_exit({"state": "needs_human", "message": "open Docker"})[0] == 2
    assert "open Docker" in lab_up.status_exit({"state": "needs_human", "message": "open Docker"})[1]
    assert lab_up.status_exit({"state": "failed", "message": "boom"})[0] == 1
    assert lab_up.status_exit({"state": "running"}) is None


# ---------------------------------------------------------------------------------------------- the steps
def test_tools_present_needs_no_install(monkeypatch):
    monkeypatch.setattr(lab_up, "refresh_path", lambda: None)
    monkeypatch.setattr(lab_up, "missing_tools", lambda: [])
    assert lab_up.step_tools(args()) == (lab_up.OK, "")


def test_missing_tools_with_no_install_is_a_human_step(monkeypatch):
    monkeypatch.setattr(lab_up, "refresh_path", lambda: None)
    monkeypatch.setattr(lab_up, "missing_tools", lambda: ["minikube"])
    kind, message = lab_up.step_tools(args(no_install=True))
    assert kind == lab_up.HUMAN and "minikube" in message


def test_kit_runs_then_tools_are_found(monkeypatch):
    state = {"missing": ["minikube", "kubectl"]}
    calls = []

    def fake_stream(cmd, timeout=None):
        calls.append(cmd)
        state["missing"] = []
        return 0
    monkeypatch.setattr(lab_up, "refresh_path", lambda: None)
    monkeypatch.setattr(lab_up, "missing_tools", lambda: list(state["missing"]))
    monkeypatch.setattr(lab_up, "stream", fake_stream)
    assert lab_up.step_tools(args()) == (lab_up.OK, "")
    assert any("install-tools" in part for part in calls[0])


def test_missing_container_engine_after_kit_is_a_human_step(monkeypatch):
    monkeypatch.setattr(lab_up, "refresh_path", lambda: None)
    monkeypatch.setattr(lab_up, "missing_tools", lambda: ["docker"])
    monkeypatch.setattr(lab_up, "stream", lambda cmd, timeout=None: 0)
    kind, message = lab_up.step_tools(args())
    assert kind == lab_up.HUMAN and "container engine" in message


def test_engine_running_is_done(monkeypatch):
    monkeypatch.setattr(lab_up, "engine_ok", lambda: True)
    assert lab_up.step_engine(args()) == (lab_up.OK, "")


def test_engine_down_without_a_starter_is_a_human_step(monkeypatch):
    monkeypatch.setattr(lab_up, "engine_ok", lambda: False)
    monkeypatch.setattr(lab_up, "engine_starter", lambda: None)
    kind, message = lab_up.step_engine(args())
    assert kind == lab_up.HUMAN and "not running" in message


def test_engine_is_started_and_awaited(monkeypatch):
    answers = iter([False, False, True])
    started = []
    monkeypatch.setattr(lab_up, "engine_ok", lambda: next(answers))
    monkeypatch.setattr(lab_up, "engine_starter", lambda: ["start-engine"])
    monkeypatch.setattr(lab_up.subprocess, "Popen", lambda cmd, **kw: started.append(cmd))
    assert lab_up.step_engine(args()) == (lab_up.OK, "")
    assert started == [["start-engine"]]


def test_engine_that_never_starts_is_a_human_step(monkeypatch):
    clock = iter(range(0, 10000, 100))
    monkeypatch.setattr(lab_up, "engine_ok", lambda: False)
    monkeypatch.setattr(lab_up, "engine_starter", lambda: ["start-engine"])
    monkeypatch.setattr(lab_up.subprocess, "Popen", lambda cmd, **kw: None)
    monkeypatch.setattr(lab_up.time, "time", lambda: next(clock))
    kind, message = lab_up.step_engine(args())
    assert kind == lab_up.HUMAN and "did not start" in message


def test_cluster_already_running_is_skipped(monkeypatch):
    monkeypatch.setattr(lab_up, "run", lambda cmd, timeout=120, input_text=None: (0, "Running\n"))
    monkeypatch.setattr(lab_up, "stream", lambda *a, **k: pytest.fail("must not start minikube"))
    assert lab_up.step_cluster(args()) == (lab_up.OK, "")


def test_cluster_start_success_and_failure(monkeypatch):
    monkeypatch.setattr(lab_up, "run", lambda cmd, timeout=120, input_text=None: (0, "Stopped\n"))
    monkeypatch.setattr(lab_up, "stream", lambda cmd, timeout=None: 0)
    assert lab_up.step_cluster(args()) == (lab_up.OK, "")
    monkeypatch.setattr(lab_up, "stream", lambda cmd, timeout=None: 1)
    assert lab_up.step_cluster(args())[0] == lab_up.FAIL


def test_image_is_skipped_when_unchanged(monkeypatch):
    lab_up.write_json(lab_up.STATE_FILE, {"image_hash": "h1"})
    monkeypatch.setattr(lab_up, "source_hash", lambda: "h1")
    listing = "docker.io/library/" + lab_up.IMAGE
    monkeypatch.setattr(lab_up, "run", lambda cmd, timeout=120, input_text=None: (0, listing))
    monkeypatch.setattr(lab_up, "stream", lambda *a, **k: pytest.fail("must not rebuild"))
    assert lab_up.step_image(args()) == (lab_up.OK, "")


def test_image_is_built_when_changed_and_flags_a_restart(monkeypatch):
    lab_up.write_json(lab_up.STATE_FILE, {"image_hash": "old"})
    built = []
    monkeypatch.setattr(lab_up, "source_hash", lambda: "new")
    monkeypatch.setattr(lab_up, "run", lambda cmd, timeout=120, input_text=None: (0, ""))
    monkeypatch.setattr(lab_up, "stream", lambda cmd, timeout=None, collect=None: built.append(cmd) or 0)
    assert lab_up.step_image(args()) == (lab_up.OK, "")
    state = lab_up.read_json(lab_up.STATE_FILE, {})
    assert built and state["image_hash"] == "new" and state["restart_needed"] is True


def test_image_build_that_prints_an_error_is_a_failure_even_with_exit_code_zero(monkeypatch):
    lab_up.write_json(lab_up.STATE_FILE, {"image_hash": "old"})
    monkeypatch.setattr(lab_up, "source_hash", lambda: "new")
    monkeypatch.setattr(lab_up, "run", lambda cmd, timeout=120, input_text=None: (0, ""))

    def fake_stream(cmd, timeout=None, collect=None):
        collect.append("error: failed to solve: dockerfile parse error on line 3")
        return 0
    monkeypatch.setattr(lab_up, "stream", fake_stream)
    kind, message = lab_up.step_image(args())
    assert kind == lab_up.FAIL and "failed to solve" in message
    assert lab_up.read_json(lab_up.STATE_FILE, {})["image_hash"] == "old"  # nothing was recorded as built


def test_source_hash_changes_with_the_source(tmp_path, monkeypatch):
    (tmp_path / "app").mkdir()
    (tmp_path / "Dockerfile").write_text("FROM x\n")
    (tmp_path / "app" / "app.py").write_text("print(1)\n")
    monkeypatch.setattr(lab_up, "ROOT", str(tmp_path))
    first = lab_up.source_hash()
    assert first == lab_up.source_hash()
    (tmp_path / "app" / "app.py").write_text("print(2)\n")
    assert lab_up.source_hash() != first


def test_deploy_restarts_the_app_only_after_a_new_image(monkeypatch):
    commands = []
    monkeypatch.setattr(lab_up, "ensure_secret_files", lambda: None)
    monkeypatch.setattr(lab_up, "run", lambda cmd, timeout=120, input_text=None: (0, "namespace: yaml"))
    monkeypatch.setattr(lab_up, "stream", lambda cmd, timeout=None: commands.append(cmd) or 0)
    assert lab_up.step_deploy(args()) == (lab_up.OK, "")
    assert not any("restart" in c for c in commands)
    lab_up.write_json(lab_up.STATE_FILE, {"restart_needed": True})
    assert lab_up.step_deploy(args()) == (lab_up.OK, "")
    assert any("restart" in c for c in commands)
    assert lab_up.read_json(lab_up.STATE_FILE, {})["restart_needed"] is False


def test_deploy_failure_is_reported(monkeypatch):
    monkeypatch.setattr(lab_up, "ensure_secret_files", lambda: None)
    monkeypatch.setattr(lab_up, "run", lambda cmd, timeout=120, input_text=None: (0, ""))
    monkeypatch.setattr(lab_up, "stream", lambda cmd, timeout=None: 1)
    assert lab_up.step_deploy(args())[0] == lab_up.FAIL


def test_secret_files_are_created_from_the_examples(tmp_path, monkeypatch):
    (tmp_path / "k8s").mkdir()
    (tmp_path / "k8s" / "alertmanager-secret.example.yaml").write_text("a")
    (tmp_path / "k8s" / "grafana-secret.example.yaml").write_text('admin-password: "admin"')
    monkeypatch.setattr(lab_up, "ROOT", str(tmp_path))
    lab_up.ensure_secret_files()
    assert (tmp_path / "k8s" / "grafana-secret.yaml").read_text() == 'admin-password: "admin"'
    (tmp_path / "k8s" / "grafana-secret.yaml").write_text("mine")
    lab_up.ensure_secret_files()
    assert (tmp_path / "k8s" / "grafana-secret.yaml").read_text() == "mine"


# ---------------------------------------------------------------------------------------------- the worker
def fake_steps(monkeypatch, outcomes):
    monkeypatch.setattr(lab_up, "STEPS", [(key, key.upper()) for key in outcomes])
    for key, outcome in outcomes.items():
        monkeypatch.setattr(lab_up, "step_" + key, (lambda o: lambda a: o)(outcome), raising=False)


def test_worker_runs_every_step_and_ends_done(monkeypatch):
    fake_steps(monkeypatch, {"a": (lab_up.OK, ""), "b": (lab_up.OK, "")})
    assert lab_up.run_worker(args()) == 0
    status = lab_up.read_status()
    assert status["state"] == "done" and status["percent"] == 100 and status["pid"] == os.getpid()


def test_worker_records_how_long_each_step_took(monkeypatch):
    fake_steps(monkeypatch, {"a": (lab_up.OK, ""), "b": (lab_up.OK, "")})
    assert lab_up.run_worker(args()) == 0
    status = lab_up.read_status()
    assert set(status["step_seconds"]) == {"a", "b"} and status["run_seconds"] >= 0


def test_worker_stops_at_a_human_step(monkeypatch):
    fake_steps(monkeypatch, {"a": (lab_up.OK, ""), "b": (lab_up.HUMAN, "open Docker Desktop"),
                             "c": (lab_up.OK, "")})
    assert lab_up.run_worker(args()) == 2
    status = lab_up.read_status()
    assert status["state"] == "needs_human" and "open Docker Desktop" in status["next_action"]
    assert status["step"] == "b"


def test_worker_turns_an_unexpected_error_into_a_failed_status(monkeypatch):
    def boom(a):
        raise RuntimeError("disk full")
    monkeypatch.setattr(lab_up, "STEPS", [("a", "A")])
    monkeypatch.setattr(lab_up, "step_a", boom, raising=False)
    assert lab_up.run_worker(args()) == 1
    assert "disk full" in lab_up.read_status()["message"]


# ---------------------------------------------------------------------------------------------- following a worker
def test_poll_reports_done_at_once(monkeypatch):
    lab_up.set_status(state="done")
    assert lab_up.poll(args(), 5) == 0


def test_poll_gives_not_finished_when_the_wait_ends(monkeypatch):
    lab_up.set_status(state="running", pid=os.getpid(), step="cluster", step_index=3, title="Start Kubernetes")
    assert lab_up.poll(args(), 0) == 3


def test_poll_restarts_a_dead_worker_once(monkeypatch):
    lab_up.set_status(state="running", pid=999999, step="image", step_index=4, title="Build")
    monkeypatch.setattr(lab_up, "SPAWN_GRACE", 0)
    spawned = []
    monkeypatch.setattr(lab_up, "spawn_worker", lambda a: spawned.append(1) or lab_up.set_status(state="done"))
    assert lab_up.poll(args(), 30) == 0
    assert spawned == [1]


def test_poll_gives_up_when_the_worker_keeps_dying(monkeypatch):
    lab_up.set_status(state="running", pid=999999)
    monkeypatch.setattr(lab_up, "SPAWN_GRACE", 0)
    monkeypatch.setattr(lab_up, "spawn_worker", lambda a: lab_up.set_status(state="running", pid=999999))
    assert lab_up.poll(args(), 30) == 1


def test_background_call_does_not_trust_an_old_done_status(monkeypatch):
    lab_up.set_status(state="done", pid=999999)
    spawned = []

    def fake_spawn(a):
        spawned.append(1)
        lab_up.set_status(state="needs_human", message="open Docker")
    monkeypatch.setattr(lab_up, "spawn_worker", fake_spawn)
    assert lab_up.cmd_up(args(), interactive=False) == 2
    assert spawned == [1]


def test_status_command(capsys):
    assert lab_up.cmd_status() == 1
    assert "never started" in capsys.readouterr().out
    lab_up.set_status(state="done", message="all good")
    assert lab_up.cmd_status() == 0
    assert "LAB_UP RESULT: DONE" in capsys.readouterr().out


# ---------------------------------------------------------------------------------------------- the tunnels
class FakeProc:
    def __init__(self, running=True):
        self.running = running

    def poll(self):
        return None if self.running else 1


def test_tunnel_pass_starts_missing_forwards_and_restarts_ended_ones():
    started = []

    def make(forward):
        started.append(forward)
        return FakeProc()
    procs = {}
    lab_up.tunnel_pass(procs, make)
    assert started == lab_up.FORWARDS and len(procs) == len(lab_up.FORWARDS)
    lab_up.tunnel_pass(procs, make)  # all running: nothing new
    assert len(started) == len(lab_up.FORWARDS)
    procs[lab_up.FORWARDS[1]] = FakeProc(running=False)  # the pod behind it was replaced and the forward ended
    lab_up.tunnel_pass(procs, make)
    assert started[-1] == lab_up.FORWARDS[1] and len(started) == len(lab_up.FORWARDS) + 1


def test_supervisor_alive_reads_the_pid_file():
    os.makedirs(lab_up.LAB_DIR, exist_ok=True)
    assert not lab_up.supervisor_alive()
    with open(lab_up.TUNNEL_PID_FILE, "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    assert lab_up.supervisor_alive()
    with open(lab_up.TUNNEL_PID_FILE, "w", encoding="utf-8") as handle:
        handle.write("999999")
    assert not lab_up.supervisor_alive()


def test_connect_is_skipped_when_the_keeper_runs_and_pages_answer(monkeypatch):
    monkeypatch.setattr(lab_up, "supervisor_alive", lambda: True)
    monkeypatch.setattr(lab_up, "tunnels_up", lambda: True)
    monkeypatch.setattr(lab_up, "spawn_detached", lambda *a, **k: pytest.fail("must not start another keeper"))
    assert lab_up.step_connect(args()) == (lab_up.OK, "")


def test_connect_starts_the_keeper_and_waits_for_the_pages(monkeypatch):
    answers = iter([False, False, True])
    spawned = []
    monkeypatch.setattr(lab_up, "supervisor_alive", lambda: False)
    monkeypatch.setattr(lab_up, "tunnels_up", lambda: next(answers))
    monkeypatch.setattr(lab_up, "spawn_detached", lambda flag, a=None: spawned.append(flag))
    assert lab_up.step_connect(args()) == (lab_up.OK, "")
    assert spawned == ["--tunnels"]


def test_connect_fails_clearly_when_the_pages_never_open(monkeypatch):
    clock = iter(range(0, 100000, 20))
    monkeypatch.setattr(lab_up, "supervisor_alive", lambda: True)
    monkeypatch.setattr(lab_up, "tunnels_up", lambda: False)
    monkeypatch.setattr(lab_up.time, "time", lambda: next(clock))
    kind, message = lab_up.step_connect(args())
    assert kind == lab_up.FAIL and "localhost" in message


def test_ensure_tunnels_starts_the_keeper_when_missing(monkeypatch):
    spawned = []
    answers = iter([False, False, True])
    monkeypatch.setattr(lab_up, "supervisor_alive", lambda: False)
    monkeypatch.setattr(lab_up, "tunnels_up", lambda: next(answers))
    monkeypatch.setattr(lab_up, "spawn_detached", lambda flag, a=None: spawned.append(flag))
    assert lab_up.ensure_tunnels(30) is True and spawned == ["--tunnels"]


def test_ensure_tunnels_does_nothing_when_everything_answers(monkeypatch):
    monkeypatch.setattr(lab_up, "supervisor_alive", lambda: True)
    monkeypatch.setattr(lab_up, "tunnels_up", lambda: True)
    monkeypatch.setattr(lab_up, "spawn_detached", lambda *a, **k: pytest.fail("no keeper needed"))
    assert lab_up.ensure_tunnels() is True


def test_kill_stale_forwards_never_raises(monkeypatch):
    def boom(*a, **k):
        raise OSError("no shell")
    monkeypatch.setattr(lab_up.subprocess, "run", boom)
    lab_up.kill_stale_forwards()


def test_tour_stop_repairs_the_tunnels_before_opening_a_page(monkeypatch):
    repaired = []
    monkeypatch.setattr(lab_up, "tunnels_up", lambda: False)
    monkeypatch.setattr(lab_up, "ensure_tunnels", lambda wait=45: repaired.append(wait))
    monkeypatch.setitem(lab_up.TOUR[0], "ready", lambda: True)
    assert lab_up.cmd_tour(args(tour=1)) == 0
    assert repaired


# ---------------------------------------------------------------------------------------------- tour and drill
def test_tour_index_and_bad_stop(capsys):
    assert lab_up.cmd_tour(args(tour=0)) == 0
    assert "Nimbus Store" in capsys.readouterr().out
    assert lab_up.cmd_tour(args(tour=99)) == 1


def test_tour_stop_opens_the_page_when_ready(monkeypatch):
    opened = []
    monkeypatch.setitem(lab_up.TOUR[1], "ready", lambda: True)
    monkeypatch.setattr(lab_up.webbrowser, "open", lambda url: opened.append(url))
    assert lab_up.cmd_tour(args(tour=2, no_browser=False)) == 0
    assert opened == [lab_up.TOUR[1]["url"]]


def test_tour_stop_that_is_not_ready_says_so(monkeypatch):
    monkeypatch.setitem(lab_up.TOUR[0], "ready", lambda: False)
    assert lab_up.cmd_tour(args(tour=1, wait=0)) == 3


def test_tour_has_seven_stops_and_the_optional_ones_always_pass():
    assert len(lab_up.TOUR) == 7
    assert lab_up.TOUR[5]["ready"]() and lab_up.TOUR[6]["ready"]()


def test_drill_needs_a_running_lab(monkeypatch):
    monkeypatch.setattr(lab_up, "lab_healthy", lambda: False)
    assert lab_up.cmd_drill(args()) == 1


def test_drill_reports_the_alert_when_it_fires(monkeypatch):
    monkeypatch.setattr(lab_up, "lab_healthy", lambda: True)
    monkeypatch.setattr(lab_up, "drill_pod_running", lambda: True)
    monkeypatch.setattr(lab_up, "firing_alerts", lambda: {"HighErrorRate", "AlwaysFiringDemoAlert"})
    monkeypatch.setattr(lab_up, "phone_alerts_on", lambda: False)
    assert lab_up.cmd_drill(args()) == 0


def test_drill_keeps_watching_until_the_wait_ends(monkeypatch):
    monkeypatch.setattr(lab_up, "lab_healthy", lambda: True)
    monkeypatch.setattr(lab_up, "drill_pod_running", lambda: True)
    monkeypatch.setattr(lab_up, "firing_alerts", lambda: set())
    assert lab_up.cmd_drill(args(wait=0)) == 3


def test_drill_starts_a_new_pod_when_none_is_running(monkeypatch):
    commands = []
    monkeypatch.setattr(lab_up, "lab_healthy", lambda: True)
    monkeypatch.setattr(lab_up, "drill_pod_running", lambda: False)
    monkeypatch.setattr(lab_up, "run", lambda cmd, timeout=120, input_text=None: commands.append(cmd) or (0, ""))
    monkeypatch.setattr(lab_up, "firing_alerts", lambda: {"HighErrorRate"})
    monkeypatch.setattr(lab_up, "phone_alerts_on", lambda: True)
    assert lab_up.cmd_drill(args()) == 0
    assert any("apply" in c for c in commands)


def test_targets_up_reads_the_prometheus_answer(monkeypatch):
    body = {"data": {"activeTargets": [{"health": "up"}, {"health": "up"}]}}
    monkeypatch.setattr(lab_up, "http_get", lambda url, timeout=5: (200, json.dumps(body)))
    assert lab_up.targets_up()
    body["data"]["activeTargets"].append({"health": "down"})
    assert not lab_up.targets_up()
    monkeypatch.setattr(lab_up, "http_get", lambda url, timeout=5: (0, ""))
    assert not lab_up.targets_up()


# ---------------------------------------------------------------------------------------------- running commands
def test_stream_does_not_wait_for_background_children(capsys):
    """The tunnels outlive the script that starts them and keep its output pipe open: stream must not hang."""
    src = ("import subprocess, sys; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(8)']); "
           "print('parent done')")
    started = time.time()
    code = lab_up.stream([sys.executable, "-c", src], timeout=60)
    assert code == 0 and time.time() - started < 6
    assert "parent done" in capsys.readouterr().out


def test_stream_stops_a_command_that_runs_too_long():
    started = time.time()
    code = lab_up.stream([sys.executable, "-c", "import time; time.sleep(30)"], timeout=2)
    assert code == 124 and time.time() - started < 15
