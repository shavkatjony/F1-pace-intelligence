"""Shared model tests (step C2): its inputs only look back, and it learns a clear rule."""

import pandas as pd
import pytest
from test_forecasting import fake_table

from dpec.forecasting.backtest import walk_forward
from dpec.forecasting.features import add_form
from dpec.forecasting.model import recency_weights, shared_model
from dpec.forecasting.targets import TARGET, hide_answers


def test_team_form_starts_from_the_previous_race():
    table = fake_table(weekends=3)
    table[TARGET] = table["round"].astype(float)  # every car's gap = the round number
    form = add_form(table)
    assert (form.loc[table["round"] == 2, "team_form"] == 1.0).all()  # only round 1 is known
    assert form.loc[table["round"] == 1, "team_form"].isna().all()  # nothing known yet


def test_form_never_uses_a_later_race():
    table = fake_table(weekends=4)
    before = add_form(table)
    changed = table.copy()
    changed.loc[changed["round"] == 4, TARGET] = 99.0
    after = add_form(changed)
    early = table["round"] < 4
    columns = ["team_form", "driver_vs_team"]
    pd.testing.assert_frame_equal(before.loc[early, columns], after.loc[early, columns])


def test_driver_vs_team_finds_the_faster_teammate():
    table = fake_table(weekends=4)
    form = add_form(table)
    last = form[form["round"] == 4].set_index("driver_code")["driver_vs_team"]
    assert last["D00"] < 0 < last["D01"]  # D00 is 0.2% faster than D01 in the same team


def test_recency_weights_halve_every_halflife():
    dates = pd.Series(pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01", "2024-03-01"]))
    weights = recency_weights(dates, halflife=1)
    assert weights.tolist() == [0.25, 0.5, 1.0, 1.0]
    assert recency_weights(dates, halflife=None).tolist() == [1.0] * 4


def test_shared_model_learns_a_clear_rule():
    table = fake_table(weekends=8)
    table[TARGET] = 2 * table["quali_gap_pct"]  # Sunday's gap is exactly twice the quali gap
    history, today = table[table["round"] < 8], table[table["round"] == 8]
    guess = shared_model(history, hide_answers(today, "after_quali"))
    assert guess.to_numpy() == pytest.approx(today[TARGET].to_numpy(), abs=1e-6)


def test_shared_model_never_sees_the_future():
    table = fake_table(weekends=6)
    before = walk_forward(table, {"shared_model": shared_model})
    changed = table.copy()
    changed.loc[changed["round"] >= 5, TARGET] = 99.0
    after = walk_forward(changed, {"shared_model": shared_model})
    early = before["round"] < 5
    pd.testing.assert_frame_equal(before[early], after[early])
    