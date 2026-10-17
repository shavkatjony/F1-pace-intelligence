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