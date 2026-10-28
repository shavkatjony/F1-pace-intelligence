"""Freeze one forecast (step C5): race pace for every car and the tyre and stop decision, made
from this weekend's sessions before the target and earlier races only, then written once.

It is the backtest's code, run on one weekend: the shared model for the pace, its errors in the
last 10 forecast weekends for the 80% ranges and the chances, the five baselines (frozen too,
so the skill test is fair), and decide_next for the tyres and stops.
"""

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from dpec.decisions.packet import our_lineage, reasons, runner_up
from dpec.decisions.replay import decide_next, first_stops
from dpec.decisions.tyres import strategy_table
from dpec.forecasting.backtest import walk_forward
from dpec.forecasting.baselines import BASELINES
from dpec.forecasting.model import shared_model
from dpec.forecasting.ranges import COVERAGE, MIN_WEEKENDS, WINDOW, past_errors
from dpec.forecasting.simulate import simulate
from dpec.forecasting.targets import forecast_table
from dpec.record.ledger import MARGIN_MIN, Decision, DriverForecast, Forecast, Plan, code_version
from dpec.record.live import TARGETS, start_of, today_rows, weekend_sessions
from telemetry_core.warehouse import query

METHOD = (
    "shared model (decision 0012); 80% split-conformal range from its errors in the last "
    f"{WINDOW} forecast weekends (decision 0013); tyres and stops (decision 0014)"
)

PRACTICE_WEAR_SQL = """
SELECT count(*) AS practice_long_runs, median(deg_s_per_lap) AS practice_deg_s_per_lap
FROM mart_long_runs
WHERE season = ? AND round = ? AND compound IN ('SOFT', 'MEDIUM', 'HARD')
"""


class TooLate(Exception):
    """The session is about to start (or has started): a forecast now proves nothing."""


def check_deadline(now: datetime, target_start: datetime, margin_min: int = MARGIN_MIN) -> datetime:
    """The deadline is margin_min minutes before the target session starts. Return it, or raise
    TooLate if `now` is past it."""
    deadline = target_start - timedelta(minutes=margin_min)
    if now > deadline:
        raise TooLate(
            f"too late: the deadline was {deadline:%Y-%m-%d %H:%M} UTC "
            f"({margin_min} minutes before the session starts at {target_start:%H:%M} UTC)"
        )
    return deadline


def pace_forecast(history: pd.DataFrame, today: pd.DataFrame, checkpoint: str) -> pd.DataFrame:
    """today with predicted, low, high, the chances and every baseline's guess."""
    out = today.assign(predicted=shared_model(history, today), low=float("nan"))
    out["high"] = float("nan")
    for name, forecaster in BASELINES.items():
        out[f"baseline_{name}"] = forecaster(history, today)
    forecast_weekends = history.loc[history["season"] >= 2023, "weekend"].unique()
    recent = sorted(forecast_weekends)[-WINDOW:]
    past = walk_forward(history, {"shared_model": shared_model}, weekends=recent)
    past = past[past["checkpoint"] == checkpoint]
    errors = past_errors(past, int(today["weekend"].iloc[0]))
    if past.loc[errors.index, "weekend"].nunique() >= MIN_WEEKENDS:
        half = errors.abs().quantile(COVERAGE)
        out["low"], out["high"] = out["predicted"] - half, out["predicted"] + half
        out = out.join(simulate(out, errors.to_numpy()))
    return out


def tyre_decision(warehouse: Path, today: pd.DataFrame, race_laps: int | None) -> Decision | None:
    """The tyre and stop decision, from practice and earlier races. None at a new circuit when
    the race length isn't given (it can't be known from the data)."""
    table = strategy_table(warehouse)
    first = today.iloc[0]
    history = table[table["race_date"] < first["race_date"]]
    if race_laps is None:
        here = history.loc[history["circuit"] == first["circuit"], "race_laps"]
        if here.empty:
            return None
        race_laps = int(here.iloc[-1])  # the latest race here
    wear = query(warehouse, PRACTICE_WEAR_SQL, [int(first["season"]), int(first["round"])])
    row = pd.Series(
        {
            "season": first["season"],
            "round": first["round"],
            "circuit": first["circuit"],
            "race_date": first["race_date"],
            "race_laps": race_laps,
            "practice_long_runs": wear["practice_long_runs"].iloc[0],
            "practice_deg_s_per_lap": wear["practice_deg_s_per_lap"].iloc[0],
        }
    )
    d = decide_next(table, first_stops(warehouse), row)
    other = runner_up(d["plans"], d["stops"])
    a, b = sorted([d["stops"], other])
    stops = f"{d['stops']} stop" + ("" if d["stops"] == 1 else "s")
    return Decision(
        call=stops if d["clear"] else f"no clear decision: {a} or {b} stops",
        most_likely_stops=d["stops"],
        clear=d["clear"],
        p_best=round(d["p_best"], 4),
        tyre_wear_s_per_lap=round(d["deg"], 4),
        tyre_wear_low=None if pd.isna(d["deg_high"]) else round(d["deg_low"], 4),
        tyre_wear_high=None if pd.isna(d["deg_high"]) else round(d["deg_high"], 4),
        pit_loss_s=round(float(d["pit_loss_s"]), 2),
        useful_life_laps=round(d["useful_life"], 1),
        race_laps=race_laps,
        first_stop_window=d["window"],
        plans=[
            Plan(
                stops=int(p["stops"]),
                seconds_behind_best=round(float(p["seconds_behind_best"]), 2),
                low_s=round(float(p["low_s"]), 2),
                high_s=round(float(p["high_s"]), 2),
                p_best=round(float(p["p_best"]), 4),
            )
            for p in d["plans"].to_dict("records")
        ],
        reasons=reasons(row, history, d, other),
    )


def maybe(v) -> float | None:
    return None if pd.isna(v) else round(float(v), 4)


def make_forecast(
    warehouse: Path,
    season: int,
    round_no: int,
    checkpoint: str,
    adopted_team: str,
    race_laps: int | None = None,
    now: datetime | None = None,
    check_time: bool = True,
) -> Forecast:
    """The record `dpec freeze` writes. check_time=False only for dry runs."""
    now = now or datetime.now(UTC)
    sessions = weekend_sessions(warehouse, season, round_no)
    race_start = start_of(sessions, season, round_no, "after_quali")
    target = start_of(sessions, season, round_no, checkpoint)
    if check_time:
        deadline = check_deadline(now, target.to_pydatetime())
    else:
        deadline = target.to_pydatetime() - timedelta(minutes=MARGIN_MIN)
    today, seen = today_rows(warehouse, season, round_no, checkpoint, race_start)
    table = forecast_table(warehouse)
    history = table[table["race_date"] < today["race_date"].iloc[0]]
    pace = pace_forecast(history, today, checkpoint).sort_values("predicted")
    lineage = our_lineage(warehouse, adopted_team)

    drivers = [
        DriverForecast(
            driver_code=r["driver_code"],
            team=r["team"],
            ours=r["lineage"] == lineage,
            predicted_gap_pct=round(float(r["predicted"]), 4),
            low_pct=maybe(r["low"]),
            high_pct=maybe(r["high"]),
            p_best=maybe(r.get("p_best")),
            p_top3=maybe(r.get("p_top3")),
            p_beats_teammate=maybe(r.get("p_beats_teammate")),
            baselines={n: round(float(r[f"baseline_{n}"]), 4) for n in BASELINES},
        )
        for r in pace.to_dict("records")
    ]
    inputs = today.to_csv(index=False) + f"{len(history)} {history['race_date'].max()}"
    return Forecast(
        season=season,
        round=round_no,
        event_name=sessions["event_name"].iloc[0],
        circuit=sessions["circuit"].iloc[0],
        checkpoint=checkpoint,
        target_session=TARGETS[checkpoint][0],
        target_start_utc=target.to_pydatetime(),
        deadline_utc=deadline,
        frozen_at_utc=now,
        sessions_seen=seen,
        code_version=code_version(),
        inputs_sha256=hashlib.sha256(inputs.encode()).hexdigest(),
        method=METHOD,
        drivers=drivers,
        decision=tyre_decision(warehouse, today, race_laps),
    )


def describe(f: Forecast) -> str:
    """The frozen forecast in a few lines: the top 5, our cars, and the tyre decision."""
    when = f.deadline_utc.astimezone()  # this computer's own time zone
    lines = [
        (
            f"{f.season} round {f.round} · {f.circuit} · {f.checkpoint} "
            f"(from {', '.join(f.sessions_seen)})"
        ),
        f"Deadline: {when:%a %d %b %H:%M} your time ({f.deadline_utc:%H:%M} UTC)",
        "",
        "Race pace, % behind the fastest car:",
    ]
    for rank, d in enumerate(f.drivers, start=1):
        if rank > 5 and not d.ours:
            continue
        span = "" if d.low_pct is None else f"  80% range {d.low_pct:+.2f} to {d.high_pct:+.2f}"
        best = "" if d.p_best is None else f"  best pace {d.p_best:.0%}"
        lines.append(
            f"  {rank:>2}. {d.driver_code}{' ★' if d.ours else '  '} {d.predicted_gap_pct:+.2f}%"
            f"{span}{best}"
        )
    if f.decision:
        d = f.decision
        lines += [
            "",
            (
                f"Tyres and stops: {d.call} (best in {d.p_best:.0%} of replays), "
                f"first stop laps {d.first_stop_window[0]}-{d.first_stop_window[1]}, "
                f"tyre wear {d.tyre_wear_s_per_lap:.3f} s/lap"
            ),
            *[f"  - {r}" for r in d.reasons],
        ]
    else:
        lines += ["", "No tyre decision: new circuit. Give the race length with --race-laps."]
    return "\n".join(lines)
