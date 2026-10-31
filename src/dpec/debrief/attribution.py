"""What a race gap is made of (step D1): two drivers' laps side by side, lap by lap.

Pairing the same lap numbers cancels what both cars share: the fuel burnt so far and the
track getting faster. What is left is explained by a small regression:

    gap (s) = pace + a * tyre age difference + b * tyre hardness difference
                   + c * A in traffic + d * B in traffic

Each part's share of the average gap = its coefficient x the average of its input, so the
parts add up to the average gap exactly. 'pace' is what remains on equal tyres in clean air:
car, driver, setup and the fuel the teams don't publish. Bootstrap: refit on laps drawn at
random 1,000 times; the 10th to 90th percentile of each part is its 80% range.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from telemetry_core.warehouse import query

PARTS = ["pace", "tyre_age", "tyre_compound", "a_traffic", "b_traffic"]
INPUTS = ["tyre_age_diff", "hardness_diff", "a_in_traffic", "b_in_traffic"]
TRAFFIC_S = 1.5  # within 1.5 s of the car ahead at the line = in its dirty air
MIN_LAPS = 10

PAIRED_LAPS_SQL = f"""
WITH laps AS (
    SELECT
        driver_code,
        lap_number,
        lap_time_s,
        tyre_age_laps,
        CASE compound WHEN 'SOFT' THEN 0 WHEN 'MEDIUM' THEN 1 WHEN 'HARD' THEN 2 END AS hardness,
        is_clean,
        -- the time since the car ahead crossed the line (any car: a lapped one is traffic too)
        lap_start_session_s - lag(lap_start_session_s) OVER (ORDER BY lap_start_session_s)
            AS gap_ahead_s
    FROM core_laps
    WHERE session_key = ?
)

SELECT
    a.lap_number,
    a.lap_time_s - b.lap_time_s AS gap_s,
    a.tyre_age_laps - b.tyre_age_laps AS tyre_age_diff,
    a.hardness - b.hardness AS hardness_diff,
    CAST(a.gap_ahead_s < {TRAFFIC_S} AS INTEGER) AS a_in_traffic,
    CAST(b.gap_ahead_s < {TRAFFIC_S} AS INTEGER) AS b_in_traffic
FROM laps AS a
INNER JOIN laps AS b USING (lap_number)
WHERE a.driver_code = ? AND b.driver_code = ? AND a.is_clean AND b.is_clean
    AND a.hardness IS NOT NULL AND b.hardness IS NOT NULL
ORDER BY a.lap_number
"""


def paired_laps(warehouse: Path, session_key: str, a: str, b: str) -> pd.DataFrame:
    """One row per lap number on which both A and B did a clean dry lap."""
    return query(warehouse, PAIRED_LAPS_SQL, [session_key, a.upper(), b.upper()])


def parts_of_gap(laps: pd.DataFrame) -> pd.Series:
    """Each part's share of the average gap (seconds per lap); they add up to the average gap.
    An input that never changes in these laps can't be told apart from pace: its part is NaN
    (not measured), and what it did is inside pace."""
    used = [c for c in INPUTS if laps[c].nunique() > 1]
    x = np.column_stack([np.ones(len(laps))] + [laps[c].to_numpy(float) for c in used])
    coef, *_ = np.linalg.lstsq(x, laps["gap_s"].to_numpy(float), rcond=None)
    means = x.mean(axis=0)
    out = pd.Series(np.nan, index=PARTS)
    out["pace"] = coef[0]
    for name, c, m in zip(used, coef[1:], means[1:], strict=True):
        out[PARTS[INPUTS.index(name) + 1]] = c * m
    return out


def bootstrap(laps: pd.DataFrame, draws: int = 1000, seed: int = 0) -> pd.DataFrame:
    """parts_of_gap refitted on `draws` resamples of the laps (drawn with replacement)."""
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(draws):
        sample = laps.iloc[rng.integers(0, len(laps), len(laps))]
        rows.append(parts_of_gap(sample))
    return pd.DataFrame(rows)


def attribute(laps: pd.DataFrame, draws: int = 1000) -> pd.DataFrame:
    """One row per part: seconds per lap, and its 80% range from the bootstrap."""
    if len(laps) < MIN_LAPS:
        raise ValueError(f"only {len(laps)} laps where both drivers were clean (need {MIN_LAPS})")
    boot = bootstrap(laps, draws)
    return pd.DataFrame(
        {
            "part": PARTS,
            "seconds_per_lap": parts_of_gap(laps).to_numpy(),
            "low": boot.quantile(0.1).to_numpy(),
            "high": boot.quantile(0.9).to_numpy(),
        }
    )
