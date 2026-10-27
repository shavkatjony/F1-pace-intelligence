"""Addresses for Phase B's tables. Each one runs one small read-only SQL query.

A path like /weekends/2024/1/pace?session=Q reads: weekend 2024 round 1, the pace table,
for qualifying. FastAPI checks the types: a round that isn't a number, or a session that
isn't one of SESSIONS, gets a 422 error before any SQL runs.
"""

import json
from typing import Literal

import duckdb
from fastapi import APIRouter, HTTPException, Request

from telemetry_core.alignment.compare import compare_laps, corner_table
from telemetry_core.warehouse import query

router = APIRouter()
Session = Literal["FP1", "FP2", "FP3", "SQ", "S", "Q", "R"]


def rows(request: Request, sql: str, params: list | None = None) -> list[dict]:
    """Run one read-only query; return its rows as JSON-ready dicts (NaN becomes null)."""
    table = query(request.app.state.settings.paths.warehouse, sql, params)
    return json.loads(table.to_json(orient="records", date_format="iso"))


def session_key(season: int, round_no: int, session: str) -> str:
    return f"{season}_{round_no:02d}_{session}"  # the same key core_sessions uses


@router.get("/health")
def health(request: Request) -> dict:
    """Is the warehouse there, and how much is in it?"""
    s = request.app.state.settings
    found = rows(request, "SELECT count(*) AS sessions, max(season) AS latest FROM core_sessions")
    return {"status": "ok", "team": s.team_name, "mode": s.mode, **found[0]}


@router.get("/settings")
def settings(request: Request) -> dict:
    """The few settings the app shows: our team and the real team whose cars are 'ours'."""
    s = request.app.state.settings
    lineage = rows(
        request,
        "SELECT any_value(lineage) AS lineage FROM dim_teams WHERE lower(team_name) = lower(?)",
        [s.adopted_team],
    )
    return {
        "team_name": s.team_name,
        "adopted_team": s.adopted_team,
        "adopted_lineage": lineage[0]["lineage"],
        "fuel_effect_s_per_lap": s.fuel_effect_s_per_lap,
        "mode": s.mode,
    }


@router.get("/weekends")
def weekends(request: Request, season: int | None = None) -> list[dict]:
    """Every weekend in the warehouse, newest first. ?season=2024 for one season."""
    return rows(
        request,
        """
        SELECT season, round, event_name, circuit, race_date, is_sprint_weekend,
            pole, winner, winner_team, is_wet_race
        FROM mart_weekends
        WHERE ? IS NULL OR season = ?
        ORDER BY season DESC, round DESC
        """,
        [season, season],
    )


@router.get("/weekends/{season}/{round_no}")
def weekend(request: Request, season: int, round_no: int) -> dict:
    """One weekend: its overview row and its sessions in time order."""
    found = rows(
        request, "SELECT * FROM mart_weekends WHERE season = ? AND round = ?", [season, round_no]
    )
    if not found:
        raise HTTPException(404, f"no weekend {season} round {round_no} in the warehouse")
    sessions = rows(
        request,
        """
        SELECT s.session_key, s.session_type, s.session_name, s.session_date_utc,
            count(l.lap_number) AS laps,
            count(l.lap_number) FILTER (WHERE l.is_clean) AS clean_laps
        FROM core_sessions AS s
        LEFT JOIN core_laps AS l USING (session_key)
        WHERE s.season = ? AND s.round = ?
        GROUP BY ALL
        ORDER BY s.session_date_utc, s.session_key  -- a tie needs a tie-breaker, or the order is random
        """,
        [season, round_no],
    )
    return {**found[0], "sessions": sessions}


@router.get("/weekends/{season}/{round_no}/pace")
def pace(request: Request, season: int, round_no: int, session: Session = "Q") -> list[dict]:
    """Each driver's best and median clean lap in one session, fastest first."""
    return rows(
        request,
        """
        WITH laps AS (
            SELECT driver_code, count(*) AS laps,
                arg_min(compound, lap_time_s) FILTER (WHERE is_clean) AS best_compound
            FROM core_laps
            WHERE session_key = ?
            GROUP BY driver_code
        )
        SELECT p.pace_rank, p.driver_code, p.team, t.lineage, p.best_lap_s, p.median_lap_s,
            p.best_lap_s - min(p.best_lap_s) OVER () AS gap_s, p.gap_to_best_pct,
            l.best_compound, p.clean_laps, l.laps
        FROM mart_driver_session_pace AS p
        LEFT JOIN laps AS l USING (driver_code)
        LEFT JOIN dim_teams AS t ON t.team_name = p.team
        WHERE p.session_key = ?
        ORDER BY p.pace_rank, p.driver_code
        """,
        [session_key(season, round_no, session)] * 2,
    )


@router.get("/weekends/{season}/{round_no}/laps")
def laps(
    request: Request, season: int, round_no: int, driver: str, session: Session = "R"
) -> list[dict]:
    """Every lap of one driver in one session. in_long_run = one of the laps that make a
    practice long run (clean, and within long_run_band_pct of the stint's median)."""
    band = request.app.state.settings.long_run_band_pct
    return rows(
        request,
        """
        SELECT l.lap_number, l.stint, l.compound, l.tyre_age_laps, l.lap_time_s, l.position,
            l.lap_reason, l.is_clean, l.is_in_lap, l.is_out_lap,
            coalesce(r.stint IS NOT NULL AND l.is_clean
                AND abs(l.lap_time_s / s.median_clean_s - 1) * 100 <= ?, false) AS in_long_run
        FROM core_laps AS l
        LEFT JOIN mart_long_runs AS r USING (session_key, driver_code, stint)
        LEFT JOIN mart_stints AS s USING (session_key, driver_code, stint)
        WHERE l.session_key = ? AND l.driver_code = upper(?)
        ORDER BY l.lap_number
        """,
        [band, session_key(season, round_no, session), driver],
    )


@router.get("/weekends/{season}/{round_no}/long-runs")
def long_runs(request: Request, season: int, round_no: int, session: Session = "FP2") -> list[dict]:
    """Practice long runs of one session (mart_long_runs), quickest first per compound."""
    return rows(
        request,
        """
        SELECT driver_code, team, stint, compound, tyre_age_start, run_laps, run_median_s,
            run_median_fuel_adj_s, deg_s_per_lap, gap_to_best_same_tyre_pct
        FROM mart_long_runs
        WHERE session_key = ?
        ORDER BY compound, run_median_s
        """,
        [session_key(season, round_no, session)],
    )


@router.get("/weekends/{season}/{round_no}/stints")
def stints(request: Request, season: int, round_no: int, session: Session = "R") -> list[dict]:
    """Tyre stints of one session, drivers in finishing order (mart_stints + core_results)."""
    return rows(
        request,
        """
        SELECT s.driver_code, s.team, t.lineage, r.finish_position, s.stint, s.compound,
            s.first_lap, s.last_lap, s.n_laps, s.tyre_age_start, s.fresh_at_start,
            s.median_clean_s, s.deg_s_per_lap
        FROM mart_stints AS s
        LEFT JOIN core_results AS r USING (session_key, driver_code)
        LEFT JOIN dim_teams AS t ON t.team_name = s.team
        WHERE s.session_key = ?
        ORDER BY r.finish_position NULLS LAST, s.driver_code, s.stint
        """,
        [session_key(season, round_no, session)],
    )


@router.get("/weekends/{season}/{round_no}/weather")
def weather(request: Request, season: int, round_no: int) -> list[dict]:
    """Weather and track evolution of every session of the weekend, in time order."""
    return rows(
        request,
        """
        SELECT s.session_type, s.session_date_utc, w.air_temp_c, w.track_temp_min_c,
            w.track_temp_c, w.track_temp_max_c, w.humidity_pct, w.wind_speed_ms,
            w.rain_share, w.had_rain, e.evo_s_per_10min, e.is_reliable AS evo_is_reliable
        FROM core_sessions AS s
        LEFT JOIN mart_session_weather AS w USING (session_key)
        LEFT JOIN mart_track_evolution AS e USING (session_key)
        WHERE s.season = ? AND s.round = ?
        ORDER BY s.session_date_utc
        """,
        [season, round_no],
    )


@router.get("/weekends/{season}/{round_no}/quality")
def quality(request: Request, season: int, round_no: int) -> dict:
    """Why laps are not clean, per session, and which saved tables are empty."""
    reasons = rows(
        request,
        """
        SELECT session_type, lap_reason, count(*) AS laps
        FROM core_laps
        WHERE season = ? AND round = ?
        GROUP BY ALL
        ORDER BY session_type, laps DESC
        """,
        [season, round_no],
    )
    files = rows(
        request,
        """
        SELECT s.session_type, f.table_name, f.n_rows, f.is_empty
        FROM core_files AS f
        JOIN core_sessions AS s USING (session_key)
        WHERE s.season = ? AND s.round = ?
        ORDER BY s.session_date_utc, f.table_name
        """,
        [season, round_no],
    )
    return {"lap_reasons": reasons, "files": files}


@router.get("/weekends/{season}/{round_no}/results")
def results(request: Request, season: int, round_no: int, session: Session = "R") -> list[dict]:
    """The official classification of one session (core_results), winner first."""
    return rows(
        request,
        """
        SELECT r.finish_position, r.driver_code, r.driver_name, r.team, t.lineage,
            r.grid_position, r.status, r.points, r.laps_completed
        FROM core_results AS r
        LEFT JOIN dim_teams AS t ON t.team_name = r.team
        WHERE r.session_key = ?
        ORDER BY r.finish_position NULLS LAST, r.driver_code
        """,
        [session_key(season, round_no, session)],
    )


@router.get("/standings/{season}/{round_no}")
def standings(request: Request, season: int, round_no: int) -> dict:
    """Drivers' and teams' championship after this round."""
    drivers = rows(
        request,
        """
        SELECT s.championship_position, s.driver_code, s.team, t.lineage, s.total_points,
            s.total_wins, s.round_points
        FROM mart_standings AS s
        LEFT JOIN dim_teams AS t ON t.team_name = s.team
        WHERE s.season = ? AND s.round = ?
        ORDER BY s.championship_position, s.driver_code
        """,
        [season, round_no],
    )
    teams = rows(
        request,
        """
        SELECT s.team, any_value(t.lineage) AS lineage, sum(s.round_points) AS total_points
        FROM mart_standings AS s
        LEFT JOIN dim_teams AS t ON t.team_name = s.team
        WHERE s.season = ? AND s.round <= ?
        GROUP BY s.team
        ORDER BY total_points DESC
        """,
        [season, round_no],
    )
    return {"drivers": drivers, "teams": teams}


@router.get("/weekends/{season}/{round_no}/compare")
def compare(
    request: Request,
    season: int,
    round_no: int,
    a: str,
    b: str,
    session: Session = "Q",
    lap_a: int | None = None,
    lap_b: int | None = None,
    step_m: float = 10,
) -> dict:
    """Driver A's lap against driver B's on one distance grid. Default: each one's fastest
    clean lap of the session. a_behind_s > 0 = A is behind B at that point of the lap."""
    s = request.app.state.settings
    key = session_key(season, round_no, session)
    lap_a = lap_a or fastest_clean_lap(request, key, a)
    lap_b = lap_b or fastest_clean_lap(request, key, b)
    try:
        both, info_a, info_b = compare_laps(
            s.paths.warehouse, s.paths.raw, step_m, (key, a, lap_a), (key, b, lap_b)
        )
    except (ValueError, duckdb.IOException) as error:
        raise HTTPException(404, f"no telemetry: {error}") from None
    return {
        "session_key": key,
        "a": lap_facts(a, lap_a, info_a),
        "b": lap_facts(b, lap_b, info_b),
        "distance_m": both["distance_m"].round(1).tolist(),
        "speed_a": both["speed_kph_ref"].round(1).tolist(),
        "speed_b": both["speed_kph_other"].round(1).tolist(),
        "throttle_a": both["throttle_pct_ref"].round().tolist(),
        "throttle_b": both["throttle_pct_other"].round().tolist(),
        "brake_a": both["brake_ref"].astype(int).tolist(),
        "brake_b": both["brake_other"].astype(int).tolist(),
        "gear_a": both["gear_ref"].astype(int).tolist(),
        "gear_b": both["gear_other"].astype(int).tolist(),
        "a_behind_s": (both["time_s_ref"] - both["time_s_other"]).round(3).tolist(),
        "x": both["x"].round().tolist(),
        "y": both["y"].round().tolist(),
        "corners": json.loads(corner_table(both).round(3).to_json(orient="records")),
    }


def fastest_clean_lap(request: Request, key: str, driver: str) -> int:
    found = rows(
        request,
        """
        SELECT lap_number FROM core_laps
        WHERE session_key = ? AND driver_code = upper(?) AND is_clean
        ORDER BY lap_time_s LIMIT 1
        """,
        [key, driver],
    )
    if not found:
        raise HTTPException(404, f"{driver.upper()} has no clean lap in {key}")
    return found[0]["lap_number"]


def lap_facts(driver: str, lap: int, info: dict) -> dict:
    return {
        "driver": driver.upper(),
        "lap": lap,
        "lap_time_s": info["lap_time_s"],
        "lap_reason": info["lap_reason"],
    }
