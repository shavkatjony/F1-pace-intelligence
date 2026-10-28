"""From pace guesses to chances (step C3): replay Sunday's race pace order thousands of times.

Each replay adds to every driver's guess one error drawn at random from the model's own past
errors (ranges.past_errors). A driver's chance of the best race pace = the share of replays
in which he has it. Same for a top-3 pace, and for beating his teammate.
"""

import numpy as np
import pandas as pd

from dpec.forecasting.ranges import MIN_WEEKENDS, WINDOW, past_errors

CHANCES = ["p_best", "p_top3", "mean_rank", "p_beats_teammate"]


def simulate(
    forecast: pd.DataFrame, errors: np.ndarray, draws: int = 4000, seed: int = 0
) -> pd.DataFrame:
    """forecast = one weekend (columns lineage and predicted). Returns the CHANCES per driver."""
    rng = np.random.default_rng(seed)  # same seed, same answer: a forecast must be repeatable
    pace = forecast["predicted"].to_numpy() + rng.choice(errors, size=(draws, len(forecast)))
    rank = pace.argsort(axis=1).argsort(axis=1) + 1  # 1 = best race pace in that replay
    out = pd.DataFrame(
        {
            "p_best": (rank == 1).mean(axis=0),
            "p_top3": (rank <= 3).mean(axis=0),
            "mean_rank": rank.mean(axis=0),
            "p_beats_teammate": np.nan,
        },
        index=forecast.index,
    )
    team = forecast["lineage"].to_numpy()
    for i in range(len(team)):
        mates = np.flatnonzero(team == team[i])
        if len(mates) == 2:  # one teammate (a team with a stand-in can have three drivers)
            mate = mates[mates != i][0]
            out.iloc[i, out.columns.get_loc("p_beats_teammate")] = (
                pace[:, i] < pace[:, mate]
            ).mean()
    return out


def walk_forward_chances(
    predictions: pd.DataFrame, window: int = WINDOW, min_weekends: int = MIN_WEEKENDS
) -> pd.DataFrame:
    """The CHANCES for walk-forward predictions of ONE forecaster, each weekend simulated from
    that forecaster's errors before it (no row until min_weekends weekends have passed)."""
    parts = [pd.DataFrame(columns=CHANCES, dtype=float)]
    for _, one in predictions.groupby("checkpoint"):
        for weekend, today in one.groupby("weekend"):
            errors = past_errors(one, weekend, window)
            if one.loc[errors.index, "weekend"].nunique() >= min_weekends:
                parts.append(simulate(today, errors.to_numpy()))
    return pd.concat(parts)

