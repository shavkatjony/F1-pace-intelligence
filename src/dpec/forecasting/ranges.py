"""Honest ranges (step C3, decision 0013): how far off the model usually is, from its own past.

80% range = guess +/- the 80th percentile of the size of the model's errors in the previous 10
forecast weekends (same forecaster, same checkpoint). That is split-conformal prediction, done
walk-forward: nothing from this weekend or later is used. When the errors grow (a rules
change), the ranges grow too, a few races later.
"""

import numpy as np
import pandas as pd

COVERAGE = 0.8
WINDOW = 10  # forecast weekends of past errors (chosen on the tune years, decision 0013)
MIN_WEEKENDS = 5  # fewer past weekends than that: no range yet


def past_errors(predictions: pd.DataFrame, weekend: int, window: int = WINDOW) -> pd.Series:
    """actual - predicted over the `window` forecast weekends before `weekend`.
    predictions = one forecaster at one checkpoint."""
    earlier = np.sort(predictions.loc[predictions["weekend"] < weekend, "weekend"].unique())
    last = predictions["weekend"].isin(earlier[-window:])
    return (predictions["actual"] - predictions["predicted"])[last]


def add_ranges(
    predictions: pd.DataFrame,
    coverage: float = COVERAGE,
    window: int = WINDOW,
    min_weekends: int = MIN_WEEKENDS,
) -> pd.DataFrame:
    """Walk-forward predictions with low and high added (empty until min_weekends have passed)."""
    out = predictions.assign(low=np.nan, high=np.nan)
    for _, one in out.groupby(["forecaster", "checkpoint"]):
        for weekend in one["weekend"].unique():
            errors = past_errors(one, weekend, window)
            if one.loc[errors.index, "weekend"].nunique() < min_weekends:
                continue
            half = errors.abs().quantile(coverage)
            rows = one.index[one["weekend"] == weekend]
            out.loc[rows, "low"] = out.loc[rows, "predicted"] - half
            out.loc[rows, "high"] = out.loc[rows, "predicted"] + half
    return out


def coverage_table(predictions: pd.DataFrame, by: tuple = ("checkpoint",)) -> pd.DataFrame:
    """How often the real race pace landed inside the range, and how wide the range was (in %
    of a lap). Rows without a range yet are left out."""
    # Lesson 15, Part 2 [You]: one row per group in `by`, with the columns
    # rows (how many rows), inside (share of rows with actual between low and high),
    # width_pct (mean of high - low). Leave out rows where low is empty.
    raise NotImplementedError

def coverage_table(predictions: pd.DataFrame, by: tuple = ("checkpoint",)) -> pd.DataFrame:
    """How often the real race pace landed inside the range, and how wide the range was (in %
    of a lap). Rows without a range yet are left out."""
    p = predictions.dropna(subset=["low"])
    p = p.assign(inside=p["actual"].between(p["low"], p["high"]), width_pct=p["high"] - p["low"])
    return (
        p.groupby(list(by))
        .agg(rows=("inside", "size"), inside=("inside", "mean"), width_pct=("width_pct", "mean"))
        .reset_index()
    )
