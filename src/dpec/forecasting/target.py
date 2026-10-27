"""What the forecaster predicts, and the one table every forecaster learns from.

Target (decision 0011): race_pace_gap_pct = a driver's median clean race lap, as % behind the
best median of that race (0 = the fastest car on Sunday). Dry races only, and only drivers
with 10+ clean race laps (that's how mart_weekend_signals is built).
"""

from pathlib import Path

import pandas as pd

from telemetry_core.warehouse import query

TARGET = "race_pace_gap_pct"
ANSWERS = ["race_pace_gap_pct", "race_clean_laps", "finish_position", "points"]  # after the race
QUALI = ["quali_gap_pct", "grid_position"]  # known once qualifying is over

# what is still hidden at each checkpoint of the weekend
CHECKPOINTS = {
    "after_practice": ANSWERS + QUALI,
    "after_quali": ANSWERS,
}

TABLE_SQL = """
SELECT s.season, s.round, w.race_date, w.circuit, s.driver_code, s.team,
    coalesce(t.lineage, s.team) AS lineage, s.is_sprint_weekend,
    s.long_run_gap_pct, s.fp2_long_run_gap_pct, s.quali_gap_pct, s.grid_position,
    s.race_pace_gap_pct, s.race_clean_laps, s.finish_position, s.points
FROM mart_weekend_signals AS s
JOIN mart_weekends AS w USING (season, round)
LEFT JOIN dim_teams AS t ON t.team_name = s.team
WHERE NOT s.is_wet_race
ORDER BY w.race_date, s.driver_code
"""


def forecast_table(warehouse: Path) -> pd.DataFrame:
    """One row per driver per dry race weekend, oldest weekend first.
    lineage = the team across name changes (AlphaTauri, RB and Racing Bulls are one team)."""
    table = query(warehouse, TABLE_SQL)
    table["weekend"] = table["season"] * 100 + table["round"]
    return table


def hide_answers(today: pd.DataFrame, checkpoint: str) -> pd.DataFrame:
    """This weekend as a forecaster sees it at the checkpoint: the hidden columns are gone."""
    return today.drop(columns=CHECKPOINTS[checkpoint])