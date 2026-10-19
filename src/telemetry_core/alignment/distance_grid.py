import numpy as np
import pandas as pd

SMOOTH = ["time_s", "speed_kph", "throttle_pct", "rpm"]     # in between values make sense 
STEPS = ["gear", "brake", "drs"]                # no in-between: take the last sample before

def add_distance(tel:pd.DataFrame) -> pd.DataFrame:
    """Metres driven since the first sample: speed x time, added up sample by sample."""
    out = tel.sort_values("time_s").reset_index(drop=True)
    speed_ms = out["speed_kph"] / 3.6
    avg_speed = (speed_ms + speed_ms.shift(1, fill_value=speed_ms.iloc[0])) / 2
    out["distance_m"] = (avg_speed * out["time_s"].diff().fillna(0.0)).cumsum()
    return out


def to_grid(
    tel: pd.DataFrame,
    step_m: float,
    start_s: float | None = None,
    end_s: float | None = None,
    lap_length_m: float | None = None,
) -> pd.DataFrame:
    """One row every step_m metres: 0, 5, 10, ... from the start line.

    start_s / end_s: the exact lap start and end (session seconds). Telemetry comes about
    4 times a second, so the first and last samples miss the line by up to 0.25 s; we fill
    that gap by interpolation, so the grid's time at the end equals the official lap time.
    lap_length_m stretches the distance so this lap ends exactly there, so laps measured
    a few metres short or long still line up with the reference lap.
    """
    tel = add_distance(tel)
    start_s = tel["time_s"].iloc[0] if start_s is None else start_s
    end_s = tel["time_s"].iloc[-1] if end_s is None else end_s
    d_start, d_end = np.interp([start_s, end_s], tel["time_s"], tel["distance_m"])
    tel["distance_m"] = tel["distance_m"] - d_start
    tel["time_s"] = tel["time_s"] - start_s
    driven = d_end - d_start
    if lap_length_m:
        tel["distance_m"] = tel["distance_m"] * lap_length_m / driven
        driven = lap_length_m
    grid = pd.DataFrame({"distance_m": np.arange(0.0, driven + step_m / 2, step_m)})
    grid.loc[len(grid) - 1, "distance_m"] = driven  # last row = the finish line exactly
    for col in SMOOTH:
        grid[col] = np.interp(grid["distance_m"], tel["distance_m"], tel[col])
    before = np.searchsorted(tel["distance_m"], grid["distance_m"], side="right") - 1
    for col in STEPS:
        grid[col] = tel[col].to_numpy()[before.clip(0)]
    return grid


def delta(ref: pd.DataFrame, other: pd.DataFrame) -> pd.DataFrame:
    """Both laps side by side. delta_s > 0 means `other` is behind `ref` at that point."""
    both = ref.merge(other, on="distance_m", suffixes=("_ref", "_other"))
    both["delta_s"] = both["time_s_other"] - both["time_s_ref"]
    return both


def apexes(grid: pd.DataFrame, window_m: float = 150, max_kph: float = 250) -> pd.DataFrame:
    """Corners = the slowest point within window_m on each side, and slower than max_kph."""
    step = grid["distance_m"].iloc[1] - grid["distance_m"].iloc[0]
    rows = int(2 * window_m / step) + 1
    lowest = grid["speed_kph"].rolling(rows, center=True, min_periods=1).min()
    is_apex = (grid["speed_kph"] == lowest) & (grid["speed_kph"] < max_kph)
    found = grid.loc[is_apex, ["distance_m", "speed_kph"]]
    # a flat bottom gives several equal rows in a row: keep the first of each
    return found[found["distance_m"].diff().fillna(np.inf) > window_m].reset_index(drop=True)