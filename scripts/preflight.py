#!/usr/bin/env python3
"""
Preflight check for the SRE Academy lab. Run it first, before you install anything else.

    Windows (PowerShell):  python scripts\\preflight.py
    Mac or Linux:          python3 scripts/preflight.py

It only reads. It never installs, changes or deletes anything, and it needs no administrator rights.
It prints one line per check with PASS, WARN, TODO or FAIL and the fix for each one:

    PASS  ready.
    WARN  works, with a limit (for example: core stack only, no add-ons).
    TODO  a tool is not installed yet. The install guide (docs/GUIDE.md step 2) adds it.
    FAIL  this laptop cannot run the lab until it is fixed. Bring the line to your professor or IT.

Options:
    --no-network   skip the two website checks (for example on a plane)

The script uses only the Python standard library and keeps Python 3.6 syntax, so it can still run on an old
Python (such as Apple's 3.9) and tell you to install a newer one. Exit code: 1 if any line is FAIL, else 0.
See docs/IT-REQUEST.md for what to ask IBM IT for.
"""

import argparse
import collections
import ctypes
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

Result = collections.namedtuple("Result", "status name found fix")

GIB = 1024 ** 3
# A laptop sold as "16 GB" reports a bit less to the operating system (for example 15.7 GiB), so the limits allow it.
RAM_MIN_GIB, RAM_GOOD_GIB = 7.5, 15.0
DISK_MIN_GB, DISK_GOOD_GB = 20, 25
PYTHON_MIN = (3, 10)
# ansible-core 2.17 (Part 5, M10) runs on Python 3.10 to 3.12 only.
PYTHON_ANSIBLE_MAX = (3, 12)

# Tool name -> (needed for, command that prints its version). Read-only commands only.
TOOLS = collections.OrderedDict([
    ("docker", ("core", ["docker", "--version"])),
    ("minikube", ("core", ["minikube", "version", "--short"])),
    ("kubectl", ("core", ["kubectl", "version", "--client"])),
    ("git", ("core", ["git", "--version"])),
    ("gh", ("core", ["gh", "--version"])),
    ("terraform", ("core", ["terraform", "version"])),
    ("helm", ("optional", ["helm", "version", "--short"])),
])

INSTALL = {
    "Windows": {
        "docker": "Install a container engine: winget install -e --id SUSE.RancherDesktop (free) "
                  "or Docker.DockerDesktop (needs a licence). See docs/IT-REQUEST.md",
        "minikube": "Run the setup kit: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\install-tools.ps1",
        "kubectl": "Run the setup kit: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\install-tools.ps1",
        "git": "winget install -e --id Git.Git",
        "gh": "Run the setup kit: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\install-tools.ps1",
        "terraform": "winget install -e --id Hashicorp.Terraform (needed in Part 5, M11)",
        "helm": "Optional (only for the Helm path in Part 5). Run the setup kit: "
                "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\install-tools.ps1",
        "python": "winget install -e --id Python.Python.3.12 --scope user, then use 'python' (never 'python3')",
    },
    "Darwin": {
        "docker": "brew install colima docker, then: colima start --cpu 4 --memory 6 --disk 60",
        "colima": "brew install colima, then: colima start --cpu 4 --memory 6 --disk 60 (8 GB Mac: --cpu 2 "
                  "--memory 4)",
        "minikube": "Run the setup kit: ./scripts/install-tools.sh",
        "kubectl": "Run the setup kit: ./scripts/install-tools.sh",
        "git": "Run the setup kit: ./scripts/install-tools.sh",
        "gh": "Run the setup kit: ./scripts/install-tools.sh",
        "terraform": "brew tap hashicorp/tap && brew install hashicorp/tap/terraform (needed in Part 5, M11)",
        "helm": "brew install helm (only for the Helm path in Part 5)",
        "python": "brew install python@3.12, then use python3.12 instead of python3",
    },
    "Linux": {
        "docker": "Install Docker Engine in Ubuntu (docs/GUIDE.md, Windows by hand, step 5)",
        "minikube": "See docs/GUIDE.md, Windows by hand (WSL2 and Ubuntu)",
        "kubectl": "See docs/GUIDE.md, Windows by hand (WSL2 and Ubuntu)",
        "git": "sudo apt-get install -y git",
        "gh": "See docs/GUIDE.md, Windows by hand (WSL2 and Ubuntu)",
        "terraform": "See docs/labs/05-automation-iac-cicd.md, M11 step 1 (needed in Part 5)",
        "helm": "See docs/GUIDE.md (only for the Helm path in Part 5)",
        "python": "sudo apt-get install -y python3 python3-venv",
    },
}

SITES = [
    ("github.com", "https://github.com"),
    ("ntfy.sh (phone alerts)", "https://ntfy.sh"),
]

NETWORK_FIX = ("Open the address in your browser. If it fails only on the VPN, try off the VPN (if your IBM policy "
               "allows) or ask IT to allow it (docs/IT-REQUEST.md). Behind a proxy, set HTTPS_PROXY.")


# ------------------------------------------------------------------------------------------- pure checks
def install_hint(system, tool):
    return INSTALL.get(system, INSTALL["Linux"]).get(tool, "See docs/GUIDE.md step 2")


def parse_version(text):
    """Return the first version number in text as a tuple of ints, for example 'v1.31.0' -> (1, 31, 0)."""
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text or "")
    if not match:
        return None
    return tuple(int(part) for part in match.groups() if part is not None)


def short_version(text):
    version = parse_version(text)
    return ".".join(str(part) for part in version) if version else (text or "").strip()[:40]


def os_release(system, release, version):
    """Windows 11 still reports release '10'; build 22000 or newer is Windows 11."""
    if system == "Windows":
        build = parse_version(version)
        if build and len(build) == 3 and build[2] >= 22000:
            return "11 (build {})".format(build[2])
        return "{} (build {})".format(release, build[2]) if build and len(build) == 3 else release
    return release


def check_os(system, release, machine):
    name = {"Darwin": "macOS", "Windows": "Windows", "Linux": "Linux"}.get(system, system or "unknown")
    found = "{} {} ({})".format(name, release, machine).strip()
    if system in ("Windows", "Darwin", "Linux"):
        return Result("PASS", "Operating system", found, "")
    return Result("FAIL", "Operating system", found, "The lab supports Windows 10/11, macOS and Linux (Ubuntu).")


def check_python(version_info, system):
    version = tuple(version_info[:3])
    found = ".".join(str(part) for part in version)
    if version[:2] > PYTHON_ANSIBLE_MAX:
        return Result("WARN", "Python", found, "Fine for the lab scripts, but Ansible in Part 5 (M10) needs Python "
                      "3.10 to 3.12. Also install 3.12: " + install_hint(system, "python"))
    if version[:2] >= PYTHON_MIN:
        return Result("PASS", "Python", found, "")
    return Result("FAIL", "Python", found, "Python 3.10 or newer is needed. " + install_hint(system, "python"))


def check_python_location(executable, system):
    """On Windows, the Microsoft Store 'python' alias is a trap: it opens the Store instead of Python."""
    if system == "Windows" and "WindowsApps" in (executable or ""):
        return Result("WARN", "Python location", executable,
                      "This is the Microsoft Store copy. Prefer: " + install_hint(system, "python"))
    return None


def check_ram(total_bytes):
    if not total_bytes:
        return Result("WARN", "Memory (RAM)", "unknown",
                      "Could not read the memory size. You need 8 GB, 16 GB is better.")
    gib = total_bytes / float(GIB)
    found = "{:.1f} GB".format(gib)
    if gib < RAM_MIN_GIB:
        return Result("FAIL", "Memory (RAM)", found, "The core stack needs an 8 GB laptop. Pair with a classmate "
                      "who has 16 GB, or ask for a lab machine.")
    if gib < RAM_GOOD_GIB:
        return Result("WARN", "Memory (RAM)", found, "8 GB profile: core stack only. Watch the add-on modules as an "
                      "instructor demo (docs/labs/README.md, Laptop profiles).")
    return Result("PASS", "Memory (RAM)", found, "")


def check_disk(free_bytes):
    gb = free_bytes / float(GIB)
    found = "{:.0f} GB free".format(gb)
    if gb < DISK_MIN_GB:
        return Result("FAIL", "Free disk", found, "Free at least 20 GB (25 GB is better): empty Downloads and the "
                      "Recycle Bin or Trash, or move large files to OneDrive or Box.")
    if gb < DISK_GOOD_GB:
        return Result("WARN", "Free disk", found, "Enough to start. Free a few more GB: the container images grow.")
    return Result("PASS", "Free disk", found, "")


def check_cpus(count):
    if not count:
        return Result("WARN", "CPU cores", "unknown", "Could not count the CPU cores. Minikube needs at least 2.")
    if count < 2:
        return Result("FAIL", "CPU cores", str(count), "Minikube needs at least 2 CPU cores.")
    if count < 4:
        return Result("WARN", "CPU cores", str(count), "It works, but deploys are slow. Close other apps first.")
    return Result("PASS", "CPU cores", str(count), "")


def check_tool(name, path, version_text, system, needed="core"):
    if not path:
        status = "TODO"
        fix = install_hint(system, name)
        if needed == "optional":
            fix = "Optional. " + fix
        return Result(status, name, "not installed", fix)
    if version_text is None:
        return Result("WARN", name, "found, but it did not print a version",
                      "Open a new terminal and run '{} --version'. Reinstall it if it fails.".format(name))
    return Result("PASS", name, short_version(version_text), "")


def check_docker_engine(cli_found, engine_ok, detail, system):
    if not cli_found:
        return Result("TODO", "Container engine running", "no docker command", install_hint(system, "docker"))
    if engine_ok:
        return Result("PASS", "Container engine running", "server " + short_version(detail), "")
    start = {
        "Windows": "Start Rancher Desktop or Docker Desktop from the Start menu and wait until it says it is running.",
        "Darwin": "Run: colima start --cpu 4 --memory 6 --disk 60 (8 GB Mac: --cpu 2 --memory 4).",
    }.get(system, "Run: sudo service docker start (or close and reopen the Ubuntu window).")
    return Result("WARN", "Container engine running", "not responding", start)


def check_execution_policy(policies):
    """policies: dict scope -> policy, from 'Get-ExecutionPolicy -List'.

    The lab runs every script with '-ExecutionPolicy Bypass', which works unless a Group Policy (MachinePolicy or
    UserPolicy) forces a stricter setting.
    """
    if not policies:
        return Result("WARN", "PowerShell script policy", "unknown",
                      "Could not read it. If scripts\\*.ps1 are blocked, show docs/IT-REQUEST.md to IT.")
    forced = [(scope, value) for scope, value in policies.items()
              if scope in ("MachinePolicy", "UserPolicy") and value not in ("Undefined", "")]
    effective = ", ".join("{}={}".format(scope, value) for scope, value in policies.items() if value != "Undefined")
    found = effective or "all Undefined (Restricted by default)"
    blocking = [item for item in forced if item[1] in ("Restricted", "AllSigned")]
    if blocking:
        return Result("FAIL", "PowerShell script policy", found,
                      "A company policy blocks unsigned scripts, so -ExecutionPolicy Bypass will not work. "
                      "Ask IT for an exception (docs/IT-REQUEST.md), or use the WSL2 and Ubuntu path.")
    return Result("PASS", "PowerShell script policy", found, "")


def parse_execution_policy_list(text):
    policies = collections.OrderedDict()
    for line in (text or "").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] not in ("Scope", "-----"):
            policies[parts[0]] = parts[1]
    return policies


def check_wsl(returncode, output):
    """Docker Desktop and Rancher Desktop both run on WSL2 on Windows."""
    text = (output or "").lower()
    if returncode is None:
        return Result("TODO", "WSL2", "not found",
                      "Rancher Desktop or Docker Desktop installs it (needs admin rights and a restart). "
                      "See docs/IT-REQUEST.md.")
    if returncode == 0 and ("default version: 2" in text or "wsl 2" in text or "wsl version" in text or not text):
        return Result("PASS", "WSL2", "installed", "")
    if returncode == 0:
        return Result("WARN", "WSL2", "installed, version unclear",
                      "Run 'wsl --status' and check it says version 2.")
    return Result("TODO", "WSL2", "not enabled",
                  "Rancher Desktop or Docker Desktop turns it on during install (admin rights and a restart). "
                  "See docs/IT-REQUEST.md.")


def check_mac(machine, brew_on_path, brew_exists_at):
    """Apple silicon keeps Homebrew in /opt/homebrew, which is not on PATH until 'brew shellenv' runs."""
    chip = "Apple silicon" if machine == "arm64" else "Intel"
    if brew_on_path:
        return Result("PASS", "Homebrew", "{} ({})".format(brew_on_path, chip), "")
    if brew_exists_at:
        return Result("WARN", "Homebrew", "installed at {} but not on PATH ({})".format(brew_exists_at, chip),
                      "Run: eval \"$({} shellenv)\" and add the same line to ~/.zprofile, "
                      "then open a new Terminal.".format(brew_exists_at))
    return Result("TODO", "Homebrew", "not installed ({})".format(chip),
                  "Install it from https://brew.sh (docs/GUIDE.md, Mac step 1).")


def check_site(name, ok, detail):
    if ok:
        return Result("PASS", "Reach " + name, "ok", "")
    return Result("WARN", "Reach " + name, detail or "no answer", NETWORK_FIX)


def summarize(results):
    counts = collections.Counter(result.status for result in results)
    return counts, (1 if counts.get("FAIL") else 0)


def format_table(results, width=100):
    """Plain ASCII table (PowerShell 5.1 consoles do not always show other characters)."""
    name_w = max([len(r.name) for r in results] + [5])
    found_w = min(max([len(r.found) for r in results] + [5]), 34)
    lines = ["{:<6}{:<{nw}}  {:<{fw}}".format("", "Check", "Found", nw=name_w, fw=found_w),
             "-" * min(width, 6 + name_w + 2 + found_w)]
    for r in results:
        found = r.found if len(r.found) <= found_w else r.found[:found_w - 3] + "..."
        lines.append("{:<6}{:<{nw}}  {:<{fw}}".format(r.status, r.name, found, nw=name_w, fw=found_w))
        if r.fix:
            lines.append("{}-> {}".format(" " * 6, r.fix))
    return "\n".join(lines)


# ----------------------------------------------------------------------------------- read-only probes
def run(cmd, timeout=15):
    """Run a read-only command. Returns (returncode, text) or (None, '') when it cannot start."""
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None, ""
    raw = proc.stdout or b""
    # wsl.exe writes UTF-16; everything else writes UTF-8 or the console code page.
    text = raw.decode("utf-16-le", "replace") if b"\x00" in raw else raw.decode("utf-8", "replace")
    return proc.returncode, text.replace("\x00", "")


def total_ram_bytes(system):
    try:
        if system == "Windows":
            class MemoryStatus(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(MemoryStatus)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys)
            return None
        if system == "Darwin":
            code, out = run(["sysctl", "-n", "hw.memsize"])
            return int(out.strip()) if code == 0 else None
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, ValueError, OSError):
        return None


def tool_version(cmd):
    code, out = run(cmd)
    if code is None or code != 0 or not out.strip():
        return None
    return out.strip().splitlines()[0]


def docker_engine():
    code, out = run(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=20)
    text = out.strip()
    return code == 0 and bool(parse_version(text)), text


def reach(url, timeout=8):
    if not url.startswith("https://"):
        raise ValueError("preflight only checks fixed https addresses")
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "sre-lab-preflight"})
    try:
        urllib.request.urlopen(request, timeout=timeout).close()  # nosec B310: https only, checked above
        return True, ""
    except urllib.error.HTTPError as error:
        # The site answered, so the network path works (some sites refuse HEAD requests).
        return True, "HTTP {}".format(error.code)
    except Exception as error:  # noqa: BLE001 - any failure means "not reachable", with the reason shown
        reason = getattr(error, "reason", error)
        return False, str(reason)[:60]


def gather(no_network=False):
    system = platform.system()
    # On a Mac, platform.release() is the Darwin kernel number (for example 24.1.0); mac_ver() is the macOS version.
    release = (platform.mac_ver()[0] or platform.release()) if system == "Darwin" else platform.release()
    results = [check_os(system, os_release(system, release, platform.version()), platform.machine()),
               check_python(sys.version_info, system)]
    location = check_python_location(sys.executable, system)
    if location:
        results.append(location)
    results.append(check_ram(total_ram_bytes(system)))
    results.append(check_disk(shutil.disk_usage(os.path.expanduser("~")).free))
    results.append(check_cpus(os.cpu_count()))

    if system == "Darwin":
        brew_at = next((p for p in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew") if os.path.exists(p)), None)
        results.append(check_mac(platform.machine(), shutil.which("brew"), brew_at))
    if system == "Windows":
        code, out = run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                         "Get-ExecutionPolicy -List | Format-Table -HideTableHeaders Scope,ExecutionPolicy"])
        results.append(check_execution_policy(parse_execution_policy_list(out) if code == 0 else {}))
        if shutil.which("wsl"):
            code, out = run(["wsl", "--status"])
            results.append(check_wsl(code, out))
        else:
            results.append(check_wsl(None, ""))

    for name, (needed, cmd) in TOOLS.items():
        path = shutil.which(name)
        results.append(check_tool(name, path, tool_version(cmd) if path else None, system, needed))
    if system == "Darwin":
        path = shutil.which("colima")
        version = tool_version(["colima", "version"]) if path else None
        results.append(check_tool("colima", path, version, system, "core"))

    cli = bool(shutil.which("docker"))
    engine_ok, detail = docker_engine() if cli else (False, "")
    results.append(check_docker_engine(cli, engine_ok, detail, system))

    if not no_network:
        for name, url in SITES:
            ok, detail = reach(url)
            results.append(check_site(name, ok, detail))
    return results


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(description="Read-only laptop check for the SRE Academy lab.")
    parser.add_argument("--no-network", action="store_true", help="skip the website checks")
    args = parser.parse_args(argv)

    print("SRE Academy lab: preflight check (read-only, changes nothing)\n")
    results = gather(no_network=args.no_network)
    print(format_table(results))
    counts, code = summarize(results)
    print("\nSummary: {} PASS, {} WARN, {} TODO, {} FAIL".format(
        counts.get("PASS", 0), counts.get("WARN", 0), counts.get("TODO", 0), counts.get("FAIL", 0)))
    if counts.get("FAIL"):
        print("FAIL: this laptop needs a fix before the lab. Show this output to your professor or IT "
              "(docs/IT-REQUEST.md).")
    elif counts.get("TODO"):
        print("Next: install the TODO tools with docs/GUIDE.md step 2 (or let IBM Bob do it), then run this again.")
    else:
        print("Ready. Next: docs/GUIDE.md step 3, or Part 1 of the lab (docs/labs/01-foundations.md).")
    return code


if __name__ == "__main__":
    sys.exit(main())
