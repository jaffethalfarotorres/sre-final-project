#!/usr/bin/env python3
"""
Bring the whole SRE lab up with one command, then show that every tool is running and connected.

    Windows (PowerShell):  python scripts\\lab_up.py
    Mac or Linux:          python3 scripts/lab_up.py
    (it works from any folder, for example: python sre-final-project/scripts/lab_up.py)

The setup is a series of steps, and every step skips itself when it is already done, so you can run the same
command again at any time, and it continues where it stopped:
  1 tools      install what is missing (setup kit: scripts/install-tools.*)
  2 engine     make sure the container engine (Docker Desktop, Rancher Desktop, Colima) is running
  3 cluster    start Minikube (Kubernetes on your laptop)
  4 image      build the shop's image (only when its source changed)
  5 deploy     deploy Nimbus Store and the monitoring tools (kubectl apply -k k8s)
  6 ready      wait until every pod is ready
  7 connect    open the tunnels to the web pages (localhost:3000, 9090, 9093, 16686, 5000) and keep them open: a small
               keeper process starts a tunnel again whenever its pod is replaced
  8 verify     check that everything is connected, then print a map of how the tools talk to each other

How it runs:
  In a terminal (a person): it runs in the foreground and shows everything live.
  Started by an AI agent (no terminal): it runs the steps in a background worker that survives the call, waits up to
  --wait seconds (default 100) printing progress, and then ends with one clear last line. Run the same command again
  until that line says DONE. The agent never has to wait 40 minutes inside one call.

The last line is always one of (and the exit code says the same):
  LAB_UP RESULT: DONE ...          (exit 0)  everything is running and connected
  LAB_UP RESULT: NOT_FINISHED ...  (exit 3)  still working: run exactly the same command again
  LAB_UP RESULT: NEEDS_HUMAN ...   (exit 2)  a person must do one thing (the line says what), then run it again
  LAB_UP RESULT: FAILED ...        (exit 1)  something broke (the line says what; details in .lab/lab_up.log)

Other actions (all end with the same kind of last line):
  --status      read-only and instant: which step it is on, the next action, the last log lines
  --tour N      a fixed, numbered tour of the tools (1 shop, 2 Prometheus, 3 Grafana, 4 Jaeger, 5 Alertmanager,
                6 phone alerts, 7 alert drill): opens the page, says what to notice, waits until it is ready
  --drill       break the shop on purpose and follow the alert (HighErrorRate fires after about 150 seconds)
  --stop        close the tunnels and stop Minikube (your data stays; run lab_up.py again to resume)

Options: --engine rancher|docker (container engine for the setup kit, Windows), --redeploy (rebuild the image and
restart the app), --no-install (never run the setup kit), --no-browser, --wait SECONDS, --mode foreground|detached.
Progress and status are written to .lab/lab_up.log and .lab/status.json (Git ignores .lab/).
Only the Python standard library is used.
"""

import argparse
import atexit
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import smoke_test  # noqa: E402

WINDOWS = platform.system() == "Windows"
MAC = platform.system() == "Darwin"
PY = "python" if WINDOWS else "python3"
CORE_TOOLS = ("docker", "minikube", "kubectl")
IMAGE = "sre-metrics-app:1.0.0"
DEPLOY_NAMESPACES = ("application", "monitoring", "opentelemetry")
ENGINE_WAIT_SECONDS = 240
READY_WAIT_SECONDS = 900
VERIFY_WAIT_SECONDS = 300
DEFAULT_WAIT = 100
SPAWN_GRACE = 25  # seconds a freshly started worker may take to write its first status
LAB_DIR = os.path.join(ROOT, ".lab")
LOG_FILE = os.path.join(LAB_DIR, "lab_up.log")
STATUS_FILE = os.path.join(LAB_DIR, "status.json")
STATE_FILE = os.path.join(LAB_DIR, "state.json")
PID_FILE = os.path.join(LAB_DIR, "lab_up.pid")
TUNNEL_PID_FILE = os.path.join(LAB_DIR, "tunnels.pid")
TUNNEL_WAIT_SECONDS = 45

FORWARDS = [
    ("application", "service/sre-metrics-app", "5000:5000"),
    ("monitoring", "service/grafana", "3000:3000"),
    ("monitoring", "service/prometheus", "9090:9090"),
    ("monitoring", "service/alertmanager", "9093:9093"),
    ("opentelemetry", "service/jaeger", "16686:16686"),
]
TUNNEL_CHECKS = ["http://localhost:5000/", "http://localhost:3000/api/health", "http://localhost:9090/-/ready",
                 "http://localhost:9093/-/ready", "http://localhost:16686/"]
OK, HUMAN, FAIL = "ok", "human", "fail"
STEPS = [
    ("tools", "Install the missing tools"),
    ("engine", "Start the container engine"),
    ("cluster", "Start Kubernetes (Minikube)"),
    ("image", "Build the shop's image"),
    ("deploy", "Deploy the shop and the monitoring tools"),
    ("ready", "Wait until every pod is ready"),
    ("connect", "Open the tunnels to the web pages"),
    ("verify", "Check that everything is connected"),
]
PAGES = [
    ("Nimbus Store (the shop)", "http://localhost:5000"),
    ("Prometheus (metrics, targets)", "http://localhost:9090/targets"),
    ("Grafana (dashboards, logs)", "http://localhost:3000"),
    ("Jaeger (traces)", "http://localhost:16686"),
    ("Alertmanager (alerts)", "http://localhost:9093"),
]
MAP = r"""
How the tools are connected (everything runs inside Minikube on this laptop):

  traffic-generator --> Nimbus Store (2 copies, :5000)
     |-- metrics /metrics ----------> Prometheus (:9090) --> alert rules --> Alertmanager (:9093)
     |                                                                         |--> your phone (ntfy)
     |                                                                         '--> Slack / email (optional)
     |-- traces (OpenTelemetry) ----> OTel Collector --> Jaeger (:16686)
     '-- JSON logs -----------------> Loki
  blackbox exporter --> probes the app from outside --> Prometheus
  Grafana (:3000) reads Prometheus, Loki and Jaeger: one place to see metrics, logs and traces together.
"""
RESULT_WORDS = {0: "DONE", 1: "FAILED", 2: "NEEDS_HUMAN", 3: "NOT_FINISHED"}


# ---------------------------------------------------------------------------------------------- output and log
class Tee:
    """Write everything to the screen and to .lab/lab_up.log, line by line, so an AI agent that loses the output
    can still read the progress from the log file."""

    def __init__(self, screen, path, tty=False):
        self.screen = screen
        self.tty = tty
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.log = open(path, "a", encoding="utf-8")

    def isatty(self):
        return self.tty

    def write(self, text):
        for target in (self.screen, self.log):
            try:
                target.write(text)
                target.flush()
            except (OSError, ValueError, UnicodeEncodeError, AttributeError):
                pass
        return len(text)

    def flush(self):
        for target in (self.screen, self.log):
            try:
                target.flush()
            except (OSError, ValueError, AttributeError):
                pass


def banner(text):
    print("\n" + "=" * 78 + "\n  " + text + "\n" + "=" * 78, flush=True)


def result_line(code, message):
    return "LAB_UP RESULT: {} - {}".format(RESULT_WORDS.get(code, "FAILED"), message)


def finish(code, message):
    print("\n" + result_line(code, message), flush=True)
    return code


# ---------------------------------------------------------------------------------------------- state files
def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else default
    except (OSError, ValueError):
        return default


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    os.replace(tmp, path)


def read_status():
    return read_json(STATUS_FILE, {})


def set_status(**fields):
    status = read_status()
    status.update(fields)
    status["updated_at"] = now()
    write_json(STATUS_FILE, status)
    return status


def pid_alive(pid):
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if WINDOWS:
        import ctypes
        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = kernel.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel.CloseHandle(handle)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------------------------- running commands
def popen_kwargs():
    """Children of a background worker must not open console windows on Windows."""
    return {"creationflags": 0x08000000} if WINDOWS else {}


def kill_tree(proc):
    try:
        if WINDOWS:
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=30)
        else:
            proc.kill()
    except (OSError, subprocess.SubprocessError):
        pass


def run(cmd, timeout=120, input_text=None):
    """Run a command quietly in the repository root. Returns (exit code, output); 127 not found, 124 timeout."""
    try:
        proc = subprocess.run(cmd, cwd=ROOT, input=input_text, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              universal_newlines=True, encoding="utf-8", errors="replace", timeout=timeout,
                              **popen_kwargs())
        return proc.returncode, proc.stdout or ""
    except FileNotFoundError:
        return 127, ""
    except subprocess.TimeoutExpired:
        return 124, "timed out after {} s".format(timeout)


def stream(cmd, timeout=None, collect=None):
    """Run a command and show its output live (and in the log). Returns the exit code (124 on timeout).
    When `collect` is a list, every output line is also appended to it."""
    print("> " + " ".join(cmd), flush=True)
    try:
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True, encoding="utf-8", errors="replace", bufsize=1,
                                **popen_kwargs())
    except FileNotFoundError:
        print("  not found: " + cmd[0])
        return 127

    def pump():
        try:
            for line in proc.stdout:
                sys.stdout.write(line)
                if collect is not None:
                    collect.append(line)
        except (OSError, ValueError):
            pass

    reader = threading.Thread(target=pump, daemon=True)
    reader.start()
    try:
        code = proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        reader.join(timeout=3)
        print("  stopped: no answer after {} s".format(timeout))
        return 124
    # A command may leave background children behind on purpose (the tunnels do). They inherit the output pipe and
    # keep it open, so wait for the command itself, then only briefly for its last lines, never for the children.
    reader.join(timeout=3)
    return code


def script(name, *args):
    """The Windows (.ps1) or Mac/Linux (.sh) version of a lab script, as a command list."""
    if WINDOWS:
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                os.path.join("scripts", name + ".ps1")] + list(args)
    return ["bash", os.path.join("scripts", name + ".sh")] + list(args)


def refresh_path():
    """Installers change PATH for new terminals only. Load the saved PATH into this process instead."""
    parts = []
    if WINDOWS:
        try:
            import winreg
            keys = [(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                    (winreg.HKEY_CURRENT_USER, r"Environment")]
            for hive, key in keys:
                try:
                    with winreg.OpenKey(hive, key) as handle:
                        value, _ = winreg.QueryValueEx(handle, "Path")
                        parts += os.path.expandvars(value).split(";")
                except OSError:
                    pass
        except ImportError:
            pass
        parts.append(os.path.join(os.path.expanduser("~"), "tools", "bin"))
    else:
        parts += ["/opt/homebrew/bin", "/usr/local/bin"]
    current = os.environ.get("PATH", "").split(os.pathsep)
    merged = []
    for p in current + parts:
        if p and p not in merged:
            merged.append(p)
    os.environ["PATH"] = os.pathsep.join(merged)


def http_get(url, timeout=5):
    """(status, text); (0, "") when nothing answers."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # nosec B310 - fixed http://localhost URLs
            return response.status, response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, ValueError):
        return 0, ""


# ---------------------------------------------------------------------------------------------- the steps
def missing_tools():
    return [t for t in CORE_TOOLS if not shutil.which(t)]


def lab_healthy():
    """True when the current kubectl context is minikube and every lab pod is ready."""
    if missing_tools():
        return False
    if smoke_test.check_context().status != "PASS":
        return False
    return smoke_test.check_pods().status == "PASS"


def step_tools(args):
    refresh_path()
    missing = missing_tools()
    if not missing:
        print("All core tools are installed: " + ", ".join(CORE_TOOLS))
        return OK, ""
    print("Missing: " + ", ".join(missing))
    if args.no_install:
        return HUMAN, "install {} with the setup kit (docs/GUIDE.md step 2), then run this again".format(
            ", ".join(missing))
    kit = script("install-tools", "-Engine", args.engine) if (WINDOWS and args.engine) else script("install-tools")
    print("Running the setup kit. It installs only what is missing (it can take 5-15 minutes)...")
    stream(kit, timeout=1800)
    refresh_path()
    missing = missing_tools()
    if not missing:
        print("All core tools are installed now.")
        return OK, ""
    if "docker" in missing:
        return HUMAN, ("the container engine needs an installer that a person runs (an admin prompt or a licence). "
                       "Windows: run this again with --engine rancher (free) or --engine docker, or see "
                       "docs/IT-REQUEST.md. Mac: the kit installs Colima")
    return HUMAN, "{} could not be installed here: see docs/GUIDE.md step 2, then run this again".format(
        ", ".join(missing))


def engine_ok():
    code, _ = run(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=25)
    return code == 0


def engine_starter():
    """The command that starts the container engine on this laptop, or None when a person must start it."""
    if WINDOWS:
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("LOCALAPPDATA", "")):
            for tail in (r"Docker\Docker\Docker Desktop.exe", r"Programs\DockerDesktop\Docker Desktop.exe"):
                exe = os.path.join(base, tail) if base else ""
                if exe and os.path.exists(exe):
                    return [exe]
        return None
    if MAC and os.path.exists("/Applications/Docker.app"):
        return ["open", "-a", "Docker"]
    if shutil.which("colima"):
        return ["colima", "start", "--cpu", "2", "--memory", "4"]
    return None


def step_engine(args):
    if engine_ok():
        print("The container engine is running.")
        return OK, ""
    starter = engine_starter()
    if not starter:
        return HUMAN, ("the container engine is not running: open Docker Desktop or Rancher Desktop (Mac: colima "
                       "start) and wait until it says it is running")
    print("The container engine is not running. Starting it: " + " ".join(starter), flush=True)
    try:
        kwargs = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if WINDOWS:
            kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(starter, **kwargs)
    except OSError as exc:
        return HUMAN, "could not start the container engine ({}): open it yourself and wait until it runs".format(exc)
    deadline = time.time() + ENGINE_WAIT_SECONDS
    while time.time() < deadline:
        time.sleep(5)
        if engine_ok():
            print("The container engine is running now.")
            return OK, ""
        print("  waiting for the container engine to start...", flush=True)
    return HUMAN, ("the container engine did not start in {} minutes: open it, click through any licence, sign-in "
                   "or update window, wait until it says it is running, then run this again".format(
                       ENGINE_WAIT_SECONDS // 60))


def step_cluster(args):
    code, out = run(["minikube", "status", "--format", "{{.Host}}"], timeout=60)
    if out.strip() == "Running":
        print("Minikube is already running.")
        return OK, ""
    print("Starting Minikube (the first time it downloads about 500 MB: 5-10 minutes)...", flush=True)
    code = stream(["minikube", "start", "--driver=docker", "--memory=4096"], timeout=1500)
    if code != 0:
        return FAIL, "minikube did not start (exit code {}): read the lines above in .lab/lab_up.log".format(code)
    return OK, ""


def source_hash():
    """A fingerprint of everything that goes into the shop's image."""
    digest = hashlib.sha256()
    paths = [os.path.join(ROOT, "Dockerfile")]
    for base, dirs, files in os.walk(os.path.join(ROOT, "app")):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        paths += [os.path.join(base, name) for name in sorted(files)]
    for path in paths:
        try:
            with open(path, "rb") as handle:
                digest.update(os.path.relpath(path, ROOT).encode("utf-8") + b"\0" + handle.read())
        except OSError:
            pass
    return digest.hexdigest()


def step_image(args):
    state = read_json(STATE_FILE, {})
    current = source_hash()
    code, listing = run(["minikube", "image", "ls"], timeout=90)
    present = IMAGE in listing
    if present and state.get("image_hash") == current and not args.redeploy:
        print("The shop's image is up to date.")
        return OK, ""
    print("Building the shop's image (about 1-3 minutes)...", flush=True)
    lines = []
    code = stream(["minikube", "image", "build", "-t", IMAGE, "."], timeout=1500, collect=lines)
    # minikube can exit with 0 even when the build failed, so the output is read as well as the exit code.
    problem = re.compile(r"failed to solve|^error:", re.I)
    failure = next((line.strip() for line in lines if problem.search(line.strip())), "")
    if code != 0 or failure:
        return FAIL, "the image build failed ({}): read the lines above in .lab/lab_up.log".format(
            failure or "exit code {}".format(code))
    state.update(image_hash=current, restart_needed=True)
    write_json(STATE_FILE, state)
    return OK, ""


def ensure_secret_files():
    """Create the private (Git-ignored) Secret files from the examples. Grafana login: admin / admin."""
    for name, note in (("alertmanager-secret", "with placeholders (Slack and email stay off)"),
                       ("grafana-secret", "with the lab login admin / admin")):
        target = os.path.join(ROOT, "k8s", name + ".yaml")
        if not os.path.exists(target):
            shutil.copyfile(os.path.join(ROOT, "k8s", name + ".example.yaml"), target)
            print("Created k8s/{}.yaml {}.".format(name, note))


def step_deploy(args):
    ensure_secret_files()
    code, namespace = run(["kubectl", "create", "namespace", "monitoring", "--dry-run=client", "-o", "yaml"])
    if code == 0:
        run(["kubectl", "apply", "-f", "-"], input_text=namespace)
    for name in ("alertmanager-secret", "grafana-secret"):
        if stream(["kubectl", "apply", "-f", "k8s/{}.yaml".format(name)], timeout=120) != 0:
            return FAIL, "kubectl could not apply k8s/{}.yaml".format(name)
    if stream(["kubectl", "apply", "-k", "k8s"], timeout=300) != 0:
        return FAIL, "kubectl apply -k k8s failed: read the lines above in .lab/lab_up.log"
    state = read_json(STATE_FILE, {})
    if state.get("restart_needed") or args.redeploy:
        # The image keeps its tag, so Kubernetes would keep the old pods: restart the app to run the new image.
        if stream(["kubectl", "rollout", "restart", "deployment/sre-metrics-app", "-n", "application"],
                  timeout=120) != 0:
            return FAIL, "the app could not be restarted"
        state["restart_needed"] = False
        write_json(STATE_FILE, state)
    return OK, ""


def pods_not_ready():
    """Names of deployments in the lab namespaces that are not fully ready; None when kubectl cannot answer."""
    waiting = []
    for namespace in DEPLOY_NAMESPACES:
        code, out = run(["kubectl", "get", "deployments", "-n", namespace, "-o", "json"], timeout=60)
        if code != 0:
            return None
        try:
            items = json.loads(out)["items"]
        except (ValueError, KeyError):
            return None
        for item in items:
            wanted = item.get("spec", {}).get("replicas", 1)
            if item.get("status", {}).get("readyReplicas", 0) < wanted:
                waiting.append("{}/{}".format(namespace, item["metadata"]["name"]))
    return waiting


def step_ready(args):
    deadline = time.time() + READY_WAIT_SECONDS
    while True:
        waiting = pods_not_ready()
        if waiting == []:
            print("Every deployment is ready.")
            return OK, ""
        if time.time() >= deadline:
            return FAIL, "still not ready after {} minutes: {}. Try kubectl describe pod".format(
                READY_WAIT_SECONDS // 60, ", ".join((waiting or ["kubectl does not answer"])[:4]))
        print("  waiting for: {}".format(", ".join(waiting) if waiting else "kubectl to answer"), flush=True)
        time.sleep(15)


def tunnels_up():
    return all(http_get(url, timeout=3)[0] for url in TUNNEL_CHECKS)


def supervisor_alive():
    try:
        with open(TUNNEL_PID_FILE, encoding="utf-8") as handle:
            return pid_alive(handle.read().strip())
    except OSError:
        return False


FORWARD_PORTS = r"(5000:5000|3000:|9090:9090|9093:9093|16686:16686|8000:8000)"


def kill_stale_forwards():
    """End leftover `kubectl port-forward` processes for the lab's ports (for example tunnels that outlived their
    keeper or came from scripts/dashboards.*). A tunnel to a replaced pod keeps listening and blocks the new one."""
    try:
        if WINDOWS:
            command = ("Get-CimInstance Win32_Process -Filter \"Name='kubectl.exe'\" | Where-Object "
                       "{ $_.CommandLine -match 'port-forward' -and $_.CommandLine -match '%s' } | "
                       "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" % FORWARD_PORTS)
            subprocess.run(["powershell", "-NoProfile", "-Command", command], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=60, **popen_kwargs())
        else:
            subprocess.run(["pkill", "-f", "kubectl port-forward.*" + FORWARD_PORTS], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=30)
    except (OSError, subprocess.SubprocessError):
        pass


def tunnel_pass(procs, make):
    """One round of the tunnel supervisor: start every port-forward that is not running (or has ended)."""
    for forward in FORWARDS:
        proc = procs.get(forward)
        if proc is None or proc.poll() is not None:
            procs[forward] = make(forward)


def run_tunnels():
    """Keep `kubectl port-forward` running for every web page. A forward ends when the pod behind it is replaced
    (after every deploy or restart), so this loop starts it again. Runs detached until lab_up.py --stop."""
    os.makedirs(LAB_DIR, exist_ok=True)
    with open(TUNNEL_PID_FILE, "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    atexit.register(lambda: os.path.exists(TUNNEL_PID_FILE) and os.remove(TUNNEL_PID_FILE))
    kill_stale_forwards()

    def make(forward):
        namespace, target, ports = forward
        return subprocess.Popen(["kubectl", "port-forward", "-n", namespace, target, ports], cwd=ROOT,
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                **popen_kwargs())
    procs = {}
    while True:
        tunnel_pass(procs, make)
        time.sleep(3)


def stop_tunnels():
    """Stop the supervisor and the port-forwards it started (and any left by scripts/dashboards.*)."""
    try:
        with open(TUNNEL_PID_FILE, encoding="utf-8") as handle:
            pid = int(handle.read().strip())
    except (OSError, ValueError):
        pid = 0
    if pid and pid_alive(pid):
        if WINDOWS:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=30)
        else:
            import signal
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except OSError:
                os.kill(pid, signal.SIGTERM)
    try:
        os.remove(TUNNEL_PID_FILE)
    except OSError:
        pass


def ensure_tunnels(wait=TUNNEL_WAIT_SECONDS):
    """True when every web page answers on localhost. Starts the tunnel keeper if it is not running."""
    if supervisor_alive() and tunnels_up():
        return True
    if not supervisor_alive():
        spawn_detached("--tunnels")
        print("Started the tunnel keeper (it reopens a tunnel whenever a pod is replaced).", flush=True)
    deadline = time.time() + wait
    while time.time() < deadline:
        if tunnels_up():
            return True
        time.sleep(3)
    return tunnels_up()


def step_connect(args):
    if supervisor_alive() and tunnels_up():
        print("The tunnels to the web pages are already open.")
        return OK, ""
    if ensure_tunnels():
        return OK, ""
    return FAIL, "the web pages did not open on localhost (3000, 9090, 9093, 16686, 5000): read .lab/lab_up.log"


def step_verify(args):
    # A restart replaces pods and the keeper reopens their tunnels a few seconds later: do not say "live" before that.
    tunnel_deadline = time.time() + TUNNEL_WAIT_SECONDS
    while not tunnels_up() and time.time() < tunnel_deadline:
        print("  waiting for the web pages on localhost...", flush=True)
        time.sleep(3)
    # Right after a (re)start some targets need a minute or two: retry quietly before calling anything a failure.
    deadline = time.time() + VERIFY_WAIT_SECONDS
    while True:
        results = smoke_test.part_b()
        failed = [r for r in results if r.status == "FAIL"]
        if not failed or time.time() >= deadline:
            break
        print("Still starting: {}. Checking again in 15 seconds...".format(", ".join(r.name for r in failed)),
              flush=True)
        time.sleep(15)
    smoke_test.print_results("Checks (read-only)", results)
    run([sys.executable, os.path.join("scripts", "lab.py"), "check", "M00"], timeout=120)
    if failed:
        return FAIL, "not everything is connected: {}".format(", ".join(r.name for r in failed))
    print(MAP)
    print("Your lab is live. The pages:")
    for name, url in PAGES:
        print("  {:<32} {}".format(name, url))
    print("Grafana opens without a login, view-only. To edit, sign in with admin / admin.")
    print("\nNext: a guided tour of each tool:  {} scripts{}lab_up.py --tour 1".format(PY, os.sep))
    print("Then watch an alert travel:         {} scripts{}lab_up.py --drill".format(PY, os.sep))
    return OK, ""


# ---------------------------------------------------------------------------------------------- the worker
def run_worker(args):
    """Run every step in order, recording progress in .lab/status.json. Returns 0 done, 1 failed, 2 needs a human."""
    os.makedirs(LAB_DIR, exist_ok=True)
    with open(PID_FILE, "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    atexit.register(lambda: os.path.exists(PID_FILE) and os.remove(PID_FILE))
    total = len(STEPS)
    set_status(state="running", pid=os.getpid(), started_at=now(), total_steps=total, step_index=0, percent=0,
               message="starting", next_action="wait")
    for index, (key, title) in enumerate(STEPS, 1):
        set_status(step=key, title=title, step_index=index, percent=int((index - 1) * 100 / total), message=title,
                   next_action="wait")
        banner("Step {} of {}: {}".format(index, total, title))
        try:
            kind, message = globals()["step_" + key](args)
        except Exception as exc:  # noqa: BLE001 - the worker must always leave a clear status behind
            kind, message = FAIL, "unexpected error in step {}: {}".format(key, exc)
        if kind != OK:
            state = "needs_human" if kind == HUMAN else "failed"
            set_status(state=state, message=message, next_action=message)
            print("\n" + result_line(2 if kind == HUMAN else 1, message), flush=True)
            return 2 if kind == HUMAN else 1
    set_status(state="done", percent=100, message="everything is running and connected",
               next_action="run lab_up.py --tour 1")
    print("\n" + result_line(0, "everything is running and connected. Next: lab_up.py --tour 1"), flush=True)
    return 0


def spawn_detached(flag, args=None):
    """Start `lab_up.py <flag>` detached from this call, so it survives when the calling tool ends or times out."""
    cmd = [sys.executable, os.path.abspath(__file__), flag]
    if args is not None:
        if args.engine:
            cmd += ["--engine", args.engine]
        if args.redeploy:
            cmd.append("--redeploy")
        if args.no_install:
            cmd.append("--no-install")
    kwargs = {"cwd": ROOT, "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if WINDOWS:
        base = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        try:
            return subprocess.Popen(cmd, creationflags=base | 0x01000000, **kwargs)  # | CREATE_BREAKAWAY_FROM_JOB
        except OSError:
            return subprocess.Popen(cmd, creationflags=base, **kwargs)
    return subprocess.Popen(cmd, start_new_session=True, **kwargs)


def spawn_worker(args):
    return spawn_detached("--worker", args)


def status_exit(status):
    """(code, message) for a terminal status, or None while it is still running."""
    state = status.get("state")
    message = status.get("message") or ""
    if state == "done":
        return 0, "everything is running and connected. Next: lab_up.py --tour 1"
    if state == "needs_human":
        return 2, message + ". Then run the same command again"
    if state == "failed":
        return 1, message + " (details: .lab/lab_up.log)"
    return None


def poll(args, wait):
    """Follow the worker for up to `wait` seconds. Returns the exit code after printing the last line."""
    deadline = time.time() + wait
    grace = time.time() + SPAWN_GRACE
    respawned = False
    seen = None
    while True:
        status = read_status()
        terminal = status_exit(status)
        if terminal:
            return finish(*terminal)
        alive = pid_alive(status.get("pid")) or time.time() < grace
        if status.get("state") == "running" and not alive:
            if respawned:
                return finish(1, "the background worker stopped twice (details: .lab/lab_up.log)")
            respawned = True
            print("The background worker stopped; starting it again (it continues where it stopped).", flush=True)
            set_status(state="running", pid=0, message="restarting")
            spawn_worker(args)
            grace = time.time() + SPAWN_GRACE
        key = (status.get("step"), status.get("message"))
        if key != seen:
            seen = key
            print("[{}] step {} of {}: {}".format(now()[11:], status.get("step_index", 0), len(STEPS),
                                                  status.get("title") or status.get("message") or "starting"),
                  flush=True)
        if time.time() >= deadline:
            return finish(3, "still working on step {} of {} ({}). Run exactly the same command again in a minute"
                          .format(status.get("step_index", 0), len(STEPS), status.get("title") or "starting"))
        time.sleep(5)


def cmd_up(args, interactive):
    status = read_status()
    worker_alive = status.get("state") == "running" and pid_alive(status.get("pid"))
    if interactive:
        if worker_alive and status.get("pid") != os.getpid():
            print("Another run is already working (process {}). Following it...".format(status.get("pid")))
            return poll(args, 1800)
        code = run_worker(args)
        return code
    if not worker_alive:
        set_status(state="running", pid=0, step="starting", step_index=0, title="starting", message="starting",
                   percent=0, next_action="wait")
        spawn_worker(args)
    else:
        print("A background run is already working (process {}). Following it...".format(status.get("pid")))
    return poll(args, args.wait)


def cmd_status():
    status = read_status()
    state = status.get("state", "never started")
    alive = pid_alive(status.get("pid"))
    if state == "running" and not alive:
        state = "stopped unexpectedly (the worker is not running): run lab_up.py again, it continues"
    print("state:       {}".format(state))
    for key, label in (("title", "step"), ("percent", "progress %"), ("message", "message"),
                       ("next_action", "next action"), ("updated_at", "updated")):
        if status.get(key) not in (None, ""):
            print("{:<12} {}".format(label + ":", status[key]))
    try:
        with open(LOG_FILE, encoding="utf-8", errors="replace") as handle:
            tail = handle.read().splitlines()[-12:]
        print("\nlast lines of .lab/lab_up.log:")
        for line in tail:
            print("  " + line)
    except OSError:
        pass
    terminal = status_exit(status)
    if terminal:
        return finish(*terminal)
    if status.get("state") == "running" and alive:
        return finish(3, "still working on step {} of {}. Run lab_up.py again to follow it".format(
            status.get("step_index", 0), len(STEPS)))
    return finish(3 if status.get("state") == "running" else 1,
                  "the lab is not up: run lab_up.py" if state == "never started" else
                  "the last run stopped: run lab_up.py again, it continues")


# ---------------------------------------------------------------------------------------------- tour and drill
def targets_up():
    status, body = http_get("http://localhost:9090/api/v1/targets?state=active")
    try:
        targets = json.loads(body)["data"]["activeTargets"]
    except (ValueError, KeyError, TypeError):
        return False
    return bool(targets) and all(t.get("health") == "up" for t in targets)


TOUR = [
    {"title": "Nimbus Store, the shop", "url": "http://localhost:5000",
     "say": ("This is the pretend online shop that everything else watches. It reports its own numbers (metrics), "
             "a JSON log line for every request, and the path of each request (traces)."),
     "ready": lambda: "running" in http_get("http://localhost:5000")[1],
     "wait_for": "the shop to answer"},
    {"title": "Prometheus: what is measured", "url": "http://localhost:9090/targets",
     "say": ("Prometheus visits each thing it watches every 10 seconds and stores the numbers. Every row should "
             "say UP in green; a red DOWN means something stopped answering."),
     "ready": targets_up, "wait_for": "every Prometheus target to be UP"},
    {"title": "Grafana: charts, logs and traces in one place", "url": "http://localhost:3000/dashboards",
     "say": ("Grafana draws the numbers as charts. Open the SRE Demo folder, then Golden Signals. The "
             "dashboards are files in Git, so they are the same on every laptop. Explore shows the logs (Loki)."),
     "ready": lambda: '"database"' in http_get("http://localhost:3000/api/health")[1],
     "wait_for": "Grafana to be healthy"},
    {"title": "Jaeger: the path of one request",
     "url": "http://localhost:16686/search?service=sre-metrics-app&limit=20&lookback=1h",
     "say": ("A trace shows where one request spent its time. Click any trace: each bar is one step, and its "
             "trace_id also appears in the shop's logs, so you can jump from a log line to the trace."),
     "ready": lambda: "sre-metrics-app" in http_get("http://localhost:16686/api/services")[1],
     "wait_for": "Jaeger to know the shop"},
    {"title": "Alertmanager: who gets woken up", "url": "http://localhost:9093",
     "say": ("Prometheus decides when something is wrong; Alertmanager decides who hears about it and groups the "
             "noise. One demo alert is always on, to prove the path works. It is expected."),
     "ready": lambda: "OK" in http_get("http://localhost:9093/-/ready")[1],
     "wait_for": "Alertmanager to be ready"},
    {"title": "Phone alerts (optional)", "url": None,
     "say": ("Real teams get alerts on their phone. This is optional and free: install the ntfy app, then run "
             "scripts{}notify_setup.py and subscribe to the topic it prints. Slack, email and AWX are placeholders "
             "in this lab and fail on purpose. Skip this stop if you like.".format(os.sep)),
     "ready": lambda: True, "wait_for": ""},
    {"title": "Alert drill: break the shop on purpose", "url": None,
     "say": ("A small pod sends failing requests. In about 150 seconds the rule HighErrorRate fires and you can "
             "follow it from Grafana to Prometheus to Alertmanager. Start it with: {} scripts{}lab_up.py "
             "--drill".format(PY, os.sep)),
     "ready": lambda: True, "wait_for": ""},
]


def cmd_tour(args):
    if args.tour == 0:
        print("The tour of the tools (run: {} scripts{}lab_up.py --tour N):".format(PY, os.sep))
        for index, stop in enumerate(TOUR, 1):
            print("  {}  {}".format(index, stop["title"]))
        return finish(0, "pick a stop, for example --tour 1")
    if not 1 <= args.tour <= len(TOUR):
        return finish(1, "there are {} stops: use --tour 1 to --tour {}".format(len(TOUR), len(TOUR)))
    stop = TOUR[args.tour - 1]
    if stop["url"] and not tunnels_up():
        ensure_tunnels(min(args.wait, 45))
    banner("Tour stop {} of {}: {}".format(args.tour, len(TOUR), stop["title"]))
    print(stop["say"])
    if stop["url"]:
        print("Page: " + stop["url"])
    deadline = time.time() + min(args.wait, 60)
    while not stop["ready"]():
        if time.time() >= deadline:
            return finish(3, "waiting for {}. If the lab was just started, run the same command again in a minute; "
                             "if the page does not open, run lab_up.py".format(stop["wait_for"]))
        print("  waiting for {}...".format(stop["wait_for"]), flush=True)
        time.sleep(5)
    if stop["url"] and not args.no_browser:
        webbrowser.open(stop["url"])
    nxt = "run --tour {} next".format(args.tour + 1) if args.tour < len(TOUR) else "that was the last stop"
    return finish(0, "stop {} is ready, {}".format(args.tour, nxt))


def phone_alerts_on():
    """True when notify_setup.py has set a real ntfy topic. Only the ntfy-url line of the private file is read."""
    try:
        import notify_setup
        url = notify_setup.read_ntfy_url()
        return bool(url) and url != notify_setup.OFF_URL
    except Exception:  # noqa: BLE001 - the drill message must never crash
        return False


def drill_pod_running():
    code, out = run(["kubectl", "get", "pod", "errload", "-n", "application", "-o", "json"], timeout=30)
    if code != 0:
        return False
    try:
        return json.loads(out).get("status", {}).get("phase") in ("Pending", "Running")
    except ValueError:
        return False


def firing_alerts():
    code, out = smoke_test.proxy_get("alertmanager:9093", "/api/v2/alerts")
    try:
        return {a["labels"]["alertname"] for a in json.loads(out)}
    except (ValueError, KeyError, TypeError):
        return set()


def cmd_drill(args):
    banner("Alert drill: break the shop on purpose and follow the alert")
    if not lab_healthy():
        return finish(1, "the lab is not running: run {} scripts{}lab_up.py first".format(PY, os.sep))
    if drill_pod_running():
        print("The drill is already running. Following it...")
    else:
        run(["kubectl", "delete", "pod", "errload", "-n", "application", "--ignore-not-found"], timeout=60)
        code, out = run(["kubectl", "apply", "-f", "k8s/drills/errload-pod.yaml"], timeout=60)
        if code != 0:
            return finish(1, "the drill pod could not start: " + out.strip()[-200:])
        print("Drill started: the errload pod sends failing requests to the app for about 12 minutes.")
        print("Watch: Grafana (Golden Signals: the error rate climbs), Prometheus > Alerts (HighErrorRate turns "
              "PENDING, then FIRING), Alertmanager (the alert arrives and is routed by severity).")
    started = time.time()
    deadline = started + args.wait
    while True:
        if "HighErrorRate" in firing_alerts():
            print("\nThe alert went from the app's metrics to a Prometheus rule to Alertmanager, which routed it.")
            if phone_alerts_on():
                print("Out of the laptop: a push goes to your phone through ntfy (it can take a minute).")
            else:
                print("Out of the laptop: nothing yet. Phone alerts are off; turn them on with: "
                      "{} scripts{}notify_setup.py".format(PY, os.sep))
            print("Slack, email and the AWX webhook are placeholders in this lab: Alertmanager tries them and they")
            print("fail, on purpose (no real accounts). Only the phone push (ntfy) leaves the laptop.")
            print("The drill pod stops by itself in about 12 minutes; the alert then resolves.")
            return finish(0, "HighErrorRate is firing")
        if time.time() >= deadline:
            return finish(3, "HighErrorRate is not firing yet (it needs about 150 seconds). Run the same command "
                             "again to keep watching")
        print("  waiting for HighErrorRate ({} s)...".format(int(time.time() - started)), flush=True)
        time.sleep(10)


def cmd_stop():
    banner("Stopping the lab (your data stays)")
    stop_tunnels()
    stream(script("dashboards", "-Stop" if WINDOWS else "--stop"))
    code = stream(["minikube", "stop"])
    set_status(state="stopped", message="stopped on purpose", next_action="run lab_up.py to resume")
    if code != 0:
        return finish(1, "minikube did not stop cleanly")
    return finish(0, "stopped. Run lab_up.py again to resume where you left off")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bring the SRE lab up with one command.")
    parser.add_argument("--status", action="store_true", help="show where the setup is (read-only, instant)")
    parser.add_argument("--tour", type=int, nargs="?", const=0, metavar="N", help="a numbered tour of the tools")
    parser.add_argument("--drill", action="store_true", help="fire the alert drill and follow the alert")
    parser.add_argument("--stop", action="store_true", help="close the tunnels and stop Minikube")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--tunnels", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--mode", choices=["foreground", "detached"], help="foreground when run by a person "
                        "in a terminal, detached (background worker, polled) when run by an AI agent")
    parser.add_argument("--wait", type=int, default=DEFAULT_WAIT, help="seconds to follow before NOT_FINISHED")
    parser.add_argument("--engine", choices=["rancher", "docker"], help="container engine for the setup kit")
    parser.add_argument("--redeploy", action="store_true", help="rebuild the image and restart the app")
    parser.add_argument("--no-install", action="store_true", help="never run the setup kit")
    parser.add_argument("--no-browser", action="store_true", help="do not open browser tabs")
    args = parser.parse_args(argv)

    interactive = (args.mode == "foreground") or (args.mode is None and sys.stdout.isatty())
    if not isinstance(sys.stdout, Tee):
        sys.stdout = Tee(sys.stdout, LOG_FILE, tty=interactive)
    refresh_path()
    if args.status:
        return cmd_status()
    if args.worker:
        return run_worker(args)
    if args.tunnels:
        return run_tunnels()
    if args.stop:
        return cmd_stop()
    if args.drill:
        if interactive and args.wait == DEFAULT_WAIT:
            args.wait = 480
        return cmd_drill(args)
    if args.tour is not None:
        return cmd_tour(args)
    print("lab_up.py started {} ({}). Progress: .lab/lab_up.log, status: lab_up.py --status".format(
        now(), "foreground" if interactive else "background worker"), flush=True)
    return cmd_up(args, interactive)


if __name__ == "__main__":
    sys.exit(main())
