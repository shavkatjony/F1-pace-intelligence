# Case 01 · When does a lap count as race pace?

Decision: [0003 · Clean tables and lap rules](../../decisions/0003-clean-laps.md) (2026-10-18) · Register: E01, E02

## 1. Research question
Which of the 297,724 recorded laps represent a car's real pace, and how can that be decided the same way for every session from 2022 to 2026?

## 2. Initial hypothesis
Most laps are not representative (out-laps, in-laps, laps behind the safety car, wet laps). A single "is this lap clean?" flag would be enough.

## 3. Dataset and scope
All 545 saved sessions (practice, sprint qualifying, sprint, qualifying, race), FastF1 `laps` tables with pit times, track status, deletion flags, accuracy flags and tyre compound.

## 4. Method
- Wrote one rule per reason a lap is not representative: `no_time`, `generated`, `in_lap`, `out_lap`, `lap_one`, `red_flag`, `safety_car`, `vsc`, `yellow`, `deleted`, `inaccurate`, `wet_tyre`, `slow`.
- Each lap receives **one** reason: `clean`, or the first rule it breaks in that fixed order. Each rule is also kept as its own yes/no column.
- Compared slow-lap limits by counting how many race laps each would remove.
- Checked three messy races by hand: Australia 2023 (three red flags), Spain 2025 (19 starters), Las Vegas 2025 (two disqualifications).

## 5. Results
- 163,599 laps clean (55%): races 78%, qualifying 27% (most qualifying laps are out-laps and cool-down laps).
- Slow-lap limit: 107% of the session's clean median removes 395 race laps; 103% would remove 3,445, mostly laps on old tyres.
- Japan 2022 and São Paulo 2024 come out with 0 clean race laps through the wet-tyre rule, with no separate rain flag needed.
- Australia 2023: 49 laps ran under red flag, but 48 have no lap time, so the first matching rule labels them `no_time`, not `red_flag`. The order decides the label; the counts still add up.

## 6. Interpretation
A single flag hides *why* a lap was excluded, and overlapping reasons make counts impossible to reconcile. A fixed order gives every lap exactly one label, so the reason counts always sum to the total, while the separate yes/no columns let a later model be stricter or looser. A tight slow-lap limit would have removed exactly the worn-tyre laps the tyre model needs to learn from.

## 7. Decision influenced
- `core_laps` carries `lap_reason` plus one boolean per rule ([`sql/core/02_core_laps.sql`](../../../sql/core/02_core_laps.sql)).
- `slow_lap_pct = 107` lives in [`config/dpec.yaml`](../../../config/dpec.yaml), not in SQL.
- `lap_one` applies only to races and sprints (standing starts); in practice and qualifying lap 1 is already an out-lap.
- Wet laps are never clean: the forecaster predicts dry pace ([decision 0011](../../decisions/0011-target-and-fair-test.md)).
- Check 04 fails if any lap has a reason outside the known list.

## 8. Known limitations
- The order is a judgement: a lap that is both a yellow-flag lap and a deleted lap is counted as `yellow`.
- `slow` is relative to each session's median, so a session in which most laps are slow (a drying track) can keep laps that are not truly representative.
- FastF1's `IsAccurate` flag is used as given.

## 9. Evidence and implementation
- SQL: [`sql/core/02_core_laps.sql`](../../../sql/core/02_core_laps.sql), [`sql/checks/04_lap_reasons_known.sql`](../../../sql/checks/04_lap_reasons_known.sql)
- Tests: [`tests/telemetry_core/test_warehouse.py`](../../../tests/telemetry_core/test_warehouse.py)
- Numbers: [numbers-check § Messy data](../../../reports/numbers-check.md#messy-data)
- Columns: [data dictionary § core_laps](../../data-dictionary.md#core_laps)
- Narrative: [methods.md § 4](../../methods.md#4-messy-data-and-what-i-did-about-it)
- How it works now: [workstream 02 · Analytics and statistics](../../workstreams/02-data-analytics-statistics.md) · [workstream 01 · Data engineering](../../workstreams/01-data-engineering.md)

Next: [Case 02 · Inconsistencies in the official timing feed](02-source-inconsistencies.md)
