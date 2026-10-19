from pathlib import Path

import pandas as pd
import yaml
from typer.testing import CliRunner

from dpec.cli import app
from telemetry_core.ingestion import fastf1_source

runner = CliRunner()


def fake_fetch(season, round_no, session_name):
    laps = pd.DataFrame({"Driver": ["VER"], "LapTime": pd.to_timedelta([95.1], unit="s")})
    return {"laps": laps}, {"season": season, "session": session_name}


def make_args(monkeypatch, tmp_path, fetch=fake_fetch):
    """Fake FastF1: 2 seasons in config, 2 rounds each, 2 sessions per round."""
    monkeypatch.setattr(fastf1_source, "enable_cache", lambda path: None)
    monkeypatch.setattr(fastf1_source, "season_rounds", lambda season: [1, 2])
    monkeypatch.setattr(
        fastf1_source, "session_names", lambda s, r: (f"Grand Prix {r}", ["Qualifying", "Race"])
    )
    monkeypatch.setattr(fastf1_source, "fetch_session", fetch)
    config = yaml.safe_load(Path("config/dpec.yaml").read_text())
    config["seasons"] = [2024, 2025]
    config["paths"]["raw"] = str(tmp_path / "raw")
    config["paths"]["log"] = str(tmp_path / "ingest_log.csv")
    path = tmp_path / "dpec.yaml"
    path.write_text(yaml.safe_dump(config))
    return ["ingest", "--config", str(path)]


def test_one_weekend(monkeypatch, tmp_path):
    args = make_args(monkeypatch, tmp_path) + ["--season", "2024", "--round", "1"]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert "2 saved" in result.output
    race = tmp_path / "raw/fastf1/season=2024/event=01_grand_prix_1/session=race"
    assert (race / "laps.parquet").exists()


def test_everything_in_config(monkeypatch, tmp_path):
    result = runner.invoke(app, make_args(monkeypatch, tmp_path))
    assert result.exit_code == 0, result.output
    assert "8 saved" in result.output  # 2 seasons x 2 rounds x 2 sessions


def test_second_run_skips(monkeypatch, tmp_path):
    args = make_args(monkeypatch, tmp_path)
    runner.invoke(app, args)
    result = runner.invoke(app, args)
    assert "0 saved, 8 skipped" in result.output


def test_one_session_only(monkeypatch, tmp_path):
    args = make_args(monkeypatch, tmp_path) + ["--season", "2024", "--session", "race"]
    result = runner.invoke(app, args)
    assert "2 saved" in result.output


def test_bad_session_does_not_stop_the_rest(monkeypatch, tmp_path):
    def flaky_fetch(season, round_no, session_name):
        if round_no == 2 and session_name == "Race":
            raise ValueError("no data")
        return fake_fetch(season, round_no, session_name)

    result = runner.invoke(app, make_args(monkeypatch, tmp_path, flaky_fetch))
    assert result.exit_code == 1
    assert "6 saved, 0 skipped, 2 failed" in result.output


def test_rate_limit_stops_and_keeps_saved(monkeypatch, tmp_path):
    calls = []

    def limited_fetch(season, round_no, session_name):
        calls.append(1)
        if len(calls) > 3:
            raise fastf1_source.RateLimitError("too many requests")
        return fake_fetch(season, round_no, session_name)

    args = make_args(monkeypatch, tmp_path, limited_fetch)
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert "rate limit" in result.output
    saved = list((tmp_path / "raw").rglob("manifest.json"))
    assert len(saved) == 3

def test_every_attempt_is_logged(monkeypatch, tmp_path):
    def flaky_fetch(season, round_no, session_name):
        if round_no == 2 and session_name == "Race":
            raise ValueError("no data")
        return fake_fetch(season, round_no, session_name)

    args = make_args(monkeypatch, tmp_path, flaky_fetch) + ["--season", "2024"]
    runner.invoke(app, args)
    runner.invoke(app, args)  # second run: everything saved is skipped, only the failure retries
    log = pd.read_csv(tmp_path / "ingest_log.csv")
    assert log["status"].tolist() == ["ok", "ok", "ok", "failed", "failed"]
    assert log.loc[log["status"] == "failed", "error"].unique().tolist() == ["no data"]
    assert log.loc[0, "rows"] == 1  # the fake laps table has one row
