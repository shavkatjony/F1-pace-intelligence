"""API tests: the fake weekend from test_warehouse, built into a warehouse, served by the app."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml
from fastapi.testclient import TestClient
from test_marts import fake_weather
from test_warehouse import params, race_laps, save

from dpec.api.main import create_app
from telemetry_core.warehouse import build


def two_drivers():
    """VER as in test_warehouse, and HAM driving the same 9 laps 0.5 s slower."""
    ham = race_laps().assign(Driver="HAM", DriverNumber="44", Team="Mercedes")
    ham["LapTime"] = pd.to_timedelta(ham["LapTime"].dt.total_seconds() + 0.5, unit="s")
    return pd.concat([race_laps(), ham], ignore_index=True)


def telemetry(number, slowest_kph):
    """Car data and position for a whole session: every lap lasts 100 s and has one corner
    in the middle (speed drops from 300 km/h to slowest_kph and back)."""
    t = np.arange(0.0, 900.0, 0.25)
    speed = slowest_kph + (300 - slowest_kph) * (0.5 + 0.5 * np.cos(2 * np.pi * (t % 100) / 100))
    car = pd.DataFrame(
        {
            "SessionTime": pd.to_timedelta(t, unit="s"),
            "Speed": speed,
            "Throttle": np.where(speed > 250, 100.0, 40.0),
            "RPM": 11000.0,
            "nGear": np.where(speed > 250, 8, 4),
            "Brake": speed < 220,
            "DRS": 0,
            "DriverNumber": number,
        }
    )
    pos = pd.DataFrame(
        {
            "SessionTime": pd.to_timedelta(t, unit="s"),
            "X": 1000 * np.cos(2 * np.pi * t / 100),
            "Y": 1000 * np.sin(2 * np.pi * t / 100),
            "DriverNumber": number,
        }
    )
    return car, pos


@pytest.fixture
def client(tmp_path):
    raw = tmp_path / "raw"
    car_ver, pos_ver = telemetry("1", 120)
    car_ham, pos_ham = telemetry("44", 110)
    tables = {
        "car_data": pd.concat([car_ver, car_ham]),
        "pos_data": pd.concat([pos_ver, pos_ham]),
        "weather": fake_weather(),
    }
    save(raw, 2024, 1, "Race", two_drivers(), **tables)
    save(raw, 2024, 1, "Qualifying", two_drivers(), **tables)
    warehouse = tmp_path / "wh.duckdb"
    for layer in ("core", "marts"):
        build(Path("sql") / layer, warehouse, params(raw))

    config = yaml.safe_load(Path("config/dpec.yaml").read_text())
    config["paths"].update({"raw": str(raw), "warehouse": str(warehouse), "data": str(tmp_path)})
    path = tmp_path / "dpec.yaml"
    path.write_text(yaml.safe_dump(config))
    return TestClient(create_app(str(path)))


def test_health_counts_sessions(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["sessions"] == 2


def test_weekend_lists_its_sessions_in_time_order(client):
    w = client.get("/api/weekends/2024/1").json()
    assert w["event_name"] == "Test Grand Prix"
    assert [s["session_type"] for s in w["sessions"]] == ["Q", "R"]


def test_pace_is_fastest_first(client):
    p = client.get("/api/weekends/2024/1/pace", params={"session": "R"}).json()
    assert [d["driver_code"] for d in p] == ["VER", "HAM"]
    assert p[1]["gap_s"] == pytest.approx(0.5)
    assert p[0]["lineage"] == "red_bull"  # from dim_teams, for the team colour


def test_unknown_weekend_is_404_and_bad_session_is_422(client):
    assert client.get("/api/weekends/2024/9").status_code == 404
    assert client.get("/api/weekends/2024/1/pace", params={"session": "XX"}).status_code == 422


def test_the_api_is_read_only(client):
    assert client.post("/api/weekends").status_code == 405
    assert client.delete("/api/weekends/2024/1").status_code == 405


def test_compare_puts_both_laps_on_one_grid(client):
    r = client.get("/api/weekends/2024/1/compare", params={"session": "R", "a": "VER", "b": "ham"})
    assert r.status_code == 200, r.text
    c = r.json()
    assert (c["a"]["driver"], c["b"]["driver"]) == ("VER", "HAM")
    assert c["a"]["lap"] == 2  # VER's fastest clean lap (95.0 s)
    n = len(c["distance_m"])
    assert all(len(c[k]) == n for k in ["speed_a", "speed_b", "a_behind_s", "x", "y"])
    assert c["a_behind_s"][0] == 0
    assert len(c["corners"]) == 1  # one slow corner per lap
    corner = c["corners"][0]
    assert corner["min_speed_a_kph"] > corner["min_speed_b_kph"]  # HAM is slower there
    assert corner["a_loses_s"] < 0  # so VER gains time in it


def test_compare_without_a_clean_lap_is_404(client):
    r = client.get("/api/weekends/2024/1/compare", params={"session": "R", "a": "VER", "b": "ALO"})
    assert r.status_code == 404
    assert "ALO has no clean lap" in r.json()["detail"]


def test_results_in_finishing_order(client):
    r = client.get("/api/weekends/2024/1/results").json()
    assert [d["driver_code"] for d in r] == ["VER", "HAM"]
    assert r[1]["status"] == "Disqualified"

def test_forecast_needs_a_backtest_first(client):
    r = client.get("/api/weekends/2024/1/forecast")
    assert r.status_code == 404
    assert "dpec backtest" in r.json()["detail"]


def test_forecast_shows_the_saved_guesses(client, tmp_path):
    saved = tmp_path / "forecasts" / "backtest.parquet"
    saved.parent.mkdir()
    pd.DataFrame(
        {
            "forecaster": ["shared_model", "shared_model", "team_form"],
            "checkpoint": "after_quali",
            "season": 2024,
            "round": 1,
            "driver_code": ["HAM", "VER", "VER"],
            "lineage": ["mercedes", "red_bull", "red_bull"],
            "predicted": [0.6, 0.1, 0.3],
            "low": [0.0, -0.5, None],
            "high": [1.2, 0.7, None],
            "actual": [0.55, 0.0, 0.0],
            "p_best": [0.2, 0.8, None],
            "p_top3": [1.0, 1.0, None],
            "mean_rank": [1.8, 1.2, None],
            "p_beats_teammate": [None, None, None],
        }
    ).to_parquet(saved)
    f = client.get("/api/weekends/2024/1/forecast").json()
    assert [d["driver_code"] for d in f] == ["VER", "HAM"]  # shared model only, best guess first
    assert f[0]["finish_position"] == 1 and f[0]["p_beats_teammate"] is None
    assert client.get("/api/weekends/2022/1/forecast").status_code == 404
    