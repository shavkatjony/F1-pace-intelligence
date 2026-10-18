# oh my hands , is hurting , the testing is takes more effort than itself ,if you know , but try and error is the first principles of upgrade


"""Warehouse tests: a tiny fake data/raw folder, the real SQL files, no internet."""

from pathlib import Path

import pandas as pd
import pytest

from telemetry_core.ingestion.writer import write_session
from telemetry_core.paths import session_folder
from telemetry_core.warehouse import build, query, render

SQL_DIR = Path("sql/core")


def save(raw, season, rnd, session_name, laps):
    info = {
        "season": season,
        "round": rnd,
        "event": "Test Grand Prix",
        "session": session_name,
        "session_date_utc": "2024-03-02 15:00:00",
        "session_info": {"Meeting": {"Circuit": {"ShortName": "Testville"}}},
    }
    folder = session_folder(raw, "fastf1", season, rnd, "Test Grand Prix", session_name)
    write_session({"laps": laps}, info, folder)


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
    counts = build(SQL_DIR, path, {"raw": raw.as_posix(), "slow_lap_pct": 107})
    return path, counts


def test_row_counts(wh):
    _, counts = wh
    assert counts == {"core_sessions": 4, "core_laps": 9 + 3 + 2 + 2}


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
        build(SQL_DIR, tmp_path / "wh.duckdb", {"raw": raw.as_posix(), "slow_lap_pct": 107})


def test_render_refuses_missing_values():
    with pytest.raises(ValueError, match="unfilled"):
        render("SELECT * FROM '{{ raw }}/x'", {})


def test_render_fills_placeholders_with_optional_whitespace():
    assert render("SELECT '{{ raw }}', {{slow_lap_pct}}", {"raw": "/data", "slow_lap_pct": 107}) == (
        "SELECT '/data', 107"
    )
