"""Public record tests (step C5): a frozen file can't change unnoticed, a late forecast is
refused, the score follows its rules, and a live decision is the replay's decision."""

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from test_decisions import fake_races

from dpec.decisions.replay import decide_next, replay
from dpec.record.freeze import TooLate, check_deadline
from dpec.record.ledger import (
    DriverForecast,
    Forecast,
    Score,
    content_hash,
    git_changes,
    late,
    problems,
    read,
    write_once,
)
from dpec.record.score import score_checkpoint, verdict

START = datetime(2026, 11, 1, 20, 0, tzinfo=UTC)  # a race start


def fake_forecast(deadline=START - timedelta(minutes=30), drivers=6) -> Forecast:
    """A frozen forecast for six drivers, D0 fastest. D0 and D1 are our cars."""
    return Forecast(
        season=2026,
        round=19,
        event_name="Test Grand Prix",
        circuit="Test",
        checkpoint="after_quali",
        target_session="R",
        target_start_utc=START,
        deadline_utc=deadline,
        frozen_at_utc=deadline - timedelta(hours=20),
        sessions_seen=["FP1", "FP2", "FP3", "Q"],
        code_version="abc1234",
        inputs_sha256="0" * 64,
        method="test",
        drivers=[
            DriverForecast(
                driver_code=f"D{k}",
                team=f"Team {k // 2}",
                ours=k < 2,
                predicted_gap_pct=0.3 * k,
                low_pct=0.3 * k - 0.5,
                high_pct=0.3 * k + 0.5,
                p_best=None,
                p_top3=None,
                p_beats_teammate=None,
                baselines={"team_form": 0.3 * k + 0.4, "no_signal": 1.0},
            )
            for k in range(drivers)
        ],
        decision=None,
    )


def test_content_hash_ignores_its_own_field():
    f = fake_forecast()
    assert content_hash(f) == content_hash(f.model_copy(update={"sha256": "anything"}))
    assert len(content_hash(f)) == 64


def test_content_hash_changes_when_one_number_changes():
    f = fake_forecast()
    edited = f.model_copy(deep=True)
    edited.drivers[0].predicted_gap_pct = 0.01
    assert content_hash(f) != content_hash(edited)


def test_ledger_is_write_once(tmp_path):
    path = tmp_path / "ledger" / "2026" / "19-test" / "after_quali.json"
    write_once(fake_forecast(), path)
    assert read(path).sha256 == content_hash(read(path))  # the file carries its own hash
    with pytest.raises(FileExistsError):
        write_once(fake_forecast(), path)


def test_an_edited_file_is_caught(tmp_path):
    path = write_once(fake_forecast(), tmp_path / "2026" / "19-test" / "after_quali.json")
    assert problems(tmp_path) == []
    data = json.loads(path.read_text())
    data["drivers"][0]["predicted_gap_pct"] = 9.9  # a quiet edit after the race
    path.write_text(json.dumps(data))
    assert "content changed" in problems(tmp_path)[0]


def test_git_sees_a_frozen_file_change(tmp_path, monkeypatch):
    """Even an edit that also updates the sha256 is caught: git remembers the pushed file."""
    monkeypatch.chdir(tmp_path)
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "init", "-q"], check=True)
    path = write_once(fake_forecast(), Path("ledger/2026/19-test/after_quali.json"))
    subprocess.run(git + ["add", "."], check=True)
    subprocess.run(git + ["commit", "-qm", "freeze"], check=True)
    first = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    path.unlink()
    edited = fake_forecast().model_copy(update={"method": "changed after the race"})
    write_once(edited, path)  # a new, valid hash: the file alone looks fine
    subprocess.run(git + ["commit", "-qam", "quiet edit"], check=True)
    assert problems() == []
    assert git_changes(first.stdout.strip()) == [("M", "ledger/2026/19-test/after_quali.json")]


def test_a_late_forecast_is_found(tmp_path):
    path = write_once(fake_forecast(), tmp_path / "after_quali.json")
    assert late([path], START - timedelta(hours=1)) == []
    assert "after its deadline" in late([path], START - timedelta(minutes=10))[0]


def test_check_deadline():
    assert check_deadline(START - timedelta(hours=2), START) == START - timedelta(minutes=30)
    with pytest.raises(TooLate):
        check_deadline(START - timedelta(minutes=29), START)


def test_verdict_rules():
    assert verdict("after_quali", 0.40, 0.90) == "GOOD"
    assert verdict("after_quali", 0.40, 0.60) == "OK"  # good error, ranges too narrow
    assert verdict("after_quali", 0.70, 0.90) == "OK"
    assert verdict("after_practice", 0.60, None) == "GOOD"  # no ranges yet: error only
    assert verdict("after_quali", 1.20, 0.90) == "MISS"  # no better than 'no signal'
    assert verdict("after_quali", 0.40, 0.40) == "MISS"  # most real paces outside


def test_score_checkpoint_adds_up():
    f = fake_forecast().model_copy(update={"sha256": "s" * 64})
    actual = pd.Series({f"D{k}": 0.3 * k + 0.1 for k in range(6)})  # every guess 0.1 too low
    s = score_checkpoint(f, actual)
    assert s.drivers_scored == 6 and s.mae_pct == pytest.approx(0.1)
    assert s.inside_range == 1.0 and s.spearman == 1.0
    assert s.baselines_mae_pct["team_form"] == pytest.approx(0.3)
    assert s.skill_vs_team_form == pytest.approx(1 - 0.1 / 0.3, abs=1e-4)
    assert [c.driver_code for c in s.our_cars] == ["D0", "D1"]


def test_live_decision_is_the_replays_decision():
    """decide_next on a race with its answers removed = what replay() decided for it."""
    table, stops = fake_races()
    replayed, _ = replay(table, stops)
    race = table[(table["season"] == 2023) & (table["round"] == 12)].iloc[0]
    blind = race.copy()
    blind[["race_deg_s_per_lap", "pit_loss_s", "top10_stops"]] = np.nan
    d = decide_next(table, stops, blind)
    same = replayed[replayed["round"] == 12].iloc[0]
    assert d["deg"] == pytest.approx(same["deg"])
    assert d["stops"] == same["stops"] and d["window"] == (
        same["window_first"],
        same["window_last"],
    )


def test_schema_files_are_current():
    """schemas/ must match the models: run `uv run dpec schema` after changing ledger.py."""
    for name, model in {"forecast": Forecast, "score": Score}.items():
        saved = json.loads(Path(f"schemas/{name}.schema.json").read_text())
        assert saved == json.loads(json.dumps(model.model_json_schema()))