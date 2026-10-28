"""Score a frozen weekend after the race (step C5): the same measures as the backtest, on the
frozen files exactly as they were. A score is a new file: it never edits a forecast.
"""

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from dpec.decisions.replay import first_stops
from dpec.decisions.tyres import strategy_table
from dpec.forecasting.targets import TARGET, forecast_table
from dpec.record.ledger import (
    CheckpointScore,
    DecisionScore,
    Forecast,
    OurCar,
    Score,
    code_version,
    read,
)

# from the backtest's test years (reports/backtest/scores.csv, 2025-26)
GOOD_MAE = {"after_practice": 0.65, "after_quali": 0.55}  # the shared model's usual error
MISS_MAE = 1.05  # 'no signal' (everyone gets the average gap): a forecast must beat this


def verdict(checkpoint: str, mae_pct: float, inside_range: float | None) -> str:
    """GOOD: an error no bigger than the backtest's (GOOD_MAE) and, if there are ranges, at
    least 70% of real paces inside them. MISS: an error above MISS_MAE, or fewer than half
    inside. OK: anything in between."""
    if mae_pct > MISS_MAE or (inside_range is not None and inside_range < 0.5):
        return "MISS"
    if mae_pct <= GOOD_MAE[checkpoint] and (inside_range is None or inside_range >= 0.7):
        return "GOOD"
    return "OK"


def score_checkpoint(forecast: Forecast, actual: pd.Series) -> CheckpointScore:
    """actual = the real race pace gap per driver_code (drivers with a race pace only)."""
    f = pd.DataFrame([d.model_dump() for d in forecast.drivers]).set_index("driver_code")
    f = f.join(actual.rename("actual"), how="inner")
    if len(f) < 5:
        raise ValueError(f"only {len(f)} drivers have both a forecast and a race pace")
    f["error"] = (f["predicted_gap_pct"] - f["actual"]).abs()
    ranged = f.dropna(subset=["low_pct"])
    inside = f["actual"].between(f["low_pct"], f["high_pct"])
    baselines = pd.DataFrame(f["baselines"].to_list(), index=f.index)
    baselines_mae = (baselines.sub(f["actual"], axis=0)).abs().mean()
    return CheckpointScore(
        checkpoint=forecast.checkpoint,
        forecast_sha256=forecast.sha256,
        drivers_scored=len(f),
        mae_pct=round(f["error"].mean(), 4),
        spearman=round(f["predicted_gap_pct"].corr(f["actual"], method="spearman"), 4),
        inside_range=round(inside[ranged.index].mean(), 4) if len(ranged) else None,
        baselines_mae_pct={k: round(v, 4) for k, v in baselines_mae.items()},
        skill_vs_team_form=round(1 - f["error"].mean() / baselines_mae["team_form"], 4),
        our_cars=[
            OurCar(
                driver_code=code,
                predicted_gap_pct=r["predicted_gap_pct"],
                actual_gap_pct=round(r["actual"], 4),
                inside_range=None if pd.isna(r["low_pct"]) else bool(inside[code]),
            )
            for code, r in f[f["ours"]].iterrows()
        ],
    )


def score_decision(forecast: Forecast, race: pd.Series, stops: pd.DataFrame) -> DecisionScore:
    """race = the race's row of the strategy table; stops = its top-10 first stops."""
    d = forecast.decision
    wear = None if pd.isna(race["race_deg_s_per_lap"]) else float(race["race_deg_s_per_lap"])
    top10 = None if pd.isna(race["top10_stops"]) else int(race["top10_stops"])
    same_plan = stops[stops["green"] & (stops["stops"] == d.most_likely_stops)]
    first, last = d.first_stop_window
    ranged = wear is not None and d.tyre_wear_low is not None
    return DecisionScore(
        call=d.call,
        actual_tyre_wear=wear,
        tyre_wear_error=None if wear is None else round(wear - d.tyre_wear_s_per_lap, 4),
        tyre_wear_inside_range=(
            bool(d.tyre_wear_low <= wear <= d.tyre_wear_high) if ranged else None
        ),
        actual_top10_stops=top10,
        stops_right=None if top10 is None else top10 == d.most_likely_stops,
        green_first_stops=len(same_plan),
        inside_window=int(same_plan["first_stop_lap"].between(first, last).sum()),
    )


def score_weekend(warehouse: Path, folder: Path, now: datetime | None = None) -> Score:
    """Score every frozen checkpoint in one event folder of the ledger."""
    forecasts = [read(p) for p in sorted(Path(folder).glob("after_*.json"))]
    if not forecasts:
        raise ValueError(f"no frozen forecast in {folder}")
    first = forecasts[0]
    table = forecast_table(warehouse)
    race = table[(table["season"] == first.season) & (table["round"] == first.round)]
    if race.empty:
        raise ValueError(
            f"no race pace for {first.season} round {first.round} yet: after the race run "
            "`uv run dpec ingest` and `uv run dpec build`. Wet races are not scored (decision 0011)"
        )
    actual = race.set_index("driver_code")[TARGET]
    checkpoints = [score_checkpoint(f, actual) for f in forecasts]

    decision = None
    latest = forecasts[-1]  # after_quali if it was frozen: it knew the most
    if latest.decision is not None:
        strategy = strategy_table(warehouse)
        row = strategy[(strategy["season"] == first.season) & (strategy["round"] == first.round)]
        stops = first_stops(warehouse)
        here = stops[(stops["season"] == first.season) & (stops["round"] == first.round)]
        if len(row):
            decision = score_decision(latest, row.iloc[0], here)

    last = checkpoints[-1]
    return Score(
        season=first.season,
        round=first.round,
        circuit=first.circuit,
        scored_at_utc=now or datetime.now(UTC),
        code_version=code_version(),
        checkpoints=checkpoints,
        decision=decision,
        verdict=verdict(last.checkpoint, last.mae_pct, last.inside_range),
    )


def summary(score: Score) -> pd.DataFrame:
    """One row per scored checkpoint, for printing."""
    rows = []
    for c in score.checkpoints:
        rows.append(
            {
                "checkpoint": c.checkpoint,
                "drivers": c.drivers_scored,
                "error_pct": c.mae_pct,
                "team_form_error_pct": c.baselines_mae_pct["team_form"],
                "skill": c.skill_vs_team_form,
                "spearman": c.spearman,
                "inside_range": np.nan if c.inside_range is None else c.inside_range,
            }
        )
    return pd.DataFrame(rows)
