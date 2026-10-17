# 0003 · Clean tables and lap rules

Date: 2026-10-__
Status: accepted

## Decision
Two core tables built by `dpec build` from plain SQL files run in DuckDB:
- core_sessions: one row per ...
- core_laps: one row per ...
Every lap gets one reason code; only `clean` laps are used for pace.

## Lap rules
(the order from Part 1, and your answer to Part 1 question 2)

## Choices I made
- slow_lap_pct = ___ because ... (your numbers from 9c)
- Wet laps are not clean because ... (what you saw in 9d)
- lap_one only for races and sprints because ... (Part 1 question 1)

## Why SQL files and not dbt (yet)
Two tables don't need a framework. The files use dbt's {{ }} style,
so they can move to dbt in step B1 when there are many more tables.
