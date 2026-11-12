# 0002 · Storage architecture: Parquet files + DuckDB

Date: 2026-10-11
Status: accepted
Updated: 2026-11-09 (sizes, the single writer, and what was not measured)
Builds on: nothing earlier (a starting decision)

## Decision
Store raw telemetry as partitioned Parquet files and use DuckDB as the local analytical database warehouse, avoiding any heavy traditional database server.

## Why
- Parquet format offers blazing-fast columnar read speeds and compression, making ingestion and notebook analysis instantaneous without hitting external APIs repeatedly.
- DuckDB provides a lightweight, serverless SQL analytical engine that embeds directly into our Python process, eliminating the operational overhead of running a separate database server.

## Update (9 November 2026): what the storage holds, and its limits
The decision is unchanged. This section records how the two parts are used now, with sizes
and the limits found since.

| Layer | Where | What it holds | Size |
|---|---|---|---|
| Download cache | data/cache/ | FastF1's own cache of the timing feed | 34 GB |
| Raw store | data/raw/fastf1/season=…/event=…/session=…/ | 7 Parquet files and a manifest.json (rows, columns and SHA-256 of each file) per session | 4.1 GB for 545 sessions |
| Warehouse | data/warehouse.duckdb | 15 tables: 6 core and dimension tables, 9 marts | about 28 MB |
| Saved predictions | data/forecasts/ | backtest.parquet and decisions.parquet | 377 KB and 17 KB |
| Public snapshot | dist/dpec-data-<date>.tar.gz | the warehouse, the forecast files, the ledger and the dry runs, with SHA256SUMS | 12.5 MB, 35 files (made on 9 November 2026) |

How the parts work together:
- `dpec build` is the only code that opens the warehouse for writing
  (src/telemetry_core/warehouse.py). It runs the SQL files in sql/core and sql/marts in name
  order. DuckDB reads the raw Parquet files directly and takes season, event and session from
  the folder names (`hive_partitioning = true`). Every build recreates every table.
- Everything else opens the warehouse read-only: the data checks, the API, the race
  engineer's tools and the telemetry alignment. `dpec check` runs 21 checks; all pass on the
  saved warehouse (9 November 2026).
- Reads are quick on the 28 MB file. Measured on 9 November 2026: most API addresses
  answered in 15 to 60 ms, and the right answers to 49 exam questions were computed in 4.7 s.
- No database server is needed, and data/ stays out of git. The public copy gets the
  snapshot, never the raw files (decision 0018).

Known limits:
- One writer at a time. DuckDB allows one writing process or several reading processes, not
  both, so while `dpec build` runs, requests to the local app fail until it ends (tested on
  9 November 2026: "Could not set lock on file").
- The raw files' SHA-256 values are written to each manifest but never checked again.
- The speed in the reasons above was not measured when this record was written: no build or
  notebook load time was recorded. The read times above were measured later.
- The 4.1 GB raw store is about an eighth of FastF1's 34 GB cache, but the two don't hold the
  same data, so that is not a measured compression ratio.

