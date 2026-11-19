"""Tests for scripts/preflight.py: the pure check functions, with fake platform values (no real probes)."""

import os
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import preflight  # noqa: E402

GIB = 1024 ** 3


@pytest.mark.parametrize("text, expected", [
    ("Docker version 27.3.1, build ce12230", (27, 3, 1)),
    ("Client Version: v1.31.0", (1, 31, 0)),
    ("v1.34.0", (1, 34, 0)),
    ("git version 2.47.1.windows.1", (2, 47, 1)),
    ("Python 3.9", (3, 9)),
    ("no numbers here", None),
    (None, None),
])
def test_parse_version(text, expected):
    assert preflight.parse_version(text) == expected


@pytest.mark.parametrize("version, status", [((3, 9, 6), "FAIL"), ((3, 10, 0), "PASS"), ((3, 12, 7), "PASS"),
                                             ((3, 13, 1), "WARN")])
def test_python_version(version, status):
    assert preflight.check_python(version, "Darwin").status == status


def test_new_python_warns_about_ansible():
    result = preflight.check_python((3, 13, 1), "Windows")
    assert "Ansible" in result.fix and "Python.Python.3.12" in result.fix


def test_terraform_is_checked_with_an_install_hint():
    assert "terraform" in preflight.TOOLS
    assert "Hashicorp.Terraform" in preflight.check_tool("terraform", None, None, "Windows").fix
    assert "hashicorp/tap/terraform" in preflight.check_tool("terraform", None, None, "Darwin").fix


def test_old_python_on_mac_points_to_brew():
    assert "brew install python@3.12" in preflight.check_python((3, 9, 6), "Darwin").fix


def test_store_python_on_windows_is_a_warning():
    store = r"C:\Users\x\AppData\Local\Microsoft\WindowsApps\python.exe"
    assert preflight.check_python_location(store, "Windows").status == "WARN"
    assert preflight.check_python_location(r"C:\Python312\python.exe", "Windows") is None
    assert preflight.check_python_location(store, "Darwin") is None


@pytest.mark.parametrize("gib, status", [(4, "FAIL"), (7.8, "WARN"), (8, "WARN"), (15.7, "PASS"), (32, "PASS")])
def test_ram_thresholds(gib, status):
    assert preflight.check_ram(int(gib * GIB)).status == status


def test_ram_unknown_is_a_warning():
    assert preflight.check_ram(None).status == "WARN"


@pytest.mark.parametrize("gb, status", [(8, "FAIL"), (19.5, "FAIL"), (22, "WARN"), (25, "PASS"), (200, "PASS")])
def test_disk_thresholds(gb, status):
    assert preflight.check_disk(int(gb * GIB)).status == status


@pytest.mark.parametrize("count, status", [(None, "WARN"), (1, "FAIL"), (2, "WARN"), (4, "PASS"), (12, "PASS")])
def test_cpu_thresholds(count, status):
    assert preflight.check_cpus(count).status == status


def test_os_names():
    assert preflight.check_os("Darwin", "24.1.0", "arm64").found.startswith("macOS")
    assert preflight.check_os("Windows", "11", "AMD64").status == "PASS"
    assert preflight.check_os("SunOS", "5.11", "sparc").status == "FAIL"


def test_windows_11_is_recognised_from_the_build():
    assert preflight.os_release("Windows", "10", "10.0.26200").startswith("11")
    assert preflight.os_release("Windows", "10", "10.0.19045").startswith("10")
    assert preflight.os_release("Darwin", "24.1.0", "whatever") == "24.1.0"


def test_missing_tool_is_todo_with_install_command():
    windows = preflight.check_tool("minikube", None, None, "Windows")
    assert windows.status == "TODO" and "install-tools.ps1" in windows.fix
    mac = preflight.check_tool("kubectl", None, None, "Darwin")
    assert "install-tools.sh" in mac.fix


def test_optional_tool_says_optional_once_and_is_not_a_todo():
    for name in ("helm", "terraform"):
        assert preflight.TOOLS[name][0] == "optional"
        result = preflight.check_tool(name, None, None, "Windows", "optional")
        assert result.status == "WARN" and "not needed for your first shift" in result.fix
        assert result.fix.count("Optional") == 1, result.fix


def test_tool_in_tools_bin_but_not_on_path_says_open_a_new_terminal():
    stale = r"C:\Users\x\tools\bin\minikube.exe"
    result = preflight.check_tool("minikube", None, None, "Windows", "core", stale)
    assert result.status == "WARN" and "old PATH: open a new terminal" in result.fix
    assert r"found in tools\bin" in result.fix
    # When the tool is on PATH, the copy in tools\bin does not matter.
    assert preflight.check_tool("minikube", r"C:\x\minikube.exe", "v1.34.0", "Windows", "core", stale).status == "PASS"


def test_tools_bin_copy_is_found_only_on_windows(tmp_path):
    (tmp_path / "tools" / "bin").mkdir(parents=True)
    (tmp_path / "tools" / "bin" / "gh.exe").write_bytes(b"")
    assert preflight.tools_bin_copy("gh", "Windows", str(tmp_path)).endswith("gh.exe")
    assert preflight.tools_bin_copy("helm", "Windows", str(tmp_path)) is None
    assert preflight.tools_bin_copy("gh", "Darwin", str(tmp_path)) is None


def test_gather_reports_a_stale_path(monkeypatch, tmp_path):
    (tmp_path / "tools" / "bin").mkdir(parents=True)
    (tmp_path / "tools" / "bin" / "kubectl.exe").write_bytes(b"")
    monkeypatch.setattr(preflight.platform, "system", lambda: "Windows")
    monkeypatch.setattr(preflight.shutil, "which", lambda name: None)
    monkeypatch.setattr(preflight.os.path, "expanduser", lambda path: str(tmp_path))
    monkeypatch.setattr(preflight, "run", lambda *a, **k: (None, ""))
    monkeypatch.setattr(preflight, "total_ram_bytes", lambda system: 16 * GIB)
    rows = {r.name: r for r in preflight.gather(no_network=True)}
    assert rows["kubectl"].status == "WARN" and "open a new terminal" in rows["kubectl"].fix
    assert rows["minikube"].status == "TODO"
    assert rows["terraform"].status == "WARN" and "first shift" in rows["terraform"].fix


def test_present_tool_shows_short_version():
    result = preflight.check_tool("docker", "/usr/bin/docker", "Docker version 27.3.1, build ce12230", "Linux")
    assert result.status == "PASS" and result.found == "27.3.1"


def test_tool_without_version_is_a_warning():
    assert preflight.check_tool("gh", "/usr/bin/gh", None, "Linux").status == "WARN"


def test_docker_engine_states():
    assert preflight.check_docker_engine(False, False, "", "Windows").status == "TODO"
    assert preflight.check_docker_engine(True, True, "27.3.1", "Windows").status == "PASS"
    stopped = preflight.check_docker_engine(True, False, "", "Darwin")
    assert stopped.status == "WARN" and "colima start" in stopped.fix


def test_execution_policy_parsing_and_group_policy_block():
    text = "MachinePolicy    AllSigned\nUserPolicy       Undefined\nProcess          Undefined\n" \
           "CurrentUser      RemoteSigned\nLocalMachine     Undefined\n"
    policies = preflight.parse_execution_policy_list(text)
    assert policies["MachinePolicy"] == "AllSigned"
    assert preflight.check_execution_policy(policies).status == "FAIL"


def test_execution_policy_local_restricted_is_fine_because_scripts_use_bypass():
    policies = preflight.parse_execution_policy_list("MachinePolicy Undefined\nLocalMachine Restricted\n")
    assert preflight.check_execution_policy(policies).status == "PASS"
    assert preflight.check_execution_policy({}).status == "WARN"


@pytest.mark.parametrize("code, output, status", [
    (None, "", "TODO"),
    (0, "Default Version: 2\nWSL version: 2.3.26.0", "PASS"),
    (0, "Default Version: 1", "WARN"),
    (1, "The Windows Subsystem for Linux is not installed.", "TODO"),
])
def test_wsl_states(code, output, status):
    assert preflight.check_wsl(code, output).status == status


def test_homebrew_on_apple_silicon():
    assert preflight.check_mac("arm64", "/opt/homebrew/bin/brew", "/opt/homebrew/bin/brew").status == "PASS"
    missing_path = preflight.check_mac("arm64", None, "/opt/homebrew/bin/brew")
    assert missing_path.status == "WARN" and "shellenv" in missing_path.fix and "Apple silicon" in missing_path.found
    assert preflight.check_mac("x86_64", None, None).status == "TODO"


def test_site_unreachable_gives_vpn_hint():
    result = preflight.check_site("github.com", False, "timed out")
    assert result.status == "WARN" and "VPN" in result.fix
    assert preflight.check_site("github.com", True, "").status == "PASS"


def test_summary_exit_code_only_fails_on_fail():
    ok = [preflight.Result("PASS", "a", "x", ""), preflight.Result("TODO", "b", "y", "z")]
    assert preflight.summarize(ok)[1] == 0
    assert preflight.summarize(ok + [preflight.Result("FAIL", "c", "y", "z")])[1] == 1


def test_table_is_plain_ascii_and_shows_fixes():
    table = preflight.format_table([preflight.Result("FAIL", "Free disk", "8 GB free", "Free 20 GB"),
                                    preflight.Result("PASS", "Python", "3.12.7", "")])
    table.encode("ascii")
    assert "-> Free 20 GB" in table and "PASS" in table
