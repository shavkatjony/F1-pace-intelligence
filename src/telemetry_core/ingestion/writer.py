import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

MANIFEST = "manifest.json"


def parquet_safe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """- timedelta columns become float seconds (the names stay the same)
    - text columns with mixed types become plain strings (missing stays missing)
    Returns the new table and the list of columns that were converted to seconds.
    """
    out = df.copy()
    seconds_cols = []
    for col in out.columns:
        if pd.api.types.is_timedelta64_dtype(out[col]):
            out[col] = out[col].dt.total_seconds()
            seconds_cols.append(col)
        elif out[col].dtype == object:
            out[col] = out[col].map(_as_text)
    return out, seconds_cols


def _as_text(value) -> str | None:
    """One cell as text; missing values stay missing."""
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return str(value)


def file_hash(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def is_saved(folder: Path) -> bool:
    return (Path(folder) / MANIFEST).exists()


def write_session(tables: dict[str, pd.DataFrame], info: dict, folder: Path) -> dict:
    """Write every table to folder/<name>.parquet and a manifest.json. Returns the manifest."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, df in tables.items():
        safe, seconds_cols = parquet_safe(df)
        path = folder / f"{name}.parquet"
        safe.to_parquet(path, index=False)
        files[name] = {
            "rows": len(safe),
            "columns": len(safe.columns),
            "seconds_columns": seconds_cols,
            "sha256": file_hash(path),
        }
    manifest = {
        "saved_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "info": info,
        "files": files,
    }
    (folder / MANIFEST).write_text(json.dumps(manifest, indent=2, default=str))
    return manifest
