import re
from pathlib import Path


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def session_folder(
    raw_root: Path,
    source: str,
    season: int,
    round_no: int,
    event_name: str,
    session_name: str,
) -> Path:
    return (
        Path(raw_root)
        / source
        / f"season={season}"
        / f"event={round_no:02d}_{slug(event_name)}"
        / f"session={slug(session_name)}"
    )

