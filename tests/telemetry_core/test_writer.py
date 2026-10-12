"""Writer tests use a tiny fake table, so they run in seconds and need no internet."""

import json

import pandas as pd

from telemetry_core.ingestion.writer import is_saved, parquet_safe, write_session


def fake_laps():
    return pd.DataFrame(
        {
            "Driver": ["VER", "LEC"],
            "LapTime": pd.to_timedelta([95.123, 95.456], unit="s"),
            "Compound": ["SOFT", None],
            "Deleted": [False, None],  # mixed types, like real FastF1 data
            "Note": [float("nan"), ["a", "list"]],
        }
    )


def test_timedelta_becomes_seconds():
    safe, seconds_cols = parquet_safe(fake_laps())
    assert seconds_cols == ["LapTime"]
    assert safe["LapTime"].tolist() == [95.123, 95.456]


def test_missing_stays_missing():
    safe, _ = parquet_safe(fake_laps())
    assert safe["Compound"].isna().tolist() == [False, True]
    assert safe["Note"].tolist() == [None, "['a', 'list']"]


def test_write_session_files_and_manifest(tmp_path):
    folder = tmp_path / "session=race"
    manifest = write_session({"laps": fake_laps()}, {"season": 2024}, folder)

    assert (folder / "laps.parquet").exists()
    assert is_saved(folder)
    assert manifest["files"]["laps"]["rows"] == 2
    saved = json.loads((folder / "manifest.json").read_text())
    assert saved["files"]["laps"]["seconds_columns"] == ["LapTime"]

    back = pd.read_parquet(folder / "laps.parquet")
    assert back.shape == (2, 5)


def test_same_data_gives_same_file(tmp_path):
    first = write_session({"laps": fake_laps()}, {}, tmp_path / "a")
    second = write_session({"laps": fake_laps()}, {}, tmp_path / "b")
    assert first["files"]["laps"]["sha256"] == second["files"]["laps"]["sha256"]
    