"""Distance grid tests on made-up telemetry, where the right answer is easy to work out."""

import numpy as np
import pandas as pd
import pytest

from telemetry_core.alignment.distance_grid import apexes, delta, to_grid


def steady_lap(seconds=10.0, kph=180.0, hz=4):
    """A car at one speed, 4 samples per second. 180 km/h = 50 m/s."""
    t = np.arange(0.0, seconds + 1e-9, 1 / hz)
    return pd.DataFrame(
        {
            "time_s": t,
            "speed_kph": kph,
            "throttle_pct": 100.0,
            "rpm": 11000.0,
            "gear": np.where(t < 5, 7, 8),
            "brake": False,
            "drs": 0,
        }
    )


def test_distance_and_time_on_the_grid():
    grid = to_grid(steady_lap(), step_m=5)
    assert grid["distance_m"].iloc[-1] == pytest.approx(500)  # 50 m/s x 10 s
    assert np.diff(grid["distance_m"]).max() == pytest.approx(5)
    at_250 = grid.loc[grid["distance_m"] == 250, "time_s"].item()
    assert at_250 == pytest.approx(5.0)


def test_exact_start_and_end_line():
    # the lap starts and ends between two samples: the grid still starts at 0 m and 0 s
    grid = to_grid(steady_lap(), step_m=5, start_s=1.1, end_s=9.1)
    assert grid["time_s"].iloc[0] == pytest.approx(0.0)
    assert grid["time_s"].iloc[-1] == pytest.approx(8.0)  # the official lap time
    assert grid["distance_m"].iloc[-1] == pytest.approx(400)


def test_stretch_to_the_reference_length():
    grid = to_grid(steady_lap(), step_m=5, lap_length_m=520)
    assert grid["distance_m"].iloc[-1] == pytest.approx(520)
    assert grid["time_s"].iloc[-1] == pytest.approx(10.0)  # stretching never changes time


def test_gear_is_never_in_between():
    grid = to_grid(steady_lap(), step_m=5)
    assert set(grid["gear"]) == {7, 8}
    assert grid.loc[grid["distance_m"] == 245, "gear"].item() == 7
    assert grid.loc[grid["distance_m"] == 255, "gear"].item() == 8


def test_delta_of_a_slower_lap():
    fast = to_grid(steady_lap(kph=180), step_m=5)
    slow = to_grid(steady_lap(seconds=10.0, kph=180), step_m=5)
    slow["time_s"] = slow["time_s"] * 1.02  # 2% slower everywhere
    both = delta(fast, slow)
    assert both["delta_s"].iloc[0] == pytest.approx(0.0)
    assert both["delta_s"].iloc[-1] == pytest.approx(0.2)  # 2% of 10 s
    assert (np.diff(both["delta_s"]) >= 0).all()  # the gap only grows


def test_apexes_find_the_slow_corners():
    d = np.arange(0.0, 4000.0, 5.0)
    speed = 300 - 220 * np.exp(-(((d - 1000) / 60) ** 2)) - 150 * np.exp(-(((d - 3000) / 60) ** 2))
    grid = pd.DataFrame({"distance_m": d, "speed_kph": speed})
    found = apexes(grid)
    assert found["distance_m"].tolist() == [1000, 3000]
    assert found["speed_kph"].round().tolist() == [80, 150]
    