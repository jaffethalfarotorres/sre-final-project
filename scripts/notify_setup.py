#!/usr/bin/env python3
"""
Phone push notifications for the lab, with no account and no sign-up: works on IBM laptops.

Alertmanager sends every critical and warning alert to ntfy (https://ntfy.sh), a free push notification service.
You read the alerts in the free ntfy app on your phone, or in any browser. On an IBM-managed laptop personal Slack and
personal mail are usually blocked, and the lab must never use IBM Slack or IBM mail, so this is the way to get real
notifications there (the "Advanced alerting" bonus of the final project).

    python3 scripts/notify_setup.py            # create a private topic, connect Alertmanager, send a test push
    python3 scripts/notify_setup.py --test     # only send another test push to the topic you already have
    python3 scripts/notify_setup.py --new      # switch to a fresh private topic (after sharing a screenshot)
    python3 scripts/notify_setup.py --off      # disconnect ntfy again (Alertmanager stops sending)

On Windows use "python" instead of "python3".

What it changes: the "ntfy-url" line of your private file k8s/alertmanager-secret.yaml (Git never uploads it; no other
line is read or printed), the matching key in the cluster Secret, and a restart of Alertmanager.

Privacy: the topic name is a random secret. Anyone who knows it can read the messages, so send only lab alerts there,
never IBM, client or personal data.
"""

import argparse
import json
import re
import secrets
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRET_FILE = ROOT / "k8s" / "alertmanager-secret.yaml"
EXAMPLE_FILE = ROOT / "k8s" / "alertmanager-secret.example.yaml"
SERVER = "https://ntfy.sh"
OFF_URL = "http://ntfy-not-configured.invalid/"
PY = "python" if sys.platform == "win32" else "python3"

# ntfy turns Alertmanager's JSON into a readable push with these Go templates
# (https://docs.ntfy.sh/publish/#message-templating).
TITLE = "[{{.status}}] {{.commonLabels.severity}}: {{.commonLabels.alertname}}"
MESSAGE = "{{range .alerts}}{{.annotations.summary}}\nRunbook: {{.annotations.runbook_url}}\n{{end}}"


def run(*args):
    """Run a command, print it, stop with a clear message if it fails."""
    print("  $ " + " ".join(args))
    result = subprocess.run(list(args), capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"That command failed:\n{result.stderr.strip()}\nIs Minikube running and the lab deployed?")
    return result.stdout.strip()


def topic_url(topic):
    query = urllib.parse.urlencode({"tpl": "yes", "t": TITLE, "m": MESSAGE, "tags": "rotating_light"})
    return f"{SERVER}/{topic}?{query}"


def read_ntfy_url():
    """Return the current ntfy-url value from the private file (only that line is read)."""
    if not SECRET_FILE.exists():
        return None
    match = re.search(r'^\s*ntfy-url:\s*"([^"]*)"', SECRET_FILE.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else None


def write_ntfy_url(url):
    """Set the ntfy-url line in the private file, creating the file from the example if needed."""
    if not SECRET_FILE.exists():
        shutil.copyfile(EXAMPLE_FILE, SECRET_FILE)
        print(f"Created {SECRET_FILE.relative_to(ROOT)} from the example (Slack and email stay off).")
    text = SECRET_FILE.read_text(encoding="utf-8")
    line = f'  ntfy-url: "{url}"'
    if re.search(r"^\s*ntfy-url:", text, re.MULTILINE):
        text = re.sub(r"^\s*ntfy-url:.*$", lambda _: line, text, flags=re.MULTILINE)
    else:
        text = text.rstrip("\n") + "\n" + line + "\n"
    SECRET_FILE.write_text(text, encoding="utf-8")


def apply_and_restart():
    print("\nUpdating the cluster Secret and restarting Alertmanager:")
    run("kubectl", "apply", "-f", str(SECRET_FILE))
    run("kubectl", "rollout", "restart", "deployment/alertmanager", "-n", "monitoring")
    run("kubectl", "rollout", "status", "deployment/alertmanager", "-n", "monitoring", "--timeout=120s")


def send_test(url):
    """Send one push in the same format Alertmanager uses, straight from this laptop."""
    body = {"status": "test", "commonLabels": {"severity": "info", "alertname": "LabConnected"},
            "alerts": [{"annotations": {
                "summary": "Your SRE lab can reach your phone. Real alerts look like this.",
                "runbook_url": "https://github.com/jaffethalfarotorres/sre-final-project/blob/main/docs/runbooks/high-error-rate.md"}}]}
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:  # nosec B310: fixed https URL
            return response.status == 200
    except OSError as error:
        print(f"Could not reach {SERVER}: {error}. Is the laptop online? A VPN or proxy may block it.")
        return False


def main():
    sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(description="Phone push notifications for the SRE lab (ntfy, no account)")
    parser.add_argument("--test", action="store_true", help="send another test push to your existing topic")
    parser.add_argument("--off", action="store_true", help="disconnect ntfy")
    parser.add_argument("--topic", help="use this topic name instead of a random one")
    parser.add_argument("--new", action="store_true", help="switch to a fresh random topic")
    args = parser.parse_args()

    current = read_ntfy_url()
    if args.off:
        write_ntfy_url(OFF_URL)
        apply_and_restart()
        print("\nntfy is disconnected. Alertmanager no longer sends phone pushes.")
        return 0
    if args.test:
        if not current or not current.startswith(SERVER):
            sys.exit(f"No topic yet. Run: {PY} scripts/notify_setup.py")
        print("Test push sent." if send_test(current) else "Test push failed.")
        return 0

    if current and current.startswith(SERVER) and not (args.topic or args.new):
        topic = urllib.parse.urlparse(current).path.strip("/")
        print(f"Keeping your existing topic {topic}.")
    else:
        topic = args.topic or "sre-lab-" + secrets.token_urlsafe(12).replace("_", "x").replace("-", "y").lower()
    url = topic_url(topic)
    write_ntfy_url(url)
    apply_and_restart()
    ok = send_test(url)

    print("\n" + "=" * 64)
    print("  Phone push is ON.")
    print(f"  Your private topic:  {topic}")
    print("  On your phone: install the free 'ntfy' app (App Store or Google Play), tap +,")
    print(f"  and subscribe to the topic {topic} on the default server ntfy.sh.")
    print(f"  Or open in any browser:  {SERVER}/{topic}")
    sent = "A test push was sent: you should see 'LabConnected' now." if ok else "The test push failed (see above)."
    print("  " + sent)
    drill = "scripts\\trigger-alert.ps1" if PY == "python" else "./scripts/trigger-alert.sh"
    print(f"  Then make an alert fire ({drill}):")
    print("  about 3 minutes later a 'firing: critical: HighErrorRate' push arrives.")
    print("  Keep the topic name to yourself, and send only lab alerts there.")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
