"""Stop plans (step C4): how many stops, and when the first one.

Simple on purpose: every lap costs deg * tyre age seconds; every stop costs pit_loss seconds.
No compounds (their pace gaps can't be measured reliably from public data, decision 0014),
no traffic, no safety cars. Fuel burns the same in every plan, so it cancels out.
"""

import numpy as np
import pandas as pd

PLANS = [1, 2, 3]  # stops; at least one, because the rules make every car use two compounds
CLEAR = 0.65  # the best plan must win in 65% of the replays, or there's no clear decision


def plan_cost(deg: float, race_laps: int, pit_loss: float, stops: int) -> float:
    """Seconds lost to wear and stops with `stops` stops and stints as equal as possible."""
    stints = np.full(stops + 1, race_laps // (stops + 1))
    stints[: race_laps % (stops + 1)] += 1
    return float(stint_cost(deg, stints).sum() + stops * pit_loss)


def wear_weight(race_laps: int, stops: int) -> float:
    """plan_cost = deg * wear_weight + stops * pit_loss: the plan's laps of tyre age, added up."""
    return plan_cost(1.0, race_laps, 0.0, stops)


def compare_plans(deg_draws: np.ndarray, race_laps: int, pit_loss: float) -> pd.DataFrame:
    """One row per plan: its cost against the best plan (median and 80% range over the draws
    of tyre wear), and the share of draws in which it is the best plan."""
    stops = np.array(PLANS)
    weights = np.array([wear_weight(race_laps, n) for n in PLANS])
    costs = np.outer(deg_draws, weights) + stops * pit_loss  # cost = deg * weight + stops * loss
    behind = costs - costs.min(axis=1, keepdims=True)
    best = costs.argmin(axis=1)
    return pd.DataFrame(
        {
            "stops": PLANS,
            "seconds_behind_best": np.median(behind, axis=0),
            "low_s": np.percentile(behind, 10, axis=0),
            "high_s": np.percentile(behind, 90, axis=0),
            "p_best": [(best == k).mean() for k in range(len(PLANS))],
        }
    )


def first_stop_window(
    deg: float, race_laps: int, pit_loss: float, stops: int, tolerance_s: float = 1.0
) -> tuple[int, int]:
    """First-stop laps whose plan (the later stints split equally) is within tolerance_s of the
    best timing. Low wear = a wide window: timing barely matters."""
    first = np.arange(1, race_laps - stops + 1)
    rest = race_laps - first
    later = np.stack([rest // stops + (k < rest % stops) for k in range(stops)])
    cost = stint_cost(deg, first) + stint_cost(deg, later).sum(axis=0)
    ok = first[cost <= cost.min() + tolerance_s]
    return int(ok.min()), int(ok.max())


def stint_cost(deg: float, laps: np.ndarray) -> np.ndarray:
    """Seconds lost to tyre wear over a stint of `laps` laps on a new set."""
    return deg * laps * (laps - 1) / 2


def flip_wear(race_laps: int, pit_loss: float, stops: int, other: int) -> float:
    """The tyre wear (s/lap) at which plan `other` starts to beat plan `stops`. Both costs are
    straight lines in deg, so they cross at one point."""
    return (
        (other - stops) * pit_loss / (wear_weight(race_laps, stops) - wear_weight(race_laps, other))
    )
