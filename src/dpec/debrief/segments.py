"""Where a lap's time went (step D1): the gap between two laps, split by what the car was doing.

Both laps sit on one distance grid (step A4b). Each 5 m step of the gap goes to one kind of
track part, read from the reference lap: braking, a slow, medium or fast corner, traction (the
exit of a slow or medium corner, before full throttle), or a straight (full throttle). The
parts add up to the whole gap by construction: they are the gap, cut into pieces.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from telemetry_core.alignment.compare import compare_laps
from telemetry_core.alignment.distance_grid import apexes

KINDS = ["straight", "braking", "slow corner", "medium corner", "fast corner", "traction"]
SLOW_KPH = 120  # a corner taken below 120 km/h is slow
FAST_KPH = 200  # ... at 200 km/h or more, fast; in between, medium
FULL_THROTTLE = 95  # % throttle that counts as flat out


def nearest_corner(both: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """For every grid row: the speed at the nearest corner of the reference lap, and whether
    the row is after that corner's apex (the exit) rather than before it."""
    ref = both.rename(columns={"speed_kph_ref": "speed_kph"})[["distance_m", "speed_kph"]]
    corners = apexes(ref)
    d = both["distance_m"].to_numpy()
    if corners.empty:  # a lap with no corner at all (only in made-up tests)
        return np.full(len(d), np.inf), np.zeros(len(d), dtype=bool)
    at = corners["distance_m"].to_numpy()
    k = np.abs(d[:, None] - at[None, :]).argmin(axis=1)  # index of the nearest apex
    return corners["speed_kph"].to_numpy()[k], d > at[k]


def kind_of(
    brake: np.ndarray, throttle: np.ndarray, after_apex: np.ndarray, corner_kph: np.ndarray
) -> np.ndarray:
    """One of KINDS for every grid row. Checked in this order: braking first, then flat out,
    then the exit of a slow or medium corner, then the corner by its speed."""
    return np.select(
        [
            brake,
            throttle >= FULL_THROTTLE,
            after_apex & (corner_kph < FAST_KPH),
            corner_kph < SLOW_KPH,
            corner_kph < FAST_KPH,
        ],
        ["braking", "straight", "traction", "slow corner", "medium corner"],
        default="fast corner",
    )



def split_gap(both: pd.DataFrame) -> pd.DataFrame:
    """One row per kind: seconds the other lap loses there (+) or gains (-), and how many
    metres of the lap are that kind. both = compare_laps' table (reference = the faster lap)."""
    corner_kph, after = nearest_corner(both)
    kinds = kind_of(
        both["brake_ref"].astype(bool).to_numpy(),
        both["throttle_pct_ref"].to_numpy(),
        after,
        corner_kph,
    )
    step_s = both["delta_s"].diff().fillna(0.0)  # the gap made in each 5 m step
    step_m = both["distance_m"].diff().fillna(0.0)
    out = (
        pd.DataFrame({"kind": kinds, "seconds": step_s, "metres": step_m})
        .groupby("kind")
        .sum()
        .reindex(KINDS, fill_value=0.0)
    )
    out["share_of_lap"] = out["metres"] / out["metres"].sum()
    return out.reset_index()


def lap_gap(
    warehouse: Path, raw: Path, session_key: str, ref: tuple[str, int], other: tuple[str, int]
) -> tuple[pd.DataFrame, float, pd.DataFrame]:
    """(the split, the official lap time gap, the grid table) for two laps of one session:
    ref and other are (driver, lap number)."""
    both, info_ref, info_other = compare_laps(
        warehouse, raw, 5, (session_key, *ref), (session_key, *other)
    )
    official = info_other["lap_time_s"] - info_ref["lap_time_s"]
    return split_gap(both), official, both
