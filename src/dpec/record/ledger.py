"""The public record (step C5, decision 0015): forecasts frozen before the session, scored after.

    ledger/2026/19-mexico-city/after_quali.json   frozen before the race, never changed again
    ledger/2026/19-mexico-city/score.json         written after the race, never changed again

Every file carries the sha256 of its own content, so an edit shows. Git and CI add what a file
can't prove alone: that no file was changed or deleted after it was pushed, and that a new
forecast reached GitHub before its deadline (by GitHub's clock, not mine).
"""

import hashlib
import json
import re
import subprocess
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

LEDGER = Path("ledger")
MARGIN_MIN = 30  # a forecast must be frozen at least 30 minutes before its session starts
CHECKPOINTS = ("after_practice", "after_quali")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")  # an unknown field is an error, not ignored


class DriverForecast(Strict):
    driver_code: str
    team: str
    ours: bool
    predicted_gap_pct: float  # race pace, % behind the fastest car (decision 0011)
    low_pct: float | None  # 80% range (decision 0013); None in the first forecast weekends
    high_pct: float | None
    p_best: float | None
    p_top3: float | None
    p_beats_teammate: float | None
    baselines: dict[str, float]  # the simple guesses, frozen too, so the skill test is fair


class Plan(Strict):
    stops: int
    seconds_behind_best: float
    low_s: float
    high_s: float
    p_best: float


class Decision(Strict):
    call: str  # "1 stop", or "no clear decision: 1 or 2 stops"
    most_likely_stops: int
    clear: bool
    p_best: float
    tyre_wear_s_per_lap: float
    tyre_wear_low: float | None
    tyre_wear_high: float | None
    pit_loss_s: float
    useful_life_laps: float
    race_laps: int
    first_stop_window: tuple[int, int]
    plans: list[Plan]
    reasons: list[str]


class Forecast(Strict):
    kind: Literal["forecast"] = "forecast"
    season: int
    round: int
    event_name: str
    circuit: str
    checkpoint: Literal["after_practice", "after_quali"]
    target_session: Literal["Q", "R"]
    target_start_utc: datetime
    deadline_utc: datetime
    frozen_at_utc: datetime
    sessions_seen: list[str]
    code_version: str  # the git commit of the code that made it
    inputs_sha256: str  # the same inputs always give the same hash
    method: str
    drivers: list[DriverForecast]
    decision: Decision | None
    sha256: str = ""  # of everything above; filled in by write_once


class OurCar(Strict):
    driver_code: str
    predicted_gap_pct: float
    actual_gap_pct: float
    inside_range: bool | None


class CheckpointScore(Strict):
    checkpoint: Literal["after_practice", "after_quali"]
    forecast_sha256: str  # exactly which frozen file was scored
    drivers_scored: int
    mae_pct: float
    spearman: float
    inside_range: float | None  # share of real race paces inside their 80% range
    baselines_mae_pct: dict[str, float]
    skill_vs_team_form: float  # 1 - our error / team_form's error: above 0 = better
    our_cars: list[OurCar]


class DecisionScore(Strict):
    call: str
    actual_tyre_wear: float | None
    tyre_wear_error: float | None
    tyre_wear_inside_range: bool | None
    actual_top10_stops: int | None
    stops_right: bool | None
    green_first_stops: int
    inside_window: int


class Score(Strict):
    kind: Literal["score"] = "score"
    season: int
    round: int
    circuit: str
    scored_at_utc: datetime
    code_version: str
    checkpoints: list[CheckpointScore]
    decision: DecisionScore | None
    verdict: Literal["GOOD", "OK", "MISS"]
    sha256: str = ""


def content_hash(record: BaseModel) -> str:
    """sha256 of the record without its own sha256 field. Keys sorted and no spaces, so the
    same content always gives the same text, and so the same hash."""
    body = record.model_dump(mode="json", exclude={"sha256"})
    text = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slug(text: str) -> str:
    """'São Paulo' -> 'sao-paulo': plain letters for folder names."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")


def event_folder(root: Path, season: int, round_no: int, circuit: str) -> Path:
    return Path(root) / str(season) / f"{round_no:02d}-{slug(circuit)}"


def write_once(record: Forecast | Score, path: Path, overwrite: bool = False) -> Path:
    """Save a record with its hash. The ledger is write-once: an existing file is never
    replaced (overwrite=True is only for dry runs, which live outside ledger/)."""
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists: the ledger is write-once")
    record = record.model_copy(update={"sha256": content_hash(record)})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def read(path: Path) -> Forecast | Score:
    """One ledger file, checked against its model (a missing or unknown field is an error)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    model = Score if data.get("kind") == "score" else Forecast
    return model.model_validate(data)


def problems(root: Path = LEDGER) -> list[str]:
    """Every ledger file that doesn't read, or whose content doesn't match its own sha256."""
    found = []
    for path in sorted(Path(root).rglob("*.json")):
        try:
            record = read(path)
        except ValueError as error:  # bad JSON and failed validation are both ValueErrors
            found.append(f"{path}: not a valid ledger file ({str(error).splitlines()[0]})")
            continue
        if record.sha256 != content_hash(record):
            found.append(f"{path}: content changed after it was frozen (sha256 doesn't match)")
    return found


def git_changes(since: str, root: Path = LEDGER) -> list[tuple[str, str]]:
    """(status, path) for every ledger file added (A), changed (M), deleted (D) or renamed (R)
    between commit `since` and now."""
    out = subprocess.run(
        ["git", "diff", "--name-status", "--no-renames", since, "HEAD", "--", str(root)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [tuple(line.split("\t", 1)) for line in out.splitlines() if line]


def late(paths: list[Path], now: datetime) -> list[str]:
    """New forecast files that arrived after their deadline."""
    found = []
    for path in paths:
        record = read(path)
        if isinstance(record, Forecast) and now > record.deadline_utc:
            found.append(
                f"{path}: arrived {now:%Y-%m-%d %H:%M} UTC, after its deadline "
                f"{record.deadline_utc:%Y-%m-%d %H:%M} UTC"
            )
    return found


def code_version() -> str:
    """The git commit of the code, with '+changes' if src/, sql/ or config/ differ from it."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", "src", "sql", "config"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return commit + ("+changes" if dirty else "")