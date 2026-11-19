#!/usr/bin/env python3
"""
Bring the whole SRE lab up with one command, then show that every tool is running and connected.

    Windows (PowerShell):  python scripts\\lab_up.py
    Mac or Linux:          python3 scripts/lab_up.py

What it does, in order (it skips what is already done, so you can run it again at any time):
  1. Checks the laptop and installs the missing tools with the setup kit (scripts/install-tools.*).
     It reloads PATH itself, so you do not need a new terminal before the next step.
  2. Starts Minikube (Kubernetes on your laptop) and deploys Nimbus Store and the monitoring tools
     (scripts/deploy.*). Skipped when the lab is already running and healthy.
  3. Opens the tunnels to the web pages (scripts/dashboards.*) and opens them in your browser.
  4. Checks that everything is connected: pods ready, Prometheus scraping every target, alert rules loaded,
     Alertmanager and Grafana healthy. Then it prints a map of how the tools talk to each other.

Other actions:
  --drill      fire the alert drill: failing requests -> Prometheus -> Alertmanager (-> your phone if set up)
  --stop       close the tunnels and stop Minikube (your data stays; run lab_up.py again to resume)

Options:
  --engine rancher|docker   which container engine the setup kit installs if none is there (Windows)
  --redeploy                deploy again even if the lab is already healthy (for example after a code change)
  --no-install              never run the setup kit (only report what is missing)
  --no-browser              do not open browser tabs

Exit codes: 0 ready, 1 something failed (the message says what), 2 a human step is needed (the message says which).
Only the Python standard library is used.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import smoke_test  # noqa: E402

WINDOWS = platform.system() == "Windows"
MAC = platform.system() == "Darwin"
PY = "python" if WINDOWS else "python3"
CORE_TOOLS = ("docker", "minikube", "kubectl")
VERIFY_WAIT_SECONDS = 300
PAGES = [
    ("Grafana (dashboards, logs)", "http://localhost:3000"),
    ("Prometheus (metrics, targets)", "http://localhost:9090/targets"),
    ("Alertmanager (alerts)", "http://localhost:9093"),
    ("Jaeger (traces)", "http://localhost:16686"),
    ("Nimbus Store (the app)", "http://localhost:5000"),
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


def banner(text):
    print("\n" + "=" * 78 + "\n  " + text + "\n" + "=" * 78, flush=True)


def stream(cmd):
    """Run a command in the repository root and show its output live. Returns the exit code."""
    print("> " + " ".join(cmd), flush=True)
    try:
        return subprocess.call(cmd, cwd=ROOT)
    except FileNotFoundError:
        print("  not found: " + cmd[0])
        return 127


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
    banner("Step 1 of 4: the tools")
    refresh_path()
    missing = missing_tools()
    if not missing:
        print("All core tools are installed: " + ", ".join(CORE_TOOLS))
        return 0
    print("Missing: " + ", ".join(missing))
    if args.no_install:
        print("Install them with the setup kit (docs/GUIDE.md step 2), then run this again.")
        return 2
    kit = script("install-tools", "-Engine", args.engine) if (WINDOWS and args.engine) else script("install-tools")
    print("Running the setup kit. It installs only what is missing (it can take 5-15 minutes)...")
    stream(kit)
    refresh_path()
    missing = missing_tools()
    if not missing:
        print("All core tools are installed now.")
        return 0
    print("\nStill missing: " + ", ".join(missing))
    if "docker" in missing:
        print("The container engine needs an installer that a person runs (admin prompt, licence or IT request).")
        print("Windows: run this again with '--engine rancher' (free) or '--engine docker',"
              " or see docs/IT-REQUEST.md.")
        print("Mac: the kit installs Colima; start it with 'colima start --cpu 2 --memory 4'.")
    print("When that is done, run this command again: it continues where it stopped.")
    return 2


def step_deploy(args):
    banner("Step 2 of 4: start Kubernetes and deploy Nimbus Store with its monitoring")
    if lab_healthy() and not args.redeploy:
        print("The lab is already running and every pod is ready. Skipping the deploy (use --redeploy to force it).")
        return 0
    print("This takes 5-10 minutes the first time (Minikube downloads its images). Later runs take 2-3 minutes.")
    code = stream(script("deploy"))
    if code != 0:
        print("\nThe deploy stopped (exit code {}). Read the last lines above; docs/GUIDE.md".format(code)
              + " 'If something goes wrong' covers the usual causes.")
        return 1
    return 0


def step_connect(args):
    banner("Step 3 of 4: open the web pages")
    code = stream(script("dashboards", "-Background" if WINDOWS else "--background"))
    if code != 0:
        print("The tunnels did not start. Run the dashboards script by hand to see the error.")
        return 1
    time.sleep(3)
    if not args.no_browser:
        for _, url in PAGES[1:]:  # the dashboards script already opened Grafana
            webbrowser.open(url)
    return 0


def step_verify():
    banner("Step 4 of 4: is everything connected?")
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
    stream([sys.executable, os.path.join("scripts", "lab.py"), "check", "M00"])
    if failed:
        print("\nNot everything is connected yet. Wait a minute and run this command again.")
        return 1
    print(MAP)
    print("Your lab is live. Open these pages:")
    for name, url in PAGES:
        print("  {:<32} {}".format(name, url))
    print("Grafana opens without a login, view-only. To edit, sign in with admin / admin.")
    print("\nNext: watch an alert travel through the tools:  {} scripts{}lab_up.py --drill".format(PY, os.sep))
    print("Phone alerts (free ntfy app, no account):        {} scripts{}notify_setup.py".format(PY, os.sep))
    return 0


def drill():
    banner("Alert drill: break the shop on purpose and follow the alert")
    if not lab_healthy():
        print("The lab is not running. Start it first:  {} scripts{}lab_up.py".format(PY, os.sep))
        return 1
    print("A small pod sends failing requests to Nimbus Store. Watch, while it runs:")
    print("  1. Grafana > SRE Demo > Golden Signals: the error rate climbs (about 1 minute).")
    print("  2. Prometheus > Alerts (http://localhost:9090/alerts): HighErrorRate turns PENDING, then FIRING.")
    print("  3. Alertmanager (http://localhost:9093): the alert arrives and is routed by severity.")
    print("  4. Your phone, if you ran notify_setup.py: a push with [firing] HighErrorRate.")
    code = stream(script("trigger-alert"))
    if code == 0:
        print("\nThe alert went from the app's metrics to a Prometheus rule to Alertmanager, which routed it.")
        if phone_alerts_on():
            print("Out of the laptop: a push goes to your phone through ntfy (it can take a minute).")
        else:
            print("Out of the laptop: nothing yet. Phone alerts are off; turn them on with:  "
                  "{} scripts{}notify_setup.py".format(PY, os.sep))
        print("Slack, email and the AWX webhook are placeholders in this lab: Alertmanager tries them and they fail,")
        print("on purpose (no real accounts). Only the phone push (ntfy) leaves the laptop.")
        print("The drill pod stops by itself in about 12 minutes; the alert then resolves.")
    return code


def phone_alerts_on():
    """True when notify_setup.py has set a real ntfy topic. Only the ntfy-url line of the private file is read."""
    try:
        import notify_setup
        url = notify_setup.read_ntfy_url()
        return bool(url) and url != notify_setup.OFF_URL
    except Exception:  # noqa: BLE001 - the drill message must never crash
        return False


def stop():
    banner("Stopping the lab (your data stays)")
    stream(script("dashboards", "-Stop" if WINDOWS else "--stop"))
    code = stream(["minikube", "stop"])
    print("Stopped. Run lab_up.py again to resume where you left off.")
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bring the SRE lab up with one command.")
    parser.add_argument("--drill", action="store_true", help="fire the alert drill and follow the alert")
    parser.add_argument("--stop", action="store_true", help="close the tunnels and stop Minikube")
    parser.add_argument("--engine", choices=["rancher", "docker"], help="container engine for the setup kit")
    parser.add_argument("--redeploy", action="store_true", help="deploy even if the lab is healthy")
    parser.add_argument("--no-install", action="store_true", help="never run the setup kit")
    parser.add_argument("--no-browser", action="store_true", help="do not open browser tabs")
    args = parser.parse_args(argv)

    refresh_path()
    if args.stop:
        return stop()
    if args.drill:
        return drill()
    for step in (step_tools, step_deploy, step_connect):
        code = step(args)
        if code != 0:
            return code
    return step_verify()


if __name__ == "__main__":
    sys.exit(main())
