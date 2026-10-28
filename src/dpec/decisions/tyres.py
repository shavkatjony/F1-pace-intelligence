"""Tyre wear and pit loss for one race, forecast from practice and earlier races (step C4).

Tyre wear = seconds a lap gets slower per lap of tyre age (fuel-corrected). Practice runs
alone overstate it (short runs on a green track), so a small regression learns, from earlier
races only, how practice wear and this circuit's past race wear turn into race wear.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from telemetry_core.warehouse import query

WEAR_FORMULA = "race_deg_s_per_lap ~ practice_deg_s_per_lap + circuit_deg"
MIN_RACES = 15  # fewer earlier races than that: too few to fit, use the circuit's history


def strategy_table(warehouse: Path) -> pd.DataFrame:
    """mart_race_strategy, dry races only, oldest first."""
    table = query(warehouse, "SELECT * FROM mart_race_strategy WHERE NOT is_wet_race")
    return table.sort_values("race_date", ignore_index=True)


def circuit_history(history: pd.DataFrame, column: str, circuit: str) -> float:
    """Median of `column` at this circuit in earlier races; all circuits if it's new."""
    here = history.loc[history["circuit"] == circuit, column].dropna()
    return (here if len(here) else history[column].dropna()).median()


def with_circuit_deg(rows: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    """Each row gets circuit_deg: race wear at its circuit in races before its own date."""
    out = rows.copy()
    out["circuit_deg"] = [
        circuit_history(
            history[history["race_date"] < row.race_date], "race_deg_s_per_lap", row.circuit
        )
        for row in rows.itertuples()
    ]
    return out


def wear_forecast(history: pd.DataFrame, today: pd.Series) -> float:
    """Race tyre wear for today's race, learned from earlier races only."""
    today_row = with_circuit_deg(today.to_frame().T, history).iloc[0]
    train = with_circuit_deg(history, history).dropna(
        subset=["race_deg_s_per_lap", "practice_deg_s_per_lap", "circuit_deg"]
    )
    if len(train) < MIN_RACES or pd.isna(today["practice_deg_s_per_lap"]):
        return float(today_row["circuit_deg"])  # no practice runs (or too little history)
    model = smf.ols(WEAR_FORMULA, train).fit()
    features = pd.DataFrame([today_row])[["practice_deg_s_per_lap", "circuit_deg"]].astype(float)
    return float(model.predict(features).iloc[0])


def useful_life(deg: float, pit_loss: float, race_laps: int) -> float:
    """Laps until a set has lost, in total, as much time as one pit stop costs.
    A lap at tyre age a is deg * a slower than new, so after L laps the loss adds up to
    deg * L * (L - 1) / 2. That equals pit_loss at L = (1 + sqrt(1 + 8 * pit_loss / deg)) / 2."""
    if deg <= 0:
        return float(race_laps)  # the tyre doesn't wear out: wear never pays for a stop
    return float(min(race_laps, (1 + np.sqrt(1 + 8 * pit_loss / deg)) / 2))
