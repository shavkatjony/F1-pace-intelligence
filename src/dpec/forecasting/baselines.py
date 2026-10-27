"""Four simple guesses (and the 'no signal' floor). The real model of step C2 must beat them,
or say honestly where it doesn't.

Every forecaster has the same shape: forecaster(history, today) -> one guess per row of today.
history = every row of earlier weekends, answers included. today = this weekend with the
answers removed (targets.hide_answers). Nothing else goes in, so nothing else can leak in.
"""

import numpy as np
import pandas as pd

from dpec.forecasting.targets import TARGET

# the signals in order of trust (decision 0010): qualifying, then FP2 runs, then any long run
SIGNALS = ["quali_gap_pct", "fp2_long_run_gap_pct", "long_run_gap_pct"]
def no_signal(history: pd.DataFrame, today: pd.DataFrame) -> pd.Series:
    """Everyone gets the average gap of all earlier races. The floor every guess must beat."""
    return pd.Series(history[TARGET].mean(), index=today.index)


def team_form(history: pd.DataFrame, today: pd.DataFrame, races: int = 3) -> pd.Series:
    """The team's average gap over its last 3 dry races, both cars. A new team gets the average."""
    per_race = history.groupby(["lineage", "race_date"], as_index=False)[TARGET].mean()
    form = (
        per_race.sort_values("race_date")
        .groupby("lineage")[TARGET]
        .apply(lambda gaps: gaps.tail(races).mean())
    )
    return today["lineage"].map(form).fillna(history[TARGET].mean())


def last_race(history: pd.DataFrame, today: pd.DataFrame) -> pd.Series:
    """Each driver's gap at his previous dry race. A rookie gets his team's form."""
    last = history.sort_values("race_date").groupby("driver_code")[TARGET].last()
    return today["driver_code"].map(last).fillna(team_form(history, today))

def best_signal(today: pd.DataFrame) -> pd.Series:
    """Row by row, the most trusted signal this weekend has (NaN if none is known yet)."""
    found = pd.Series(np.nan, index=today.index)
    for name in SIGNALS:
        if name in today:
            found = found.fillna(today[name])
    return found


def signal_as_is(history: pd.DataFrame, today: pd.DataFrame) -> pd.Series:
    """Race gap = this weekend's best signal, unchanged. No signal: team form."""
    return best_signal(today).fillna(team_form(history, today))


def per_year_model(history: pd.DataFrame, today: pd.DataFrame, min_weekends: int = 3) -> pd.Series:
    """A straight line race gap ~ signal, fitted on one season only: this one, or the last one
    until this season has min_weekends races. One line per signal; no signal: team form."""
    weekends = history.groupby("season")["weekend"].nunique()
    usable = weekends[weekends >= min_weekends].index
    season = today["season"].iloc[0]
    train = history[history["season"] == (season if season in usable else usable.max())]
    guess = team_form(history, today)
    for name in reversed(SIGNALS):  # the most trusted signal goes last, so it wins
        if name not in today or train[name].notna().sum() < 10:
            continue
        both = train.dropna(subset=[name])
        slope, intercept = np.polyfit(both[name], both[TARGET], 1)
        known = today[name].notna()
        guess[known] = intercept + slope * today.loc[known, name]
    return guess


BASELINES = {
    "no_signal": no_signal,
    "last_race": last_race,
    "team_form": team_form,
    "signal_as_is": signal_as_is,
    "per_year_model": per_year_model,
}