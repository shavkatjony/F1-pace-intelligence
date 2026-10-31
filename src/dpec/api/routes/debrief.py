"""Addresses for Phase D's debrief (step D1): where driver A's time went against driver B.
Computed when asked, from core_laps and the saved telemetry. Read-only like the rest.
"""

import json

import duckdb
from fastapi import APIRouter, HTTPException, Request

from dpec.api.routes.analytics import Session, fastest_clean_lap, session_key
from dpec.debrief.attribution import attribute, paired_laps
from dpec.debrief.segments import lap_gap

router = APIRouter()


@router.get("/weekends/{season}/{round_no}/debrief")
def debrief(
    request: Request, season: int, round_no: int, a: str, b: str, session: Session = "Q"
) -> dict:
    """A's best lap of the session against B's, split by part of the track (+ = A loses), and
    A's race gap to B split into pace, tyres and traffic, with 80% ranges. A part that can't
    be measured comes back as a note instead of an error, so the window shows what it can."""
    s = request.app.state.settings
    a, b = a.upper(), b.upper()
    out: dict = {"a": a, "b": b, "session": session, "lap": None, "race": None}
    key = session_key(season, round_no, session)
    try:
        lap_a, lap_b = fastest_clean_lap(request, key, a), fastest_clean_lap(request, key, b)
        split, official, _ = lap_gap(s.paths.warehouse, s.paths.raw, key, (b, lap_b), (a, lap_a))
        out["lap"] = {
            "gap_s": round(official, 3),
            "parts": json.loads(split.round(4).to_json(orient="records")),
        }
    except HTTPException as problem:
        out["lap_note"] = problem.detail
    except (ValueError, duckdb.IOException):
        out["lap_note"] = f"no telemetry saved for {key}"
    laps = paired_laps(s.paths.warehouse, session_key(season, round_no, "R"), a, b)
    try:
        parts = attribute(laps)
        out["race"] = {
            "laps": len(laps),
            "gap_s": round(float(laps["gap_s"].mean()), 3),
            "a_traffic_share": round(float(laps["a_in_traffic"].mean()), 3),
            "parts": json.loads(parts.round(4).to_json(orient="records")),
        }
    except ValueError as problem:
        out["race_note"] = str(problem)
    return out

