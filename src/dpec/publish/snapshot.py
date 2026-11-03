"""The data snapshot for the public copy (step E1, decision 0018).

The public app needs the warehouse, the saved forecasts and the public record, but not the
4 GB of raw files. make_snapshot() puts those few files in one .tar.gz with a SHA256SUMS list,
so the image build (and anyone else) can check that nothing changed on the way. The file is
attached to a GitHub Release; the release workflow builds the Docker image from it.
"""

import hashlib
import io
import json
import tarfile
from datetime import UTC, date, datetime
from pathlib import Path

from dpec.record.ledger import LEDGER, code_version
from telemetry_core.config import Settings
from telemetry_core.warehouse import query


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def snapshot_files(s: Settings) -> dict[str, Path]:
    """Name inside the snapshot -> the file on this computer."""
    files = {"data/warehouse.duckdb": s.paths.warehouse}
    for path in sorted((s.paths.data / "forecasts").glob("*.parquet")):
        files[f"data/forecasts/{path.name}"] = path
    for path in sorted(LEDGER.rglob("*.json")):
        files[path.as_posix()] = path
    return files


def add_text(tar: tarfile.TarFile, name: str, text: str) -> None:
    data = text.encode()
    info = tarfile.TarInfo(name)
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))


def make_snapshot(s: Settings, out_dir: Path = Path("dist"), today: date | None = None) -> Path:
    files = snapshot_files(s)
    missing = [str(p) for p in files.values() if not p.exists()]
    if missing:
        raise FileNotFoundError(f"missing: {missing}. Run `make data` and `dpec backtest` first")
    latest = query(
        s.paths.warehouse,
        "SELECT arg_max(event_name, session_date_utc) AS event, max(season) AS season "
        "FROM core_sessions",
    ).iloc[0]
    manifest = {
        "made_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "code_version": code_version(),
        "data_up_to": f"{latest['event']} {latest['season']}",
        "files": {name: path.stat().st_size for name, path in files.items()},
    }
    sums = "".join(f"{sha256(path)}  {name}\n" for name, path in files.items())
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"dpec-data-{today or date.today()}.tar.gz"
    with tarfile.open(out, "w:gz") as tar:
        for name, path in files.items():
            tar.add(path, arcname=name)
        add_text(tar, "SHA256SUMS", sums)
        add_text(tar, "manifest.json", json.dumps(manifest, indent=2) + "\n")
    return out


def verify(folder: Path) -> list[str]:
    """Files in an unpacked snapshot whose checksum doesn't match SHA256SUMS (empty = all good).
    The same check as `sha256sum -c SHA256SUMS` (Linux) or `shasum -a 256 -c SHA256SUMS` (Mac)."""
    bad = []
    for line in (folder / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        path = folder / name
        if not path.exists() or sha256(path) != digest:
            bad.append(name)
    return bad
