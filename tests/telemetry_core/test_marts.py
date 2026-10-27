"""Mart tests: build core + marts on the fake weekend from test_warehouse."""

from pathlib import Path

import pandas as pd
import pytest
from test_warehouse import fake_results, params, race_laps, save

from telemetry_core.warehouse import build, query, run_checks


def fake_weather(minutes=20, rain_from=None):
    rain = [rain_from is not None and m >= rain_from for m in range(minutes)]
    return pd.DataFrame(
        {
            "Time": [60.0 * m for m in range(minutes)],
            "AirTemp": 25.0,
            "TrackTemp": [30.0 + m * 0.5 for m in range(minutes)],
            "Humidity": 50.0,
            "Pressure": 1010.0,
            "Rainfall": rain,
            "WindDirection": 90,
            "WindSpeed": 1.5,
        }
    )


@pytest.fixture
def marts(tmp_path):
    raw = tmp_path / "raw"
    for rnd in (1, 2):
        save(raw, 2024, rnd, "Race", race_laps(), weather=fake_weather())
        save(raw, 2024, rnd, "Qualifying", race_laps().head(3), weather=fake_weather())
    hamilton_wins = fake_results().assign(Points=[0.0, 25.0], Position=[2.0, 1.0])
    save(raw, 2024, 3, "Race", race_laps(), results=hamilton_wins, weather=fake_weather(10, 5))
    path = tmp_path / "wh.duckdb"
    for layer in ("core", "marts"):
        build(Path("sql") / layer, path, params(raw))
    return path


def test_standings_run_through_the_season(marts):
    s = query(marts, "SELECT * FROM mart_standings WHERE driver_code = 'VER' ORDER BY round")
    assert s["total_points"].tolist() == [25.0, 50.0, 50.0]
    assert s["championship_position"].tolist() == [1, 1, 1]
    ham = query(marts, "SELECT total_points FROM mart_standings WHERE driver_code = 'HAM'")
    assert ham["total_points"].tolist() == [0.0, 0.0, 25.0]


def test_weekend_overview(marts):
    w = query(marts, "SELECT * FROM mart_weekends ORDER BY round")
    assert w["winner"].tolist() == ["VER", "VER", "HAM"]
    assert w["safety_car_laps"].tolist() == [1, 1, 1]  # lap 4 has status "14"
    assert not w["is_wet_race"].any()


def test_weather_summary(marts):
    w = query(marts, "SELECT * FROM mart_session_weather WHERE session_key = '2024_03_R'")
    assert w["n_samples"].item() == 10
    assert w["track_temp_min_c"].item() == 30.0
    assert w["rain_share"].item() == 0.5
    assert w["had_rain"].item()

def test_weather_ignores_track_sensor_dropouts(tmp_path):
    raw = tmp_path / "raw"
    weather = fake_weather()
    weather.loc[5, "TrackTemp"] = 0.0  # one sample where the track sensor dropped out
    save(raw, 2024, 1, "Race", race_laps(), weather=weather)
    path = tmp_path / "wh.duckdb"
    for layer in ("core", "marts"):
        build(Path("sql") / layer, path, params(raw))
    w = query(path, "SELECT * FROM mart_session_weather")
    assert w["track_temp_min_c"].item() == 30.0
    assert w["n_samples"].item() == 20  # the sample is kept: its air temperature is fine
    


def test_pace_uses_clean_laps_only(marts):
    p = query(marts, "SELECT * FROM mart_driver_session_pace WHERE session_key = '2024_01_R'")
    assert p["clean_laps"].item() == 2  # laps 2 and 3
    assert p["best_lap_s"].item() == 95.0
    assert p["gap_to_best_pct"].item() == 0.0


def test_checks_pass_on_good_data(marts):
    raw = marts.parent / "raw"
    failed = [c["name"] for c in run_checks(Path("sql/checks"), marts, params(raw)) if c["n_bad"]]
    # the fake races hand out 25 points, not 101; every other check passes
    assert failed == ["06_points_add_up"]


def practice_laps():
    """VER in FP2: stint 1 = out lap, 8 long-run laps that get 0.04 s slower per lap,
    one push lap, in lap. Stint 2 = out lap, 2 quick laps on softs."""
    times = [None, *[95.0 + 0.04 * i for i in range(8)], 92.0, 110.0, None, 91.5, 91.6]
    n = len(times)
    laps = race_laps().iloc[[0] * n].reset_index(drop=True)
    laps["LapNumber"] = [float(i) for i in range(1, n + 1)]
    laps["Stint"] = [1.0] * 11 + [2.0] * 3
    laps["Compound"] = ["MEDIUM"] * 11 + ["SOFT"] * 3
    laps["TyreLife"] = [float(i) for i in range(1, 12)] + [1.0, 2.0, 3.0]
    laps["LapTime"] = pd.to_timedelta(times, unit="s")
    laps["PitOutTime"] = pd.to_timedelta([1.0] + [None] * 10 + [1.0, None, None], unit="s")
    laps["PitInTime"] = pd.to_timedelta([None] * 10 + [3.0] + [None] * 3, unit="s")
    laps["TrackStatus"] = "1"
    return laps


@pytest.fixture
def practice(tmp_path):
    raw = tmp_path / "raw"
    save(raw, 2024, 1, "Practice 2", practice_laps(), weather=fake_weather())
    save(raw, 2024, 1, "Race", race_laps(), weather=fake_weather())
    path = tmp_path / "wh.duckdb"
    for layer in ("core", "marts"):
        build(Path("sql") / layer, path, params(raw))
    return path


def test_stints_split_by_tyre_set(practice):
    s = query(practice, "SELECT * FROM mart_stints WHERE session_key = '2024_01_FP2'")
    assert s["stint"].tolist() == [1, 2]
    assert s["compound"].tolist() == ["MEDIUM", "SOFT"]
    assert s["n_laps"].tolist() == [11, 3]
    assert s["n_clean"].tolist() == [9, 2]  # 8 long-run laps + the push lap; 2 quick laps


def test_long_run_drops_the_push_lap_and_adds_the_fuel_effect(practice):
    [run] = query(practice, "SELECT * FROM mart_long_runs").to_dict("records")
    assert run["stint"] == 1
    assert run["run_laps"] == 8  # the 92.0 s push lap is outside the 2% band
    assert run["deg_s_per_lap"] == pytest.approx(0.04 + 0.06)
    assert run["gap_to_best_same_tyre_pct"] == 0.0


def quali_laps(driver, base_s):
    """6 push laps, one every 5 minutes, each 0.05 s quicker than the one before:
    the track gets 0.1 s faster every 10 minutes."""
    laps = race_laps().iloc[[1] * 6].reset_index(drop=True)
    laps["Driver"] = driver
    laps["LapNumber"] = [float(i) for i in range(1, 7)]
    laps["LapTime"] = pd.to_timedelta([base_s - 0.05 * i for i in range(6)], unit="s")
    laps["LapStartTime"] = pd.to_timedelta([300.0 * i for i in range(6)], unit="s")
    laps["Time"] = laps["LapStartTime"] + laps["LapTime"]
    laps["Compound"] = "SOFT"
    return laps


def test_track_evolution_ignores_who_is_faster(tmp_path):
    raw = tmp_path / "raw"
    laps = pd.concat([quali_laps("VER", 90.0), quali_laps("HAM", 90.6)])
    save(raw, 2024, 1, "Qualifying", laps, weather=fake_weather())
    path = tmp_path / "wh.duckdb"
    for layer in ("core", "marts"):
        build(Path("sql") / layer, path, params(raw))
    e = query(path, "SELECT * FROM mart_track_evolution")
    assert e["n_drivers"].item() == 2
    assert e["evo_s_per_10min"].item() == pytest.approx(-0.1)
    assert e["q1_to_q2_s"].item() == pytest.approx(-0.5)  # fake results: Q2 - Q1 = -0.5 s


def test_weekend_signals_join_practice_quali_and_race(tmp_path):
    raw = tmp_path / "raw"
    long_race = race_laps().iloc[[1] * 12].reset_index(drop=True)
    long_race["LapNumber"] = [float(i) for i in range(2, 14)]  # 12 clean laps, no lap one
    save(raw, 2024, 1, "Practice 2", practice_laps(), weather=fake_weather())
    save(raw, 2024, 1, "Qualifying", race_laps().head(3), weather=fake_weather())
    save(raw, 2024, 1, "Race", long_race, weather=fake_weather())
    path = tmp_path / "wh.duckdb"
    for layer in ("core", "marts"):
        build(Path("sql") / layer, path, params(raw))
    [row] = query(path, "SELECT * FROM mart_weekend_signals").to_dict("records")
    assert row["driver_code"] == "VER"
    assert row["n_long_runs"] == 1
    assert row["long_run_gap_pct"] == 0.0
    assert row["quali_gap_pct"] == 0.0
    assert row["race_clean_laps"] == 12
    assert row["finish_position"] == 1
