"""Walk-forward backtest: forecast every past weekend with only what was known before it.

For each dry weekend W from 2023 on: history = all weekends that raced before W, and today = W
with the answers removed. Every forecaster guesses; the guess is kept next to the answer.
Nothing from W's race or later can reach a forecaster: it is cut out before the call.
"""

import pandas as pd

from dpec.forecasting.targets import CHECKPOINTS, TARGET, hide_answers

KEYS = ["season", "round", "weekend", "circuit", "driver_code", "lineage"]


def walk_forward(
    table: pd.DataFrame,
    forecasters: dict,
    first_season: int = 2023,
    min_drivers: int = 8,
    weekends: list[int] | None = None,
) -> pd.DataFrame:
    """One row per driver, weekend, checkpoint and forecaster: predicted vs actual.
    weekends: forecast only these (a live forecast needs only the last few, for its range)."""
    rows = []
    chosen = table[table["season"] >= first_season]
    if weekends is not None:
        chosen = chosen[chosen["weekend"].isin(weekends)]
    for _, today in chosen.groupby("weekend", sort=False):
        history = table[table["race_date"] < today["race_date"].iloc[0]]
        if len(today) < min_drivers or history.empty:
            continue
        for checkpoint in CHECKPOINTS:
            seen = hide_answers(today, checkpoint)
            for name, forecaster in forecasters.items():
                guess = forecaster(history, seen)
                rows.append(
                    today[KEYS].assign(
                        checkpoint=checkpoint,
                        forecaster=name,
                        predicted=guess.to_numpy(),
                        actual=today[TARGET].to_numpy(),
                    )
                )
    return pd.concat(rows, ignore_index=True)


def score(
    predictions: pd.DataFrame, lap_s: float = 90, by: tuple = ("checkpoint", "forecaster")
) -> pd.DataFrame:
    """One row per checkpoint and forecaster (or per `by`). mae_pct = mean absolute error in %
    of a lap; mae_s = the same in seconds on a lap_s lap; median_rho = how well the order
    matches (Spearman per weekend, then the median over weekends)."""
    p = predictions.assign(abs_error=(predictions["predicted"] - predictions["actual"]).abs())
    groups = list(by)
    rho = (
        p.groupby(groups + ["weekend"])[["predicted", "actual"]]
        .corr(method="spearman")
        .xs("predicted", level=-1)["actual"]
        .groupby(groups)
        .median()
    )
    out = p.groupby(groups).agg(
        weekends=("weekend", "nunique"), rows=("abs_error", "size"), mae_pct=("abs_error", "mean")
    )
    out["mae_s"] = out["mae_pct"] / 100 * lap_s
    out["median_rho"] = rho
    return out.reset_index().sort_values(groups[:-1] + ["mae_pct"])
