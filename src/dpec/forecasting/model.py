"""The shared model (step C2, decision 0012): ONE regression for every track and every year.

    race gap = a + b * team_form + c * driver_vs_team                    (after practice)
    race gap = a + b * team_form + c * driver_vs_team + d * quali gap    (after qualifying)

It is refitted before every weekend on all earlier races. Newer races weigh more (half-life
12 races, about half a season), so it keeps learning through a season and after a rules change.
"""

import pandas as pd
import statsmodels.formula.api as smf

from dpec.forecasting.features import add_form

FORMULAS = {
    "after_practice": "race_pace_gap_pct ~ team_form + driver_vs_team",
    "after_quali": "race_pace_gap_pct ~ quali_gap_pct + team_form + driver_vs_team",
}
NEEDS = {"after_practice": [], "after_quali": ["quali_gap_pct"]}  # columns a formula can't miss
MIN_ROWS = 50  # fewer training rows than that: too few to fit, the guess stays team form


def recency_weights(race_dates: pd.Series, halflife: float | None) -> pd.Series:
    """1 for the last race, 0.5 for the race `halflife` races before it, and so on.
    halflife=None: every race counts the same."""
    races_ago = race_dates.rank(method="dense", ascending=False) - 1
    return 0.5 ** (races_ago / halflife) if halflife else pd.Series(1.0, index=race_dates.index)


def with_form(history: pd.DataFrame, today: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """history and today, each with the model's inputs added (see features.add_form)."""
    rows = add_form(pd.concat([history, today], keys=["history", "today"]))
    return rows.loc["history"], rows.loc["today"]


def training_rows(history: pd.DataFrame, checkpoint: str) -> pd.DataFrame:
    """The history rows a checkpoint's regression can learn from (no input missing)."""
    return history.dropna(subset=NEEDS[checkpoint] + ["team_form"])


def fit(
    history: pd.DataFrame, checkpoint: str, halflife: float | None = 12, formulas: dict = FORMULAS
):
    """The fitted regression for one checkpoint (history must already have the inputs)."""
    train = training_rows(history, checkpoint)
    weights = recency_weights(train["race_date"], halflife)
    return smf.wls(formulas[checkpoint], train, weights=weights).fit()


def shared_model(
    history: pd.DataFrame,
    today: pd.DataFrame,
    halflife: float | None = 12,
    formulas: dict = FORMULAS,
) -> pd.Series:
    """A forecaster like the baselines: one guess per row of today. Everyone gets the
    after-practice guess; drivers with a qualifying time then get the after-quali one.
    halflife and formulas are there for experiments; the defaults are decision 0012."""
    h, t = with_form(history, today)
    guess = t["team_form"].copy()  # kept only if there's too little history to fit
    for checkpoint, needs in NEEDS.items():
        if any(column not in t for column in needs) or len(training_rows(h, checkpoint)) < MIN_ROWS:
            continue  # not known yet at this checkpoint, or too little to learn from
        known = t.dropna(subset=needs).index
        model = fit(h, checkpoint, halflife, formulas)
        guess[known] = model.predict(t.loc[known]).to_numpy()
    return guess
