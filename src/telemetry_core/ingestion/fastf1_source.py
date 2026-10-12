from pathlib import Path

import fastf1
import pandas as pd
from fastf1.exceptions import RateLimitExceededError

# Re-exported so the rest of the project never imports fastf1 itself.
RateLimitError = RateLimitExceededError


def enable_cache(cache_dir: Path) -> None:
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_dir))


def season_rounds(season: int) -> list[int]:
    """Round numbers of a season's race weekends (pre-season testing left out)."""
    schedule = fastf1.get_event_schedule(season, include_testing=False)
    return [int(r) for r in schedule["RoundNumber"]]


def session_names(season: int, round_no: int) -> tuple[str, list[str]]:
    """Event name and the sessions that have already happened, from the official schedule.

    A session counts as happened 3 hours after its start, so a future race is never requested.
    """
    event = fastf1.get_event(season, round_no)
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=3)
    names = []
    for i in range(1, 6):
        name, start = event[f"Session{i}"], event[f"Session{i}DateUtc"]
        if not (isinstance(name, str) and name) or pd.isna(start):
            continue
        start = pd.Timestamp(start)
        if start.tzinfo is None:
            start = start.tz_localize("UTC")
        if start < cutoff:
            names.append(name)
    return event["EventName"], names


def _per_driver(data: dict) -> pd.DataFrame:
    """car_data and pos_data come as {car number: table}. Stack them into one table."""
    parts = [pd.DataFrame(df).assign(DriverNumber=str(num)) for num, df in data.items()]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def fetch_session(season: int, round_no: int, session_name: str) -> tuple[dict, dict]:
    """Load one session and return (tables, info). Tables are untouched FastF1 data."""
    session = fastf1.get_session(season, round_no, session_name)
    session.load(laps=True, telemetry=True, weather=True, messages=True)
    tables = {
        "laps": pd.DataFrame(session.laps),
        "results": pd.DataFrame(session.results),
        "car_data": _per_driver(session.car_data),
        "pos_data": _per_driver(session.pos_data),
        "weather": pd.DataFrame(session.weather_data),
        "race_control": pd.DataFrame(session.race_control_messages),
        "track_status": pd.DataFrame(session.track_status),
    }
    info = {
        "source": "fastf1",
        "fastf1_version": fastf1.__version__,
        "season": season,
        "round": round_no,
        "event": session.event["EventName"],
        "session": session.name,
        "session_date_utc": str(session.date),
        "session_info": session.session_info,
    }
    return tables, info