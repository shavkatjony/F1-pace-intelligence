"""Forecasting tests (step C1): the answers stay hidden, the future can't leak in, the scores add up.
They use a small made-up season, so they run in a second and need no warehouse."""

import numpy as np
import pandas as pd
import pytest

from dpec.forecasting import baselines
from dpec.forecasting.backtest import score, walk_forward
from dpec.forecasting.targets import TARGET, hide_answers


def fake_table(weekends=6, drivers=10, seed=0):
    """A made-up season: driver k's car is 0.2% slower than driver k-1's, plus noise.
    Two drivers per team, one race every two weeks."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2023-03-05", periods=weekends, freq="14D")
    rows = []
    for w in range(weekends):
        for d in range(drivers):
            speed = 0.2 * d
            rows.append(
                {
                    "season": 2023,
                    "round": w + 1,
                    "weekend": 202301 + w,
                    "race_date": dates[w],
                    "circuit": f"Circuit {w + 1}",
                    "driver_code": f"D{d:02d}",
                    "team": f"Team {d // 2}",
                    "lineage": f"team_{d // 2}",
                    "is_sprint_weekend": False,
                    "long_run_gap_pct": speed + rng.normal(0, 0.4),
                    "fp2_long_run_gap_pct": speed + rng.normal(0, 0.3),
                    "quali_gap_pct": speed + rng.normal(0, 0.1),
                    "grid_position": d + 1,
                    "race_pace_gap_pct": speed + rng.normal(0, 0.1),
                    "race_clean_laps": 50,
                    "finish_position": d + 1,
                    "points": 0,
                }
            )
    return pd.DataFrame(rows)


def test_hide_answers_removes_what_is_not_known_yet():
    today = fake_table(weekends=1)
    practice = hide_answers(today, "after_practice")
    quali = hide_answers(today, "after_quali")
    for hidden in [TARGET, "finish_position", "points"]:
        assert hidden not in practice and hidden not in quali
    assert "quali_gap_pct" not in practice and "grid_position" not in practice
    assert "quali_gap_pct" in quali and "long_run_gap_pct" in practice


def test_a_forecaster_cannot_read_todays_answer():
    def cheat(history, today):
        return today[TARGET]

    with pytest.raises(KeyError):
        walk_forward(fake_table(), {"cheat": cheat})


def test_walk_forward_never_sees_the_future():
    table = fake_table()
    before = walk_forward(table, baselines.BASELINES)
    changed = table.copy()
    future = changed["round"] >= 5
    changed.loc[future, TARGET] = 99.0  # rewrite what happened in rounds 5 and 6
    after = walk_forward(changed, baselines.BASELINES)
    early = before["round"] < 5
    pd.testing.assert_frame_equal(before[early], after[early])  # rounds 2-4: not one guess moved


def test_walk_forward_starts_after_the_first_race():
    predictions = walk_forward(fake_table(), {"no_signal": baselines.no_signal})
    assert predictions["round"].min() == 2  # round 1 has no history to learn from
    assert set(predictions["checkpoint"]) == {"after_practice", "after_quali"}


def test_team_form_is_the_average_of_the_last_three_races():
    history = fake_table(weekends=4)
    history[TARGET] = history["round"].astype(float)  # every car's gap = the round number
    today = hide_answers(fake_table(weekends=1).assign(round=5), "after_practice")
    form = baselines.team_form(history, today)
    assert (form == 3.0).all()  # rounds 2, 3 and 4


def test_last_race_gives_a_rookie_his_teams_form():
    history = fake_table(weekends=3)
    today = hide_answers(fake_table(weekends=1).assign(round=4), "after_practice")
    today.loc[0, "driver_code"] = "NEW"
    guess = baselines.last_race(history, today)
    assert guess[0] == pytest.approx(baselines.team_form(history, today)[0])


def test_signal_as_is_prefers_qualifying():
    today = hide_answers(fake_table(weekends=1), "after_quali")
    guess = baselines.signal_as_is(fake_table(weekends=2), today)
    assert guess.equals(today["quali_gap_pct"])


def test_score_counts_errors_and_order():
    predictions = pd.DataFrame(
        {
            "checkpoint": "after_quali",
            "forecaster": "f",
            "weekend": [1, 1, 1, 2, 2, 2],
            "predicted": [0.0, 1.0, 2.0, 0.0, 1.0, 2.0],
            "actual": [0.0, 1.0, 3.0, 2.0, 1.0, 0.0],  # weekend 1 in order, weekend 2 reversed
        }
    )
    row = score(predictions).iloc[0]
    assert row["mae_pct"] == pytest.approx(5 / 6)
    assert row["median_rho"] == pytest.approx(0.0)  # median of +1 and -1
    assert row["weekends"] == 2


def test_baselines_beat_no_signal_on_a_clear_season():
    scores = score(walk_forward(fake_table(weekends=8), baselines.BASELINES))
    quali = scores[scores["checkpoint"] == "after_quali"].set_index("forecaster")["mae_pct"]
    assert quali["per_year_model"] < quali["no_signal"]
    assert quali["team_form"] < quali["no_signal"]
    