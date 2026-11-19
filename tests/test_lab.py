"""Tests for the lab game engine (scripts/lab.py) and its mission catalog (lab/missions.json)."""

import json
import os
import re
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import lab  # noqa: E402


@pytest.fixture
def catalog():
    return lab.load_catalog()


def test_catalog_ids_are_unique_and_checks_exist(catalog):
    ids = [m["id"] for m in catalog["missions"]]
    assert len(ids) == len(set(ids))
    for mission in catalog["missions"]:
        assert mission["check"].split(":")[0] in lab.CHECKS, mission["id"]
        assert mission["kind"] in ("core", "addon", "capstone", "portfolio")
        assert os.path.exists(os.path.join(ROOT, mission["guide"])), mission["guide"]


def test_quiz_answers_are_hashed_not_plain(catalog):
    for mission in catalog["missions"]:
        for question in mission["quiz"]:
            assert re.fullmatch(r"[0-9a-f]{16}", question["answer"])
            assert len(question["options"]) >= 2


def test_levels_and_xp(catalog):
    assert lab.level_of(catalog, 0)[0]["name"] == "Career Changer"
    progress = {"missions": {"M00": {}, "M05": {}}, "quiz": {"M00:1": True}}
    assert lab.xp_of(catalog, progress) == 100 + 150 + catalog["quiz_xp"]
    top = max(level["xp"] for level in catalog["levels"])
    assert lab.level_of(catalog, top + 1)[1] is None


def test_wrong_answer_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(lab, "PROGRESS", tmp_path / "progress.json")
    args = type("Args", (), {"mission": "B00", "number": 1, "choice": "z"})()
    assert lab.cmd_answer(args) == 1
    assert not json.loads((tmp_path / "progress.json").read_text())["quiz"] if (tmp_path / "progress.json").exists() \
        else True


def test_checks_never_crash_without_a_cluster(monkeypatch):
    monkeypatch.setattr(lab, "run", lambda *a, **k: (127, ""))
    for mission in lab.load_catalog()["missions"]:
        result = lab.run_check(mission["check"])
        assert set(result) == {"ok", "detail"}


def test_proof_writes_passport_badge_and_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(lab, "PROGRESS", tmp_path / "progress.json")
    monkeypatch.setattr(lab, "PROOF_DIR", tmp_path / "proof")
    monkeypatch.setattr(lab, "_origin_repo", lambda: "student/sre-final-project")
    lab.save_progress({"missions": {"M00": {"completed": "2027-01-10T10:00:00+00:00", "evidence": "11/11 pods ready"}},
                       "quiz": {}})
    lab.cmd_proof(type("Args", (), {"name": "Test Student"})())
    passport = (tmp_path / "proof" / "PASSPORT.md").read_text(encoding="utf-8")
    assert "Test Student" in passport and "M00" in passport
    assert (tmp_path / "proof" / "badge.svg").read_text(encoding="utf-8").startswith("<svg")
    assert len(json.loads((tmp_path / "proof" / "evidence.json").read_text())["sha256"]) == 64


def test_one_journey_every_camp_teaches_a_principle(catalog):
    assert "tracks" not in catalog
    for zone in catalog["zones"]:
        assert zone["principle"] and zone["skills"] and zone["interview"]
    portfolio = [m for m in catalog["missions"] if m["kind"] == "portfolio"]
    assert len(portfolio) == 4 and all(m["needs"] is None for m in portfolio)


def test_quiz_attempts_are_limited(tmp_path, monkeypatch):
    monkeypatch.setattr(lab, "PROGRESS", tmp_path / "progress.json")
    args = type("Args", (), {"mission": "B00", "number": 1, "choice": "z"})()
    assert lab.cmd_answer(args) == 1
    assert lab.cmd_answer(args) == 1
    args.choice = "b"  # the right answer is refused once the question is locked
    assert lab.cmd_answer(args) == 1
    progress = lab.load_progress()
    assert not progress["quiz"] and lab.quiz_settled(lab.load_catalog(), progress, "B00:1")


def test_second_try_gives_half_xp(tmp_path, monkeypatch):
    monkeypatch.setattr(lab, "PROGRESS", tmp_path / "progress.json")
    catalog = lab.load_catalog()
    args = type("Args", (), {"mission": "B00", "number": 1, "choice": "a"})()
    lab.cmd_answer(args)
    args.choice = "b"
    assert lab.cmd_answer(args) == 0
    assert lab.xp_of(catalog, lab.load_progress()) == catalog["quiz_xp"] // 2


def test_cohort_report_summarizes_the_class(tmp_path, monkeypatch):
    import cohort_report
    monkeypatch.setattr(lab, "PROGRESS", tmp_path / "progress.json")
    monkeypatch.setattr(lab, "PROOF_DIR", tmp_path / "proof")
    monkeypatch.setattr(lab, "_origin_repo", lambda: "student/sre-final-project")
    lab.save_progress({"missions": {"M00": {"completed": "2027-01-10T10:00:00+00:00", "evidence": "ok"}},
                       "quiz": {}})
    lab.cmd_proof(type("Args", (), {"name": "Student A"})())
    text = cohort_report.report(cohort_report.load(tmp_path / "proof"), lab.load_catalog())
    assert "1 students" in text and "| ok |" in text
