"""Decision tests (step C4): the plan maths add up, and the replay never sees the future.
They use made-up races, so they run in a second and need no warehouse."""

import numpy as np
import pandas as pd
import pytest

from dpec.decisions.plans import compare_plans, first_stop_window, flip_wear, plan_cost
from dpec.decisions.replay import replay
from dpec.decisions.tyres import circuit_history, useful_life


def fake_races(n=30, seed=0):
    """12 races in 2022, 18 in 2023, three circuits in turn. Race wear = half of practice wear
    plus noise; each race, 10 top-10 drivers stop once, around lap 20."""
    rng = np.random.default_rng(seed)
    dates = {
        2022: pd.date_range("2022-03-06", periods=12, freq="14D"),
        2023: pd.date_range("2023-03-05", periods=n - 12, freq="14D"),
    }
    rows, stops = [], []
    for i in range(n):
        season, rnd = (2022, i + 1) if i < 12 else (2023, i - 11)
        practice = rng.uniform(0.05, 0.25)
        rows.append(
            {
                "season": season,
                "round": rnd,
                "circuit": f"Circuit {i % 3}",
                "race_date": dates[season][rnd - 1],
                "race_laps": 57,
                "practice_long_runs": 30,
                "practice_deg_s_per_lap": practice,
                "race_deg_s_per_lap": practice / 2 + rng.normal(0, 0.01),
                "pit_loss_s": 22 + rng.normal(0, 1),
                "top10_stops": 1,
            }
        )
        for d in range(10):
            stops.append(
                {
                    "season": season,
                    "round": rnd,
                    "driver_code": f"D{d}",
                    "stops": 1,
                    "first_stop_lap": 20 + d % 3,
                    "green": True,
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(stops)


def test_plan_cost_adds_tyre_wear_and_stops():
    # 10 laps, 1 stop: two stints of 5 laps lose 0.1 * (0+1+2+3+4) = 1.0 s each
    assert plan_cost(0.1, 10, 20.0, 1) == pytest.approx(1.0 + 1.0 + 20.0)


def test_the_best_plan_chances_add_up():
    plans = compare_plans(np.array([0.02, 0.05, 0.10, 0.30]), 57, 22.0)
    assert plans["p_best"].sum() == pytest.approx(1.0)
    one = compare_plans(np.array([0.30]), 57, 22.0).set_index("stops")  # one replay: high wear
    assert one["p_best"].idxmax() == 3 and one.loc[3, "seconds_behind_best"] == 0.0


def test_low_tyre_wear_gives_a_wider_window():
    soft_first, soft_last = first_stop_window(0.02, 57, 22.0, 1)
    hard_first, hard_last = first_stop_window(0.20, 57, 22.0, 1)
    assert soft_last - soft_first > hard_last - hard_first  # timing matters less


def test_flip_wear_is_where_two_plans_cost_the_same():
    wear = flip_wear(57, 22.0, 1, 2)
    assert plan_cost(wear, 57, 22.0, 1) == pytest.approx(plan_cost(wear, 57, 22.0, 2))
    assert plan_cost(wear * 1.1, 57, 22.0, 2) < plan_cost(wear * 1.1, 57, 22.0, 1)


def test_useful_life_loses_one_pit_stop():
    laps = useful_life(0.1, 20.0, 100)
    assert 0.1 * laps * (laps - 1) / 2 == pytest.approx(20.0)
    assert useful_life(-0.01, 20.0, 57) == 57  # no wear: the set lasts the race


def test_circuit_history_falls_back_to_all_circuits():
    history = pd.DataFrame({"circuit": ["A", "A", "B"], "pit_loss_s": [20.0, 22.0, 30.0]})
    assert circuit_history(history, "pit_loss_s", "A") == 21.0
    assert circuit_history(history, "pit_loss_s", "New") == 22.0  # median of all three


def test_replay_never_sees_the_future():
    table, stops = fake_races()
    before, _ = replay(table, stops)
    changed = table.copy()
    future = (changed["season"] == 2023) & (changed["round"] >= 10)
    changed.loc[future, "race_deg_s_per_lap"] = 9.9  # rewrite what happened from round 10
    changed.loc[future, "top10_stops"] = 3
    after, _ = replay(changed, stops)
    early = before["round"] < 10
    pd.testing.assert_frame_equal(before[early], after[early])  # not one decision moved


def test_replay_starts_in_the_first_season_and_stops_at_until():
    table, stops = fake_races()
    replayed, plans = replay(table, stops, until=(2023, 5))
    assert replayed["season"].unique().tolist() == [2023]  # 2022 only teaches
    assert replayed["round"].tolist() == [1, 2, 3, 4, 5]
    assert set(plans) == {(2023, r) for r in range(1, 6)}
    