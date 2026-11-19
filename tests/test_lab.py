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
        assert os.path.exists(os.path.join(ROOT, mission["guide"].split("#")[0])), mission["guide"]


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

    def offline(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr(lab, "_http_get", offline)
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
    assert "## Privacy" in passport and "lab.py verify" in passport and "Docker containers (M00)" in passport


def test_one_journey_every_camp_teaches_a_principle(catalog):
    assert "tracks" not in catalog
    ids = {m["id"] for m in catalog["missions"]}
    for zone in catalog["zones"]:
        assert zone["principle"] and zone["skills"] and zone["interview"]
        for skill in zone["skills"]:
            assert skill["skill"] and skill["proof"] and set(skill["proof"]) <= ids, skill
        assert [q["kind"] for q in zone["interview"]] == ["concept", "judgement", "behavioural"], zone["name"]
        assert all(q["question"].strip() for q in zone["interview"])
        assert zone["interview"][2]["evidence"] and set(zone["interview"][2]["evidence"]) <= ids
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


def test_skills_need_their_proof_missions_not_a_cleared_camp(catalog):
    def earned(*done):
        progress = {"missions": {mid: {} for mid in done}, "quiz": {}}
        return {s["skill"]: s["proof"] for _, won in lab.skills_earned(catalog, progress) for s in won}

    assert earned() == {}
    assert set(earned("B00")) == {"Working safely with an AI coding agent (IBM Bob, Claude Code or similar)",
                                  "Reviewing and approving commands before they run"}
    only_rollback = earned("M14")  # camp 6 is far from cleared, but the mission that proves the skill is done
    assert only_rollback == {"Rollbacks": ["M14"]}
    assert "Kubernetes basics: pods, deployments, services, probes" not in earned("M00")  # needs M02 too
    assert "Kubernetes basics: pods, deployments, services, probes" in earned("M00", "M02")
    every_core = [m["id"] for m in catalog["missions"] if m["kind"] in ("core", "capstone")]
    assert "GitOps with ArgoCD" not in earned(*every_core)  # only the add-on M13 proves it
    assert lab.proof_label(catalog, ["M13"]) == "M13 (add-on)"


def test_old_catalog_shape_still_works(catalog):
    legacy = dict(catalog, zones=[dict(z, skills=["Old skill"], interview="Old question?") for z in catalog["zones"]])
    progress = {"missions": {"B00": {}}, "quiz": {}}
    earned = [(z["part"], [s["skill"] for s in won]) for z, won in lab.skills_earned(legacy, progress)]
    assert earned == [(0, ["Old skill"])]
    assert lab.zone_questions(legacy["zones"][0]) == [{"kind": "concept", "question": "Old question?"}]


def test_cv_and_mission_control_show_the_proof(tmp_path, monkeypatch, capsys, catalog):
    import lab_ui
    monkeypatch.setattr(lab, "PROGRESS", tmp_path / "progress.json")
    lab.save_progress({"missions": {"B00": {}, "M14": {}}, "quiz": {}})
    lab.cmd_cv(None)
    out = capsys.readouterr().out
    assert "Rollbacks (proved by M14)" in out and "[behavioural]" in out and "Docker" not in out
    page = lab_ui.career(catalog, lab.load_progress(), {0})
    assert "Rollbacks" in page and "M14" in page and "Tell me about a time" in page


def test_rank_names_do_not_over_promise(catalog):
    names = [level["name"] for level in catalog["levels"]]
    assert "Junior SRE Lab Graduate" in names and not any("Interview-Ready" in n for n in names)


def test_default_journey_is_a_short_first_shift(catalog):
    journey = lab.default_journey(catalog)
    assert journey and journey["default"] is True and journey["achievement"]
    ids = {m["id"] for m in catalog["missions"]}
    steps = [s["mission"] for s in journey["steps"]]
    assert set(steps) <= ids and len(steps) == len(set(steps))
    assert 150 <= sum(s["minutes"] for s in journey["steps"]) <= 180
    assert lab.default_journey({"missions": []}) is None and lab.journey_state({"missions": []}, {}) is None


def test_next_mission_follows_the_journey(catalog):
    steps = [s["mission"] for s in lab.default_journey(catalog)["steps"]]
    progress = {"missions": {}, "quiz": {}}
    for step in steps:
        assert lab.next_mission(catalog, progress)["id"] == step
        progress["missions"][step] = {}
    after = lab.next_mission(catalog, progress)  # the journey is done: back to the rest of the lab
    assert after is not None and after["id"] not in steps
    state = lab.journey_state(catalog, progress)
    assert state["complete"] and state["minutes_left"] == 0


def test_journey_completion_is_recorded(tmp_path, monkeypatch, capsys, catalog):
    import lab_ui
    monkeypatch.setattr(lab, "PROGRESS", tmp_path / "progress.json")
    monkeypatch.setattr(lab, "PROOF_DIR", tmp_path / "proof")
    monkeypatch.setattr(lab, "_origin_repo", lambda: None)
    monkeypatch.setattr(lab, "run_check", lambda spec: lab.evidence(True, "test evidence"))
    journey = lab.default_journey(catalog)
    steps = [s["mission"] for s in journey["steps"]]
    lab.save_progress({"missions": {mid: {"completed": "2027-01-10T10:00:00+00:00", "evidence": "ok"}
                                    for mid in steps[:-1]}, "quiz": {}})
    assert lab.cmd_check(type("Args", (), {"mission": steps[-1], "all": False})()) == 0
    out = capsys.readouterr().out
    assert "SHIFT COMPLETE" in out and journey["achievement"] in out and "Keep exploring" in out
    progress = lab.load_progress()
    assert journey["id"] in progress["journeys"] and lab.xp_of(catalog, progress) >= 0
    assert journey["achievement"] in lab.journey_achievements(catalog, progress)
    lab.cmd_check(type("Args", (), {"mission": steps[-1], "all": False})())  # no second banner
    assert "SHIFT COMPLETE" not in capsys.readouterr().out
    lab.cmd_journey(None)
    assert "Journey complete" in capsys.readouterr().out
    lab.cmd_proof(type("Args", (), {"name": "Test Student"})())
    evidence = json.loads((tmp_path / "proof" / "evidence.json").read_text())
    assert journey["id"] in evidence["journeys"]
    assert journey["name"] in (tmp_path / "proof" / "PASSPORT.md").read_text(encoding="utf-8")
    page = lab_ui.render(catalog, progress, 0, catalog["levels"][0], None, None, "now")
    assert "SHIFT COMPLETE" in page and "Keep exploring" in page


def test_status_shows_the_journey_first(tmp_path, monkeypatch, capsys, catalog):
    monkeypatch.setattr(lab, "PROGRESS", tmp_path / "progress.json")
    lab.cmd_status(None)
    out = capsys.readouterr().out
    journey = lab.default_journey(catalog)
    assert out.startswith(journey["name"]) and "minutes left" in out


def test_phone_push_check_never_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(lab, "NTFY_SECRET", tmp_path / "missing.yaml")
    result = lab.check_phone_push()
    assert result["ok"] is False and "notify_setup.py" in result["detail"]

    secret = tmp_path / "alertmanager-secret.yaml"
    monkeypatch.setattr(lab, "NTFY_SECRET", secret)
    secret.write_text('stringData:\n  ntfy-url: "http://ntfy-not-configured.invalid/"\n', encoding="utf-8")
    assert lab.check_phone_push()["ok"] is False

    secret.write_text('stringData:\n  ntfy-url: "https://ntfy.sh/sre-lab-secrettopic?tpl=yes"\n', encoding="utf-8")
    seen = []

    def offline(url, timeout=10):
        seen.append(url)
        raise OSError("offline")

    monkeypatch.setattr(lab, "_http_get", offline)
    result = lab.check_phone_push()
    assert result["ok"] is False and "sre-lab-secrettopic" not in result["detail"]
    assert seen == ["https://ntfy.sh/sre-lab-secrettopic/json?poll=1&since=24h"]

    monkeypatch.setattr(lab, "_http_get", lambda url, timeout=10: '{"event":"open"}\n'
                        '{"event":"message","title":"[test] info: LabConnected"}\n')
    assert lab.check_phone_push()["ok"] is False
    monkeypatch.setattr(lab, "_http_get", lambda url, timeout=10: 'not json\n'
                        '{"event":"message","title":"[firing] critical: HighErrorRate"}\n')
    result = lab.check_phone_push()
    assert result["ok"] is True and "sre-lab-secrettopic" not in result["detail"]


def test_shipped_postmortem_does_not_clear_m09_or_m27(tmp_path, monkeypatch, catalog):
    """A fresh clone has only the author's postmortem: it must not earn M09 or M27 (or their CV skills)."""
    shipped = os.path.join(ROOT, "docs", "postmortems", "2026-11-19-alert-drill-and-ai-triage.md")
    assert os.path.basename(shipped) in lab.ORIGINAL_POSTMORTEMS
    folder = tmp_path / "docs" / "postmortems"
    folder.mkdir(parents=True)
    with open(shipped, encoding="utf-8") as source:
        text = source.read()
    (folder / os.path.basename(shipped)).write_text(text, encoding="utf-8")
    (folder / "README.md").write_text("TTD 1 TTA 2 TTR 3 AI human", encoding="utf-8")
    monkeypatch.setattr(lab, "ROOT", tmp_path)
    checks = {m["id"]: m["check"] for m in catalog["missions"]}
    assert lab.run_check(checks["M09"])["ok"] is False
    assert lab.run_check(checks["M27"])["ok"] is False
    # The same text saved as the student's own postmortem does count.
    (folder / "2027-01-10-my-game-day.md").write_text(text, encoding="utf-8")
    assert lab.run_check(checks["M09"])["ok"] is True
    assert lab.run_check(checks["M27"])["ok"] is True
