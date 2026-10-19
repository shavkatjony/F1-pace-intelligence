
from pathlib import Path

import duckdb
import pandas as pd

LAP_SQL = """
SELECT l.car_number, l.lap_time_s, l.lap_start_session_s, l.lap_end_session_s, l.lap_reason,
       s.season, s.event_folder, s.session_folder
FROM core_laps AS l
JOIN core_sessions AS s USING (session_key)
WHERE l.session_key = ? AND l.driver_code = ? AND l.lap_number = ?
"""

MARGIN_S = 1.0  # one extra second on each side, so the start and end line can be interpolated

TEL_SQL = """
SELECT SessionTime AS time_s, Speed AS speed_kph, Throttle AS throttle_pct, RPM AS rpm,
       nGear AS gear, Brake AS brake, DRS AS drs
FROM read_parquet(?)
WHERE DriverNumber = ? AND SessionTime BETWEEN ? AND ?
ORDER BY SessionTime
"""
def load_lap(
    warehouse: Path, raw_root: Path, session_key: str, driver: str, lap: int
) -> tuple[pd.DataFrame, dict]:
    """Return (telemetry rows of that lap, facts about the lap)."""
    with duckdb.connect(str(warehouse), read_only=True) as con:
        found = con.execute(LAP_SQL, [session_key, driver.upper(), lap]).df()
    if found.empty:
        raise ValueError(f"no lap {lap} for {driver} in {session_key}")
    info = found.iloc[0].to_dict()
    folder = (
        Path(raw_root)
        / "fastf1"
        / f"season={info['season']}"
        / f"event={info['event_folder']}"
        / f"session={info['session_folder']}"
    )
    params = [
        str(folder / "car_data.parquet"),
        info["car_number"],
        info["lap_start_session_s"] - MARGIN_S,
        info["lap_end_session_s"] + MARGIN_S,
    ]
    tel = duckdb.execute(TEL_SQL, params).df()
    if len(tel) < 10:
        raise ValueError(f"only {len(tel)} telemetry rows for {driver} lap {lap} in {session_key}")
    return tel, info


'''It asks core_laps where the lap is (car number, start, end, folder), then reads only that car and that time window from car_data.parquet. DuckDB skips the rest of the file, so it's fast even for a 6 MB race file.
The ? marks are parameters: DuckDB fills them in safely. Never paste values into SQL text yourself.
Fewer than 10 rows means FastF1 has no telemetry for that lap: it stops with a clear message instead of drawing a wrong chart.'''
