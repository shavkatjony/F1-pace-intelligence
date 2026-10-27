"""Inputs for the shared model (step C2), built only from races before each weekend.

team_form: the team's race gap, recent races weighing more. Each race older halves its weight
every `team_halflife` races (an exponentially weighted mean, pandas `ewm`).
driver_vs_team: how far a driver usually is from his own team's average (- = faster than it).
"""

import pandas as pd

from dpec.forecasting.targets import TARGET


def add_form(
    rows: pd.DataFrame, team_halflife: float = 3, driver_halflife: float = 6
) -> pd.DataFrame:
    """rows = history and today together; today's answers are empty. Returns the same rows with
    team_form and driver_vs_team added, each from races before that row's own weekend."""
    races = (
        rows.groupby(["lineage", "race_date"], as_index=False)[TARGET]
        .mean()
        .rename(columns={TARGET: "team_race_gap"})
        .sort_values("race_date")
    )
    races["team_form"] = races.groupby("lineage")["team_race_gap"].transform(
        lambda gaps: gaps.shift().ewm(halflife=team_halflife).mean()  # shift: this race not yet
    )
    out = rows.merge(races, on=["lineage", "race_date"], how="left")
    out.index = rows.index
    field = rows.groupby("race_date")[TARGET].mean().sort_index()
    field_before = field.expanding().mean().shift()  # average gap of every earlier race
    out["team_form"] = out["team_form"].fillna(out["race_date"].map(field_before))  # new team

    out["vs_team"] = out[TARGET] - out["team_race_gap"]
    in_order = out.sort_values("race_date", kind="stable")
    out["driver_vs_team"] = (
        in_order.groupby("driver_code")["vs_team"]
        .transform(lambda gaps: gaps.shift().ewm(halflife=driver_halflife).mean())
        .fillna(0.0)  # a rookie: same as his team
    )
    return out.drop(columns=["team_race_gap", "vs_team"])