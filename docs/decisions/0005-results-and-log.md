# 0005 · Official results, data inventory, download log

Date: 2026-10-__
Status: accepted

## Decision
- core_results comes from FastF1's results files, which already carry
  the official classification from Jolpica. No second adapter.
- core_files lists every saved table with its row count and fingerprint.
- dpec ingest appends one line per download attempt to data/ingest_log.csv.

## Why no Jolpica adapter
(the evidence: points filled in, DSQs present, your 8a and 8d results)

## When we would add one
(what check would tell us FastF1's results are not enough)

## Why score against the official result
(your Part 1 question 1, and one example from 8b)

## Known gaps
- 2023_09_FP1 pos_data is empty (FastF1 has none). Not used for pace.
