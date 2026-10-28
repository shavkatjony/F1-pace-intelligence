"""Replay every past dry race (step C4): the decision the packet would have made before the
race, from earlier races and this weekend's practice only, next to what really happened.

Scored the way the GPT team-engineering review asked: tyre wear (error in s/lap), the number
of stops, and the share of real first stops inside the window. Never "did the plan win": the
other plans were not raced.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from dpec.decisions.plans import CLEAR, compare_plans, first_stop_window
from dpec.decisions.tyres import circuit_history, strategy_table, useful_life, wear_forecast
from telemetry_core.warehouse import query

ERROR_WINDOW = 20  # races of past wear-forecast errors used for its range and the replays
MIN_ERRORS = 5  # fewer than that: no range yet
MIN_SHIFT_STOPS = 20  # real first stops needed before the window is moved by the undercut

FIRST_STOPS_SQL = """
SELECT s.season, s.round, s.driver_code, r.finish_position,
    count(*) OVER (PARTITION BY s.season, s.round, s.driver_code) - 1 AS stops,
    s.last_lap AS first_stop_lap,
    NOT (l.under_safety_car OR l.under_vsc OR l.under_red_flag) AS green
FROM mart_stints AS s
INNER JOIN core_results AS r
    ON r.season = s.season AND r.round = s.round AND r.driver_code = s.driver_code
    AND r.session_type = 'R'
INNER JOIN core_laps AS l
    ON l.session_key = s.session_key AND l.driver_code = s.driver_code
    AND l.lap_number = s.last_lap
WHERE s.session_type = 'R' AND r.finish_position <= 10
QUALIFY s.stint = min(s.stint) OVER (PARTITION BY s.season, s.round, s.driver_code)
"""


def first_stops(warehouse: Path) -> pd.DataFrame:
    """Each top-10 finisher's first stop: its lap, his number of stops, and whether it was
    green (no safety car, VSC or red flag on the in-lap). Drivers who never stopped: left out."""
    stops = query(warehouse, FIRST_STOPS_SQL)
    return stops[stops["stops"] >= 1]


def decide(
    history: pd.DataFrame, today: pd.Series, errors: np.ndarray, shift: dict, seed: int = 0
) -> dict:
    """The decision for one race, from earlier races only: tyre wear and its 80% range, pit loss,
    useful life, every plan's cost, the preferred plan (or none), and the first-stop window.
    errors = earlier wear-forecast errors; shift = laps to move each plan's window by."""
    deg = wear_forecast(history, today)
    pit_loss = circuit_history(history, "pit_loss_s", today["circuit"])
    laps = int(today["race_laps"])
    if len(errors):  # replay the race 4,000 times with tyre wear as wrong as it has been
        half = float(np.quantile(np.abs(errors), 0.8))
        draws = np.maximum(deg + np.random.default_rng(seed).choice(errors, 4000), 0.0)
    else:  # no errors to learn from yet: one replay, no range
        half, draws = np.nan, np.array([deg])
    plans = compare_plans(draws, laps, pit_loss)
    best = plans.loc[plans["p_best"].idxmax()]
    stops = int(best["stops"])
    first, last = first_stop_window(max(deg, 0.001), laps, pit_loss, stops)
    move = shift.get(stops, 0)
    return {
        "deg": deg,
        "deg_low": max(deg - half, 0.0),
        "deg_high": deg + half,
        "pit_loss_s": pit_loss,
        "useful_life": useful_life(deg, pit_loss, laps),
        "plans": plans,
        "stops": stops,
        "p_best": float(best["p_best"]),
        "clear": bool(best["p_best"] >= CLEAR),
        "tyre_window": (first, last),
        "shift": move,
        "window": (max(1, first + move), min(laps - stops, last + move)),
    }


def replay_all(
    warehouse: Path, first_season: int = 2023, until: tuple[int, int] | None = None
) -> tuple[pd.DataFrame, dict]:
    """replay() on the warehouse's tables."""
    return replay(strategy_table(warehouse), first_stops(warehouse), first_season, until)


def replay(
    table: pd.DataFrame,
    stops: pd.DataFrame,
    first_season: int = 2023,
    until: tuple[int, int] | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Every dry race from first_season (up to `until` = (season, round), if given): one row of
    what the packet said and what happened, plus each race's full plan table (for the packets).
    table = strategy_table(), oldest race first; stops = first_stops()."""
    rows, plans, errors, moved = [], {}, [], []
    for _, today in table.iterrows():
        if until and (today["season"], today["round"]) > until:
            break  # races are in date order: everything after this is later
        if today["season"] < first_season or pd.isna(today["race_deg_s_per_lap"]):
            continue
        history = table[table["race_date"] < today["race_date"]]
        recent = np.array(errors[-ERROR_WINDOW:]) if len(errors) >= MIN_ERRORS else np.array([])
        d = decide(history, today, recent, undercut_shift(moved))

        here = stops[(stops["season"] == today["season"]) & (stops["round"] == today["round"])]
        same_plan = here[here["green"] & (here["stops"] == d["stops"])]
        first, last = d["window"]
        rows.append(
            {
                **{k: today[k] for k in ["season", "round", "circuit", "race_laps"]},
                **{k: d[k] for k in ["deg", "deg_low", "deg_high", "pit_loss_s", "useful_life"]},
                **{k: d[k] for k in ["stops", "p_best", "clear", "shift"]},
                "window_first": first,
                "window_last": last,
                "actual_deg": today["race_deg_s_per_lap"],
                "actual_stops": today["top10_stops"],
                "green_first_stops": len(same_plan),
                "inside_window": int(same_plan["first_stop_lap"].between(first, last).sum()),
            }
        )
        plans[(int(today["season"]), int(today["round"]))] = d["plans"]
        # only now, after the race, its answers join what later races may learn from
        errors.append(today["race_deg_s_per_lap"] - d["deg"])
        for row in here[here["green"]].itertuples():
            moved.append((row.stops, row.first_stop_lap - centre_for(row.stops, d, today)))
    return pd.DataFrame(rows), plans

def decide_next(
    table: pd.DataFrame, stops: pd.DataFrame, today: pd.Series, first_season: int = 2023
) -> dict:
    """The decision for a race that hasn't run yet (step C5). today = its strategy row, with
    practice filled in and the race columns empty. It learns from every earlier race exactly
    what replay() learns: the wear forecast's errors and the undercut."""
    history = table[table["race_date"] < today["race_date"]]
    replayed, _ = replay(history, stops, first_season)
    errors = (replayed["actual_deg"] - replayed["deg"]).to_list()
    recent = np.array(errors[-ERROR_WINDOW:]) if len(errors) >= MIN_ERRORS else np.array([])
    moved = []
    for race in replayed.to_dict("records"):
        here = stops[(stops["season"] == race["season"]) & (stops["round"] == race["round"])]
        for row in here[here["green"]].itertuples():
            moved.append((row.stops, row.first_stop_lap - centre_for(row.stops, race, race)))
    return decide(history, today, recent, undercut_shift(moved))


def undercut_shift(moved: list[tuple[int, float]]) -> dict[int, int]:
    """Per plan (number of stops): how many laps before (-) or after the middle of the
    tyre-only window real first stops came in earlier races. The undercut makes teams stop
    early. Only once MIN_SHIFT_STOPS stops of that plan have been seen."""
    by_plan: dict[int, list[float]] = {}
    for stops, laps in moved:
        by_plan.setdefault(stops, []).append(laps)
    return {k: round(float(np.median(v))) for k, v in by_plan.items() if len(v) >= MIN_SHIFT_STOPS}


def centre_for(stops: int, decision: dict, today: pd.Series) -> float:
    """The middle of the tyre-only window of a plan with `stops` stops (for the undercut)."""
    first, last = first_stop_window(
        max(decision["deg"], 0.001), int(today["race_laps"]), decision["pit_loss_s"], stops
    )
    return (first + last) / 2


def score(replayed: pd.DataFrame) -> pd.DataFrame:
    """The replay in five numbers per group of races: clear decisions and the rest."""
    r = replayed.assign(
        right=replayed["stops"] == replayed["actual_stops"],
        wear_error=(replayed["actual_deg"] - replayed["deg"]).abs(),
        wear_inside=replayed["actual_deg"].between(replayed["deg_low"], replayed["deg_high"]),
    )
    r["decision"] = np.where(r["clear"], "clear", "no clear decision")
    parts = [r.assign(decision="all races"), r]
    return (
        pd.concat(parts)
        .groupby("decision", sort=False)
        .agg(
            races=("right", "size"),
            stops_right=("right", "mean"),
            always_one_stop_right=("actual_stops", lambda s: (s == 1).mean()),
            wear_error_s_per_lap=("wear_error", "mean"),
            wear_inside_range=("wear_inside", "mean"),
            first_stops=("green_first_stops", "sum"),
            inside_window=("inside_window", "sum"),
        )
        .assign(window_share=lambda t: t["inside_window"] / t["first_stops"])
        .reset_index()
    )

