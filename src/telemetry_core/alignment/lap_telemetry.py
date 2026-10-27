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

XY_SQL = """
SELECT SessionTime AS time_s, X AS x, Y AS y
FROM read_parquet(?)
WHERE DriverNumber = ? AND SessionTime BETWEEN ? AND ?
ORDER BY SessionTime
"""


def lap_folder(raw_root: Path, info: dict) -> Path:
    """The data/raw folder of the session this lap belongs to."""
    return (
        Path(raw_root)
        / "fastf1"
        / f"season={info['season']}"
        / f"event={info['event_folder']}"
        / f"session={info['session_folder']}"
    )


def load_lap(
    warehouse: Path, raw_root: Path, session_key: str, driver: str, lap: int
) -> tuple[pd.DataFrame, dict]:
    """Return (telemetry rows of that lap, facts about the lap)."""
    with duckdb.connect(str(warehouse), read_only=True) as con:
        found = con.execute(LAP_SQL, [session_key, driver.upper(), lap]).df()
    if found.empty:
        raise ValueError(f"no lap {lap} for {driver} in {session_key}")
    info = found.iloc[0].to_dict()
    params = [
        str(lap_folder(raw_root, info) / "car_data.parquet"),
        info["car_number"],
        info["lap_start_session_s"] - MARGIN_S,
        info["lap_end_session_s"] + MARGIN_S,
    ]
    tel = duckdb.execute(TEL_SQL, params).df()
    if len(tel) < 10:
        raise ValueError(f"only {len(tel)} telemetry rows for {driver} lap {lap} in {session_key}")
    return tel, info


def load_lap_xy(raw_root: Path, info: dict) -> pd.DataFrame:
    """Where the car was on track during the lap (pos_data: x and y in 1/10 m), for maps."""
    params = [
        str(lap_folder(raw_root, info) / "pos_data.parquet"),
        info["car_number"],
        info["lap_start_session_s"] - MARGIN_S,
        info["lap_end_session_s"] + MARGIN_S,
    ]
    xy = duckdb.execute(XY_SQL, params).df()
    if len(xy) < 10:
        raise ValueError(f"only {len(xy)} position rows for car {info['car_number']}")
    return xy


''' what changed : the folder of a lap's raw files is now one small function (lap_folder),
 because two readers need it. 
 The new reader load_lap_xy reads pos_data.parquet (x and y on track) for one lap, 
 the same way load_lap reads car_data.parquet'''