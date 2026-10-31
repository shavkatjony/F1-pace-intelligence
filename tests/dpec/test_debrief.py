"""Debrief tests (step D1): the lap split adds up to the gap, every grid row gets the right
kind, and the race split finds effects that were put in on purpose."""

import numpy as np
import pandas as pd
import pytest

from dpec.debrief.attribution import attribute, bootstrap, parts_of_gap
from dpec.debrief.segments import KINDS, kind_of, split_gap


def test_kind_of_checks_braking_first_then_flat_out():
    brake = np.array([True, False, False, False, False, False])
    throttle = np.array([100, 100, 60, 60, 60, 60])
    after = np.array([False, False, True, False, False, True])
    corner = np.array([90, 90, 90, 90, 150, 230])
    assert kind_of(brake, throttle, after, corner).tolist() == [
        "braking",  # braking wins even at full throttle (a lift-and-brake overlap)
        "straight",
        "traction",  # after the apex of a slow corner, not yet flat out
        "slow corner",
        "medium corner",
        "fast corner",  # the exit of a fast corner is still the corner
    ]


def fake_lap_pair(n=401):
    """Two laps on a 2 km grid with one slow corner in the middle. B loses 0.2 s in the corner
    and 0.1 s on the straight after it."""
    d = np.linspace(0, 2000, n)
    speed = 300 - 220 * np.exp(-(((d - 1000) / 80) ** 2))  # 80 km/h at the apex (1,000 m)
    brake = (d > 850) & (d < 960)
    throttle = np.where(brake, 0, np.where(speed > 290, 100, 50))
    lose = np.where(np.abs(d - 1000) < 100, 0.2 / 40, 0) + np.where(d > 1300, 0.1 / 140, 0)
    delta = np.cumsum(lose)
    return pd.DataFrame(
        {
            "distance_m": d,
            "speed_kph_ref": speed,
            "brake_ref": brake,
            "throttle_pct_ref": throttle,
            "delta_s": delta - delta[0],
        }
    )


def test_split_adds_up_to_the_whole_gap():
    both = fake_lap_pair()
    split = split_gap(both)
    assert split["kind"].tolist() == KINDS
    assert split["seconds"].sum() == pytest.approx(both["delta_s"].iloc[-1], abs=1e-9)
    assert split["share_of_lap"].sum() == pytest.approx(1.0)
    by_kind = split.set_index("kind")["seconds"]
    assert by_kind["straight"] == pytest.approx(0.1, abs=0.01)  # the time lost after 1,300 m
    assert by_kind[["braking", "slow corner", "traction"]].sum() == pytest.approx(0.2, abs=0.01)


def fake_race(n=60, seed=0):
    """Paired laps: A is 0.5 s slower on equal tyres, loses 0.05 s per lap of extra tyre age
    and 0.4 s on a lap in traffic."""
    rng = np.random.default_rng(seed)
    laps = pd.DataFrame(
        {
            "lap_number": np.arange(2, n + 2),
            "tyre_age_diff": rng.integers(-5, 10, n),
            "hardness_diff": rng.integers(-1, 2, n),
            "a_in_traffic": (rng.random(n) < 0.3).astype(int),
            "b_in_traffic": 0,  # B never in traffic: can't be measured
        }
    )
    laps["gap_s"] = (
        0.5 + 0.05 * laps["tyre_age_diff"] + 0.4 * laps["a_in_traffic"] + rng.normal(0, 0.05, n)
    )
    return laps


def test_parts_add_up_to_the_average_gap():
    laps = fake_race()
    parts = parts_of_gap(laps)
    assert parts.sum() == pytest.approx(laps["gap_s"].mean())  # NaN parts are skipped
    assert np.isnan(parts["b_traffic"])  # never different, so not measured
    assert parts["a_traffic"] == pytest.approx(0.4 * laps["a_in_traffic"].mean(), abs=0.03)
    assert parts["pace"] == pytest.approx(0.5, abs=0.05)


def test_bootstrap_is_repeatable_and_ranges_hold_the_estimate():
    laps = fake_race()
    assert bootstrap(laps, draws=50).equals(bootstrap(laps, draws=50))  # same seed, same draws
    table = attribute(laps, draws=200).set_index("part").dropna()
    assert (
        (table["low"] <= table["seconds_per_lap"]) & (table["seconds_per_lap"] <= table["high"])
    ).all()


def test_too_few_laps_is_an_error():
    with pytest.raises(ValueError, match="only 5 laps"):
        attribute(fake_race(n=5))
