
from pathlib import Path

import numpy as np
import pandas as pd

from telemetry_core.alignment.distance_grid import apexes, delta, to_grid
from telemetry_core.alignment.lap_telemetry import load_lap, load_lap_xy


def compare_laps(
    warehouse: Path, raw_root: Path, step_m: float, a: tuple, b: tuple
) -> tuple[pd.DataFrame, dict, dict]:
    """a and b are (session_key, driver, lap number). Returns (both laps, facts A, facts B).

    One row every step_m metres of lap A. Lap B is stretched to A's length, so each row is
    the same point on track for both. x, y = where that point is (from A's position data)."""
    tel_a, info_a = load_lap(warehouse, raw_root, *a)
    tel_b, info_b = load_lap(warehouse, raw_root, *b)
    ref = to_grid(tel_a, step_m, info_a["lap_start_session_s"], info_a["lap_end_session_s"])
    other = to_grid(
        tel_b,
        step_m,
        info_b["lap_start_session_s"],
        info_b["lap_end_session_s"],
        lap_length_m=ref["distance_m"].iloc[-1],
    )
    both = delta(ref, other)
    xy = load_lap_xy(raw_root, info_a)
    session_time = info_a["lap_start_session_s"] + both["time_s_ref"]
    both["x"] = np.interp(session_time, xy["time_s"], xy["x"])
    both["y"] = np.interp(session_time, xy["time_s"], xy["y"])
    return both, info_a, info_b


def corner_table(both: pd.DataFrame, window_m: float = 150) -> pd.DataFrame:
    """One row per corner of lap A: lowest speed of each car near the apex, and the time A
    loses (+) or gains (-) on B from window_m before the apex to window_m after it."""
    d = both["distance_m"].to_numpy()
    ref = both.rename(columns={"speed_kph_ref": "speed_kph"})[["distance_m", "speed_kph"]]
    rows = []
    for n, apex in enumerate(apexes(ref, window_m).itertuples(), start=1):
        lo, hi = max(apex.distance_m - window_m, d[0]), min(apex.distance_m + window_m, d[-1])
        a_in, a_out = np.interp([lo, hi], d, both["time_s_ref"])
        b_in, b_out = np.interp([lo, hi], d, both["time_s_other"])
        near = (d >= lo) & (d <= hi)
        rows.append(
            {
                "corner": n,
                "distance_m": apex.distance_m,
                "min_speed_a_kph": both.loc[near, "speed_kph_ref"].min(),
                "min_speed_b_kph": both.loc[near, "speed_kph_other"].min(),
                "a_loses_s": (a_out - a_in) - (b_out - b_in),
            }
        )
    return pd.DataFrame(rows)

