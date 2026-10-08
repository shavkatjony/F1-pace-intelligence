# 06 · Analytics Layer (all the basics)

> **Short version:** Everything the F1 Pit Wall repo showed is included here: overview, driver comparison, telemetry, track map, corners, tyres, track evolution, strategy, weather and data quality. But it's built as **clean data marts that feed the forecaster**, not as a pile of separate tabs. AI builds most of it fast. You build the marts the forecaster depends on.

---

## Overview steps

1. List the questions (below). Each question maps to one mart.
2. AI builds the "context" marts (overview, results, standings, calendar, weather).
3. AI builds the comparison marts on top of the aligned grid (file 05).
4. **You** build the long-run pace, tyre stint and track-evolution marts. The forecaster uses these.
5. Add a dbt test to every mart (keys, ranges, row counts).
6. Expose each mart through the API (file 11 windows read them).

---

## The question list → marts

| # | Question a DPEC engineer asks | Mart || Feeds forecaster? |
|---|---|---|---|---|
| 1 | What happened in this session? (results, gaps, fastest laps) | `mart_session_overview` | context |
| 2 | Championship, calendar, next session time | `mart_standings`, `mart_calendar` | context |
| 3 | Where is driver A faster than B on the lap? | `mart_lap_delta` (grid-based delta) | no |
| 4 | Speed, throttle, brake, gear traces, overlaid | `mart_telemetry_overlay` | no |
| 5 | Track map coloured by speed / delta | `mart_track_map` | no |
| 6 | Corner by corner: entry, minimum, exit, braking point | `mart_corner_summary` | yes (car-profile features) |
| 7 | Speed traps and straight-line speed | `mart_straightline` | yes (car-profile features) |
| 8 | Practice long runs: pace per stint, cleaned | `mart_long_runs` | **yes, main input** |
| 9 | Tyre degradation per stint, fuel-corrected | `mart_tyre_stints` | **yes** |
| 10 | How is the track getting faster through the weekend? | `mart_track_evolution` | **yes** |
| 11 | Weather through the session | `mart_weather` | yes (conditions) |
| 12 | What strategies were actually used? (stints, pit laps, compounds) | `mart_strategy_history` | yes (race simulation inputs) |
| 13 | How good is this session's data? | `mart_data_quality` | yes (weights) |
| 14 | Teammate comparison across a weekend | `mart_teammate` | debrief (file 09) |

---

## Detailed side: the three marts you own

### `mart_long_runs`
- Detect long runs in practice: ≥ N consecutive clean laps on one tyre set, in the same pace band.
- Output per run: driver, compound, tyre age at start, laps, median pace, slope, track temp, quality score.
- Why it's yours: deciding what counts as a "race-sim run" versus a "quali push" or "programme lap" is a judgement call, and the forecaster depends on it.

### `mart_tyre_stints`
- Per stint: lap times fuel-corrected with the fuel model estimate (file 07), the degradation slope with uncertainty, and the cliff signal (where the slope suddenly rises).
- Labelled `estimated`, because fuel correction is a model (rule 2).

### `mart_track_evolution`
- Rubbering-in effect: how much the whole field speeds up over the weekend and through each session, after adjusting for tyres and fuel.
- Used to move practice pace to "Sunday conditions".

---

## What's deliberately different from the benchmark repo

- One set of marts, many windows (file 11). No 11 disconnected tabs.
- Every mart sits on **aligned** data and **flagged** laps, so the basics are actually correct.
- Insight text isn't if/else templates. Explanations come from the debrief (file 09) and the AI layer (file 10), with numbers attached.

---



## Exit test

Each of the 14 questions is answered by one query against its mart; dbt tests pass; the three marts you own have short written definitions in `docs/`.
