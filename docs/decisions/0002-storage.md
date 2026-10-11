# 0002 · Storage architecture: Parquet files + DuckDB

Date: 2026-10-11
Status: accepted

## Decision
Store raw telemetry as partitioned Parquet files and use DuckDB as the local analytical database warehouse, avoiding any heavy traditional database server.

## Why
- Parquet format offers blazing-fast columnar read speeds and compression, making ingestion and notebook analysis instantaneous without hitting external APIs repeatedly.
- DuckDB provides a lightweight, serverless SQL analytical engine that embeds directly into our Python process, eliminating the operational overhead of running a separate database server.
