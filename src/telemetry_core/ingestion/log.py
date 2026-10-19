"""The download log: one line per download attempt, only ever appended, never edited."""

import csv
from datetime import UTC, datetime
from pathlib import Path

FIELDS = ["time_utc", "source", "season", "round", "session", "status", "rows", "seconds", "error"]


def log_attempt(path: Path, **values) -> None:
    """Append one line. status is 'ok', 'failed' or 'rate_limited'."""
    row = {"time_utc": datetime.now(UTC).isoformat(timespec="seconds"), **values}
    unknown = set(row) - set(FIELDS)
    if unknown:
        raise ValueError(f"unknown log fields: {sorted(unknown)}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)

