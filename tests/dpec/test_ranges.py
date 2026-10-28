"""Ranges and chances (step C3): honest width, no peeking ahead, chances that add up."""

import numpy as np
import pandas as pd
import pytest

from dpec.forecasting.ranges import add_ranges, coverage_table
from dpec.forecasting.simulate import simulate, walk_forward_chances


def fake_predictions(weekends=40, drivers=20, seed=1):
    """Guesses whose errors are normal with sd 0.5: an 80% range should be about +/-0.64."""
    rng = np.random.default_rng(seed)
    rows = []
    for w in range(weekends):
        guess = np.linspace(0, 3, drivers)
        rows.append(
            pd.DataFrame(
                {
                    "forecaster": "f",
                    "checkpoint": "after_quali",
                    "weekend": 202301 + w,
                    "driver_code": [f"D{d:02d}" for d in range(drivers)],
                    "lineage": [f"team_{d // 2}" for d in range(drivers)],
                    "predicted": guess,
                    "actual": guess + rng.normal(0, 0.5, drivers),
                }
            )
        )
    return pd.concat(rows, ignore_index=True)


def test_ranges_cover_about_80_percent():
    table = coverage_table(add_ranges(fake_predictions()))
    assert 0.75 <= table["inside"].item() <= 0.85
    assert table["width_pct"].item() == pytest.approx(2 * 0.64, abs=0.15)


def test_no_range_before_enough_past_weekends():
    r = add_ranges(fake_predictions(weekends=8), min_weekends=5)
    has_range = r.groupby("weekend")["low"].apply(lambda low: low.notna().all())
    assert has_range.tolist() == [False] * 5 + [True] * 3


def test_ranges_never_use_a_later_weekend():
    p = fake_predictions(weekends=12)
    before = add_ranges(p)
    later = p["weekend"] >= 202310
    changed = p.assign(actual=p["actual"].where(~later, 99.0))
    after = add_ranges(changed)
    pd.testing.assert_frame_equal(before[~later], after[~later])  # earlier ranges unchanged


def test_chances_add_up():
    p = fake_predictions(weekends=1)
    errors = np.random.default_rng(0).normal(0, 0.5, 400)
    c = simulate(p, errors)
    assert c["p_best"].sum() == pytest.approx(1.0)
    assert c["p_top3"].sum() == pytest.approx(3.0)
    assert c["p_best"].iloc[0] > c["p_best"].iloc[5]  # the fastest guess is most often fastest
    mates = c["p_beats_teammate"].iloc[0] + c["p_beats_teammate"].iloc[1]
    assert mates == pytest.approx(1.0)  # one of the two always wins


def test_chances_are_repeatable():
    p = fake_predictions(weekends=1)
    errors = np.linspace(-1, 1, 101)
    pd.testing.assert_frame_equal(simulate(p, errors), simulate(p, errors))


def test_walk_forward_chances_start_after_five_weekends():
    p = fake_predictions(weekends=7)
    c = walk_forward_chances(p)
    assert sorted(p.loc[c.index, "weekend"].unique()) == [202306, 202307]

