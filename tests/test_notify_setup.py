"""Tests for scripts/notify_setup.py: it edits only the ntfy-url line of the private secret file."""

import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import notify_setup  # noqa: E402


def test_write_ntfy_url_changes_only_that_line(tmp_path, monkeypatch):
    secret = tmp_path / "alertmanager-secret.yaml"
    secret.write_text('stringData:\n  slack-webhook-url: "keep-me"\n  ntfy-url: "http://old.invalid/"\n',
                      encoding="utf-8")
    monkeypatch.setattr(notify_setup, "SECRET_FILE", secret)
    url = notify_setup.topic_url("sre-lab-test")
    notify_setup.write_ntfy_url(url)
    text = secret.read_text(encoding="utf-8")
    assert 'slack-webhook-url: "keep-me"' in text
    assert notify_setup.read_ntfy_url() == url
    assert text.count("ntfy-url:") == 1


def test_write_ntfy_url_creates_file_and_adds_missing_key(tmp_path, monkeypatch):
    example = tmp_path / "example.yaml"
    example.write_text('stringData:\n  smtp-auth-password: "x"\n', encoding="utf-8")
    monkeypatch.setattr(notify_setup, "EXAMPLE_FILE", example)
    monkeypatch.setattr(notify_setup, "SECRET_FILE", tmp_path / "secret.yaml")
    monkeypatch.setattr(notify_setup, "ROOT", tmp_path)
    notify_setup.write_ntfy_url(notify_setup.OFF_URL)
    assert notify_setup.read_ntfy_url() == notify_setup.OFF_URL


def test_topic_url_uses_alertmanager_templates():
    url = notify_setup.topic_url("sre-lab-abc")
    assert url.startswith("https://ntfy.sh/sre-lab-abc?") and "tpl=yes" in url and "commonLabels" in url
