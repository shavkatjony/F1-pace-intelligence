# oh my hands , is hurting , the testing is takes more effort than itself ,if you know , but try and error is the first principles of upgrade


"""Warehouse tests: a tiny fake data/raw folder, the real SQL files, no internet."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from telemetry_core.alignment.lap_telemetry import load_lap
from telemetry_core.ingestion.writer import write_session
from telemetry_core.paths import session_folder
from telemetry_core.warehouse import build, query, render, run_checks, undocumented_columns

# Existing directory definition
SQL_DIR = Path("sql/core")
# New params helper
CHECKS_DIR = Path("sql/checks")

def params(raw):
    return {"raw": raw.as_posix(), "seeds": "seeds", "slow_lap_pct": 107}

def save(raw, season, rnd, session_name, laps, results=None, **other_tables):
    info = {
        "season": season,
        "round": rnd,
        "event": "Test Grand Prix",
        "session": session_name,
        "session_date_utc": "2024-03-02 15:00:00",
        "session_info": {"Meeting": {"Circuit": {"ShortName": "Testville"}}},
    }
    folder = session_folder(raw, "fastf1", season, rnd, "Test Grand Prix", session_name)
    results = fake_results() if results is None else results
    tables = {"laps": laps, "results": results, **other_tables}
    write_session(tables, info, folder)

def fake_results():
    """Two drivers: VER wins from pole, HAM is disqualified after the race."""
    return pd.DataFrame(
        {
            "Abbreviation": ["VER", "HAM"],
            "DriverId": ["max_verstappen", "hamilton"],
            "DriverNumber": ["1", "44"],
            "FullName": ["Max Verstappen", "Lewis Hamilton"],
            "TeamName": ["Red Bull Racing", "Mercedes"],
            "TeamId": ["red_bull", "mercedes"],
            "GridPosition": [1.0, 2.0],
            "Position": [1.0, 2.0],
            "ClassifiedPosition": ["1", "D"],
            "Status": ["Finished", "Disqualified"],
            "Points": [25.0, 0.0],
            "Laps": [9.0, 9.0],
            "Q1": [90.0, 90.5],
            "Q2": [89.5, 90.0],
            "Q3": [89.0, 89.6],
        }
    )


def race_laps():
    """One driver, 9 laps; each lap breaks a different rule."""
    n = 9
    seconds = [100.0, 95.0, 95.2, 120.0, 99.0, 95.1, None, 140.0, 95.3]
    laps = pd.DataFrame(
        {
            "Driver": ["VER"] * n,
            "DriverNumber": ["1"] * n,
            "Team": ["Red Bull Racing"] * n,
            "LapNumber": [float(i) for i in range(1, n + 1)],
            "Stint": [1.0] * n,
            "Compound": ["MEDIUM"] * n,
            "TyreLife": [float(i) for i in range(1, n + 1)],
            "LapTime": pd.to_timedelta(seconds, unit="s"),
            "PitInTime": pd.to_timedelta([None] * 4 + [3.0] + [None] * 4, unit="s"),
            "PitOutTime": pd.to_timedelta([None] * 5 + [1.0] + [None] * 3, unit="s"),
            "TrackStatus": ["1", "1", "1", "14", "1", "1", "1", "1", "12"],
            "Deleted": [False] * n,
            "FastF1Generated": [False] * n,
            "IsAccurate": [True] * n,
        }
    )
    # columns the SQL reads but these tests don't check
    for col in ["Sector1Time", "Sector2Time", "Sector3Time"]:
        laps[col] = pd.to_timedelta([30.0] * n, unit="s")
    # lap i starts at 100 * (i - 1) seconds into the session and lasts 100 s
    laps["LapStartTime"] = pd.to_timedelta([100.0 * i for i in range(n)], unit="s")
    laps["Time"] = laps["LapStartTime"] + pd.to_timedelta(100.0, unit="s")

    laps["FreshTyre"] = True
    laps["SpeedST"] = 300.0
    laps["Position"] = 1.0
    laps["LapStartDate"] = pd.Timestamp("2024-03-02 15:00:00")
    laps["DeletedReason"] = ""
    return laps


@pytest.fixture
def wh(tmp_path):
    raw = tmp_path / "raw"
    save(raw, 2024, 1, "Race", race_laps())
    save(raw, 2024, 1, "Qualifying", race_laps().head(3))
    save(raw, 2023, 6, "Sprint Shootout", race_laps().head(2))
    save(raw, 2023, 6, "Sprint", race_laps().head(2))
    path = tmp_path / "wh.duckdb"
    counts = build(SQL_DIR, path, params(raw))
    return path, counts


def test_row_counts(wh):
    _, counts = wh
    assert counts == {
        "core_sessions": 4,
        "core_laps": 9 + 3 + 2 + 2,
        "core_results": 4 * 2,  # 4 sessions x 2 drivers
        "core_files": 4 * 2,  # 4 sessions x (laps, results)
        "dim_drivers": 2 + 2,  # (VER, HAM) in 2023 and in 2024
        "dim_teams": 2, # Red Bull Racing, Mercedes
    }



def test_session_keys_and_types(wh):
    path, _ = wh
    s = query(path, "SELECT * FROM core_sessions ORDER BY session_key")
    assert s["session_key"].tolist() == ["2023_06_S", "2023_06_SQ", "2024_01_Q", "2024_01_R"]
    assert s["is_sprint_weekend"].tolist() == [True, True, False, False]
    assert set(s["circuit"]) == {"Testville"}


def test_each_lap_gets_the_right_reason(wh):
    path, _ = wh
    laps = query(path, "SELECT lap_reason FROM core_laps WHERE session_key = '2024_01_R'")
    assert laps["lap_reason"].tolist() == [
        "lap_one",  # lap 1 of a race
        "clean",
        "clean",
        "safety_car",  # status "14": green, then safety car
        "in_lap",
        "out_lap",
        "no_time",
        "slow",  # 140 s is far above 107% of the clean median (95.1 s)
        "yellow",
    ]


def test_lap_one_is_only_a_race_rule(wh):
    path, _ = wh
    q = query(path, "SELECT lap_reason FROM core_laps WHERE session_key = '2024_01_Q'")
    assert q["lap_reason"].tolist()[0] == "clean"


def test_one_row_per_driver_lap_session(wh):
    path, _ = wh
    dupes = query(
        path,
        "SELECT session_key, driver_code, lap_number, count(*) AS n FROM core_laps "
        "GROUP BY ALL HAVING n > 1",
    )
    assert dupes.empty


def test_unknown_session_name_fails(tmp_path):
    raw = tmp_path / "raw"
    save(raw, 2024, 1, "Practice 9", race_laps())
    with pytest.raises(Exception, match="unknown session name"):
        build(SQL_DIR, tmp_path / "wh.duckdb", params(raw))


def test_render_refuses_missing_values():
    with pytest.raises(ValueError, match="unfilled"):
        render("SELECT * FROM '{{ raw }}/x'", {})


def test_render_fills_placeholders_with_optional_whitespace():
    assert render("SELECT '{{ raw }}', {{slow_lap_pct}}", {"raw": "/data", "slow_lap_pct": 107}) == (
        "SELECT '/data', 107"
    )

def test_load_lap_reads_only_that_lap(tmp_path):
    raw = tmp_path / "raw"
    t = np.arange(0.0, 900.0, 0.25)  # car_data for the whole session, 4 samples a second
    car_data = pd.DataFrame(
        {
            "SessionTime": pd.to_timedelta(t, unit="s"),
            "Speed": 200.0,
            "Throttle": 100.0,
            "RPM": 11000.0,
            "nGear": 7,
            "Brake": False,
            "DRS": 0,
            "DriverNumber": "1",
        }
    )
    save(raw, 2024, 1, "Race", race_laps(), car_data=car_data)
    wh = tmp_path / "wh.duckdb"
    build(SQL_DIR, wh, params(raw))

    tel, info = load_lap(wh, raw, "2024_01_R", "ver", 3)  # lap 3 = 200 s to 300 s
    assert info["lap_start_session_s"] == 200.0
    assert tel["time_s"].min() >= 199.0  # one second of margin on each side
    assert tel["time_s"].max() <= 301.0
    with pytest.raises(ValueError, match="no lap 99"):
        load_lap(wh, raw, "2024_01_R", "VER", 99)
        
# ==============================================================
# for the new 2 tests 
# =============================================================
def test_results_keep_the_official_classification(wh):
    path, _ = wh
    r = query(path, "SELECT * FROM core_results WHERE session_key = '2024_01_R'")
    assert r["driver_id"].tolist() == ["max_verstappen", "hamilton"]
    assert r["classified"].tolist() == ["1", "D"]
    assert r["points"].tolist() == [25.0, 0.0]


def test_files_table_lists_every_saved_table(wh):
    path, _ = wh
    f = query(path, "SELECT table_name, n_rows, is_empty FROM core_files WHERE session_key = '2024_01_R'")
    assert f["table_name"].tolist() == ["laps", "results"]
    assert f["n_rows"].tolist() == [9, 2]
    assert not f["is_empty"].any()

# =============================================================
# these functions are created after 2 table is addded these are dim drivers and dim teams , for testing , chao
# =============================================================

# ==============================================================
# Lesson 7: ID maps and checks
# ==============================================================
def test_missing_driver_id_is_borrowed_from_the_same_season(tmp_path):
    raw = tmp_path / "raw"
    no_ids = fake_results().assign(DriverId=["", "nan"])  # like sprint qualifying
    save(raw, 2024, 5, "Sprint Qualifying", race_laps().head(2), results=no_ids)
    save(raw, 2024, 5, "Sprint", race_laps().head(2))
    wh = tmp_path / "wh.duckdb"
    build(SQL_DIR, wh, params(raw))
    r = query(wh, "SELECT driver_id FROM core_results WHERE session_key = '2024_05_SQ'")
    assert r["driver_id"].tolist() == ["max_verstappen", "hamilton"]


def test_empty_team_is_filled_from_the_same_weekend(tmp_path):
    raw = tmp_path / "raw"
    save(raw, 2026, 7, "Practice 1", race_laps().assign(Team=""))
    save(raw, 2026, 7, "Practice 2", race_laps())
    wh = tmp_path / "wh.duckdb"
    build(SQL_DIR, wh, params(raw))
    teams = query(wh, "SELECT DISTINCT team FROM core_laps WHERE session_key = '2026_07_FP1'")
    assert teams["team"].tolist() == ["Red Bull Racing"]


def test_stand_in_team_comes_from_the_same_car_number(tmp_path):
    raw = tmp_path / "raw"
    rookie = race_laps().assign(Driver="IWA", DriverNumber="36")
    save(raw, 2026, 7, "Practice 1", rookie.assign(Team=""))
    save(raw, 2026, 13, "Practice 1", rookie)  # same rookie, same number, team known
    wh = tmp_path / "wh.duckdb"
    build(SQL_DIR, wh, params(raw))
    teams = query(wh, "SELECT DISTINCT team FROM core_laps WHERE session_key = '2026_07_FP1'")
    assert teams["team"].tolist() == ["Red Bull Racing"]


def test_checks_pass_on_good_data(wh):
    path, _ = wh
    raw = path.parent / "raw"
    failed = [c["name"] for c in run_checks(CHECKS_DIR, path, params(raw)) if c["n_bad"]]
    # the fake races have 25 points, not 101; every other check passes
    assert failed == ["06_points_add_up"]


def test_a_check_returns_the_bad_rows(wh, tmp_path):
    path, _ = wh
    (tmp_path / "checks").mkdir()
    (tmp_path / "checks" / "01_no_slow_laps.sql").write_text(
        "SELECT * FROM core_laps WHERE lap_reason = 'slow'"
    )
    [result] = run_checks(tmp_path / "checks", path, {})
    assert result["n_bad"] == 1


def test_dictionary_check_lists_missing_columns(wh, tmp_path):
    path, _ = wh
    dictionary = tmp_path / "dict.md"
    dictionary.write_text("## core_sessions\n\n| column | meaning |\n|---|---|\n| `season` | year |\n")
    missing = undocumented_columns(path, dictionary)
    assert "core_sessions.season" not in missing
    assert "core_sessions.round" in missing
    assert "core_laps.lap_reason" in missing
    
# =============================================================
# test functions ends here 
# =============================================================