"""A weekend as it is before its target session: what a live forecast is made from.

targets.forecast_table starts from the race, so a weekend whose race hasn't run yet isn't in it.
Here the rows start from the drivers of the last session before the target, with the same
columns; what isn't known yet stays empty. The same code runs on a past weekend (a dry run):
it reads only that weekend's sessions before the target, so the race can't leak in.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from dpec.forecasting.targets import ANSWERS, hide_answers
from telemetry_core.ingestion import fastf1_source
from telemetry_core.warehouse import query

# checkpoint -> the session it must be frozen before (code in core_sessions, schedule name)
TARGETS = {"after_practice": ("Q", "Qualifying"), "after_quali": ("R", "Race")}

SESSIONS_SQL = """
SELECT session_type, session_date_utc, event_name, circuit, is_sprint_weekend
FROM core_sessions
WHERE season = ? AND round = ?
ORDER BY session_date_utc
"""

TODAY_SQL = """
WITH drivers AS (
    -- the drivers of the last session before the target: they are the ones who race
    SELECT driver_code, any_value(team) AS team
    FROM core_laps
    WHERE season = ? AND round = ? AND session_type = ?
    GROUP BY driver_code
),

long_runs AS (
    SELECT
        driver_code,
        median(gap_to_best_same_tyre_pct) AS long_run_gap_pct,
        median(gap_to_best_same_tyre_pct) FILTER (WHERE session_type = 'FP2')
            AS fp2_long_run_gap_pct
    FROM mart_long_runs
    WHERE season = ? AND round = ?
    GROUP BY driver_code
),

quali AS (
    SELECT p.driver_code, p.gap_to_best_pct AS quali_gap_pct, r.finish_position AS grid_position
    FROM mart_driver_session_pace AS p
    LEFT JOIN core_results AS r
        ON r.season = p.season AND r.round = p.round AND r.driver_code = p.driver_code
        AND r.session_type = 'Q'
    WHERE p.season = ? AND p.round = ? AND p.session_type = 'Q'
)

SELECT d.driver_code, d.team, coalesce(t.lineage, d.team) AS lineage,
    lr.long_run_gap_pct, lr.fp2_long_run_gap_pct, q.quali_gap_pct, q.grid_position
FROM drivers AS d
LEFT JOIN dim_teams AS t ON t.team_name = d.team
LEFT JOIN long_runs AS lr USING (driver_code)
LEFT JOIN quali AS q USING (driver_code)
ORDER BY d.driver_code
"""


def weekend_sessions(warehouse: Path, season: int, round_no: int) -> pd.DataFrame:
    """The sessions of one weekend saved so far, in time order."""
    sessions = query(warehouse, SESSIONS_SQL, [season, round_no])
    if sessions.empty:
        raise ValueError(
            f"no sessions saved for {season} round {round_no}: run "
            f"`uv run dpec ingest --season {season} --round {round_no}` and `uv run dpec build`"
        )
    return sessions


def start_of(sessions: pd.DataFrame, season: int, round_no: int, checkpoint: str) -> pd.Timestamp:
    """When the checkpoint's target session starts (UTC): from the warehouse if it's saved
    (a past weekend), otherwise from the official schedule."""
    code, name = TARGETS[checkpoint]
    saved = sessions.loc[sessions["session_type"] == code, "session_date_utc"]
    if len(saved):
        return pd.Timestamp(saved.iloc[0]).tz_localize("UTC")
    return fastf1_source.session_start(season, round_no, name)


def today_rows(
    warehouse: Path, season: int, round_no: int, checkpoint: str, race_start: pd.Timestamp
) -> tuple[pd.DataFrame, list[str]]:
    """This weekend's rows as a forecaster sees them at the checkpoint (the same columns as
    targets.forecast_table, hidden ones dropped), and the sessions they were made from."""
    sessions = weekend_sessions(warehouse, season, round_no)
    target = start_of(sessions, season, round_no, checkpoint).tz_localize(None)
    seen = sessions[sessions["session_date_utc"] < target]
    if seen.empty:
        raise ValueError(f"{season} round {round_no}: no session before the target is saved yet")
    if checkpoint == "after_quali" and "Q" not in seen["session_type"].to_list():
        raise ValueError(
            f"{season} round {round_no}: qualifying isn't saved yet. FastF1 has a session about "
            "3 hours after it starts; run `uv run dpec ingest` and `uv run dpec build` then"
        )
    last = seen["session_type"].iloc[-1]
    rows = query(warehouse, TODAY_SQL, [season, round_no, last] + [season, round_no] * 2)
    rows = rows.assign(
        season=season,
        round=round_no,
        weekend=season * 100 + round_no,
        race_date=pd.Timestamp(race_start.date()),
        circuit=sessions["circuit"].iloc[0],
        is_sprint_weekend=bool(sessions["is_sprint_weekend"].any()),
        **{column: np.nan for column in ANSWERS},  # not known before the race
    )
    return hide_answers(rows, checkpoint), seen["session_type"].to_list()
