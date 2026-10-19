# 0003 · Clean tables and lap rules

Date: 2026-10-17
Status: accepted

## Decision
Two core tables built by `dpec build` from plain SQL files run in DuckDB:
- core_sessions: one row per session (FP1, FP2, FP3, SQ, S, Q, R) of every saved weekend.
  Key: session_key, e.g. 2024_01_R.
- core_laps: one row per driver per lap per session.
  Key: session_key + driver_code + lap_number.
Every lap gets one reason code; only `clean` laps are used for pace.

## Lap rules
A lap gets the first reason that is true, in this order:
no_time, generated, in_lap, out_lap, lap_one, red_flag, safety_car, vsc,
yellow, deleted, inaccurate, wet_tyre, slow.
One reason per lap keeps the counts adding up to the total. Example: an in-lap
under the safety car is `in_lap`; either way it isn't race pace.
Every rule also stays as its own yes/no column, so later steps can be stricter or looser.

## Choices I made
- slow_lap_pct = 107. In races, 395 laps are slower than 107% of the session's
  clean median, but 3,445 at 103%. A 103% limit would drop laps on old tyres,
  which is exactly what the tyre model must learn. In practice the limit barely
  matters: cool-down laps are far slower than any limit.
- Wet laps are not clean: the forecaster predicts dry pace. Japan 2022 and
  São Paulo 2024 come out with 0 clean laps, which is right.
- lap_one only for races and sprints: only they have a standing start with the
  whole field in traffic. In practice and qualifying, lap 1 is an out-lap from
  the pits and `out_lap` already catches it.

## Result (2026-10-17)
545 sessions, 297,724 laps, 163,599 clean (55%). Races 78% clean, qualifying 27%.
Grain check: no duplicates.

## Why SQL files and not dbt (yet)
Two tables don't need a framework. The files use dbt's {{ }} style,
so they can move to dbt in step B1 when there are many more tables.
