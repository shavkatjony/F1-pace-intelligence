"""Public copy tests (step E1): the public settings match the local ones except the mode, the
snapshot holds what the image needs and its checksums catch a changed file."""

import tarfile
from datetime import date
from pathlib import Path

import duckdb
import yaml

from dpec.publish.snapshot import make_snapshot, verify
from telemetry_core.config import load_settings


def test_public_settings_only_change_the_mode():
    local = yaml.safe_load(Path("config/dpec.yaml").read_text())
    public = yaml.safe_load(Path("config/public.yaml").read_text())
    assert public.pop("mode") == "public"
    local.pop("mode")
    assert public == local


def test_snapshot_has_the_data_and_checksums_that_catch_a_change(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # the ledger/ folder is looked up from here
    warehouse = tmp_path / "data" / "warehouse.duckdb"
    (tmp_path / "data" / "forecasts").mkdir(parents=True)
    with duckdb.connect(str(warehouse)) as con:
        con.execute(
            "CREATE TABLE core_sessions AS SELECT 2026 AS season, 'Test Grand Prix' AS event_name, "
            "TIMESTAMP '2026-11-01 20:00' AS session_date_utc"
        )
    (tmp_path / "data" / "forecasts" / "backtest.parquet").write_bytes(b"PAR1")
    (tmp_path / "ledger" / "2026" / "19-test").mkdir(parents=True)
    (tmp_path / "ledger" / "2026" / "19-test" / "after_quali.json").write_text("{}")
    (tmp_path / "reports" / "dry-runs" / "2026" / "01-test").mkdir(parents=True)
    (tmp_path / "reports" / "dry-runs" / "2026" / "01-test" / "score.json").write_text("{}")
    s = load_settings(Path(__file__).parents[2] / "config" / "dpec.yaml")
    s = s.model_copy(
        update={
            "paths": s.paths.model_copy(update={"warehouse": warehouse, "data": tmp_path / "data"})
        }
    )

    out = make_snapshot(s, tmp_path / "dist", today=date(2026, 11, 2))
    assert out.name == "dpec-data-2026-11-02.tar.gz"
    with tarfile.open(out) as tar:
        names = set(tar.getnames())
        tar.extractall(tmp_path / "unpacked", filter="data")
    assert names == {
        "data/warehouse.duckdb",
        "data/forecasts/backtest.parquet",
        "ledger/2026/19-test/after_quali.json",
        "reports/dry-runs/2026/01-test/score.json",
        "SHA256SUMS",
        "manifest.json",
    }
    assert verify(tmp_path / "unpacked") == []
    (tmp_path / "unpacked" / "ledger" / "2026" / "19-test" / "after_quali.json").write_text("{ }")
    assert verify(tmp_path / "unpacked") == ["ledger/2026/19-test/after_quali.json"]
