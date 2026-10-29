"""Addresses for the public record (step C5): the frozen forecasts and scores in ledger/, and
the dry runs in reports/dry-runs/ (made after the fact, so never shown as the record).
Read-only like the rest: it only reads the JSON files.
"""

from pathlib import Path
from typing import Literal

from fastapi import APIRouter

from dpec.record.ledger import LEDGER, Forecast, Score, content_hash, read

router = APIRouter()
SOURCES = {"ledger": LEDGER, "dry-runs": Path("reports/dry-runs")}


def weekend_row(folder: Path) -> dict:
    """One frozen weekend: its forecasts (latest checkpoint last), the call and the score."""
    records = [read(p) for p in sorted(folder.glob("*.json"))]
    forecasts = [r for r in records if isinstance(r, Forecast)]
    scores = [r for r in records if isinstance(r, Score)]
    if not forecasts:
        return {}
    latest = forecasts[-1]
    row = {
        "season": latest.season,
        "round": latest.round,
        "circuit": latest.circuit,
        "intact": all(r.sha256 == content_hash(r) for r in records),
        "frozen": [
            {
                "checkpoint": f.checkpoint,
                "frozen_at_utc": f.frozen_at_utc.isoformat(),
                "deadline_utc": f.deadline_utc.isoformat(),
                "minutes_early": round((f.deadline_utc - f.frozen_at_utc).total_seconds() / 60),
                "sha256": f.sha256,
            }
            for f in forecasts
        ],
        "ours": [
            {"driver_code": d.driver_code, "predicted": d.predicted_gap_pct}
            for d in latest.drivers
            if d.ours
        ],
        "call": latest.decision.call if latest.decision else None,
        "verdict": None,
    }
    if scores:
        s, last = scores[0], scores[0].checkpoints[-1]
        row.update(
            verdict=s.verdict,
            error_pct=last.mae_pct,
            skill=last.skill_vs_team_form,
            inside_range=last.inside_range,
            stops_right=s.decision.stops_right if s.decision else None,
            our_actual={c.driver_code: c.actual_gap_pct for c in last.our_cars},
        )
    return row


@router.get("/record")
def record(source: Literal["ledger", "dry-runs"] = "ledger") -> list[dict]:
    """Every frozen weekend, newest first. source=dry-runs: the dry runs instead."""
    folders = sorted(SOURCES[source].glob("*/*"), reverse=True)
    return [row for row in map(weekend_row, folders) if row]
