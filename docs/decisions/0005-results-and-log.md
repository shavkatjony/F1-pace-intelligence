# 0005 · Official results, data inventory, download log

Date: 2026-10-19
Status: accepted

## Decision
- core_results comes from FastF1's results files, which already carry
  the official classification from Jolpica. No second adapter.
- core_files lists every saved table with its row count and fingerprint.
- dpec ingest appends one line per download attempt to data/ingest_log.csv.

## Why no Jolpica adapter
FastF1 merges Jolpica's classification into results.parquet. In my data:
points are filled in for all 2,212 race rows and 552 sprint rows, every race
hands out 101 or 102 points and every sprint 36, and disqualifications decided
after the flag are there (Russell, Spa 2024; Norris and Piastri, Las Vegas 2025).
A second adapter would download the same numbers again.

## When we would add one
When a check finds a race or sprint with no results, or points that don't add
up. Then a small Jolpica adapter fills exactly those sessions.

## Why score against the official result
The on-track order isn't the result: time penalties and disqualifications come
later. Spa 2024: Russell crossed the line first and was disqualified for an
underweight car, so Hamilton won. A forecaster scored on the on-track order
would be scored against a result that doesn't exist.

## Known gaps
- 2023_09_FP1 pos_data is empty (FastF1 has none). Not used for pace.
