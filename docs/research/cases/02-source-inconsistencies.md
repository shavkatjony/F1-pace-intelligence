# Case 02 · Inconsistencies in the official timing feed

Decisions: [0005 · Results, inventory, log](../../decisions/0005-results-and-log.md) (2026-10-19), [0006 · Checks and ID maps](../../decisions/0006-checks-and-id-maps.md) (2026-10-21), [0007 · Marts](../../decisions/0007-marts.md) (updated 2026-10-27) · Register: E03, E04, E05

## 1. Research question
Can the official timing feed, as delivered by FastF1, be joined and aggregated across five seasons without silent errors? Where it cannot, what is the smallest correct repair?

## 2. Initial hypothesis
The feed is official, so identifiers, team names and results should be consistent. A second source (Jolpica) might be needed for official results.

## 3. Dataset and scope
All 545 sessions: `results`, `laps` and `weather` tables; 2,212 race result rows and 552 sprint result rows; 54,295 weather readings.

## 4. Method
Every assumption about the data was written as a SQL query that **returns the rows breaking it**, so an empty result is a pass and a failure shows exactly which rows are wrong ([decision 0006](../../decisions/0006-checks-and-id-maps.md)). The checks run on every rebuild (`dpec check`). Each failure was traced to its source rows and either repaired with a stated rule or recorded as a known gap.

## 5. Results

| Problem found | Scale | Repair |
|---|---|---|
| Sprint-qualifying results have no driver IDs (also 6 qualifying no-shows) | every sprint-qualifying session | A driver code is unique within a season, so the ID is borrowed from the same driver's other sessions that season (`dim_drivers`) |
| Team name empty | 2026 rounds 5 and 7, FP1 | Same driver, same weekend first; else same driver and car number that season (FP1 stand-ins) |
| Teams renamed across years | 15 names | A hand-written lineage map: 11 lineages ([`seeds/teams.csv`](../../../seeds/teams.csv)); for example Alfa Romeo, Kick Sauber and Audi are one lineage, while Racing Bulls stays separate from Red Bull Racing |
| Track temperature exactly 0 °C | 47 of 54,295 readings, 14 sessions | A dry track at 0 °C is impossible: treated as missing, guarded by check 18 |
| Official results | 101 or 102 points per race, 36 per sprint; disqualifications after the flag present (Spa 2024, Las Vegas 2025) | None needed: FastF1 already merges Jolpica's classification, so no second adapter was built |
| Position data missing | 2023 round 9 FP1 `pos_data` | Recorded in [`seeds/known_gaps.csv`](../../../seeds/known_gaps.csv); not used for pace |

## 6. Interpretation
"Official" did not mean "consistent". The defects were small in volume but would have produced believable wrong answers: a team's form split across three names, sprint-qualifying pace attributed to nobody, or average track temperatures pulled down by impossible zeros. Checks that return rows made each defect visible at the moment it appeared, rather than after a model behaved strangely.

## 7. Decision influenced
- Twenty checks in [`sql/checks/`](../../../sql/checks/), plus a check that the data dictionary documents every column.
- `dim_drivers` and `dim_teams` as the only way to resolve identity; team form in the forecaster follows the lineage, not the name ([`sql/core/05_dim_drivers.sql`](../../../sql/core/05_dim_drivers.sql), [`06_dim_teams.sql`](../../../sql/core/06_dim_teams.sql)).
- Forecasts are scored against the official classification, not the on-track order (Spa 2024: the first car across the line was disqualified).
- A Jolpica adapter will be added only if a check finds a race without results or with points that do not add up.

## 8. Known limitations
- Lineage choices are judgements (for example, Audi continuing Sauber's lineage) and are documented in decision 0006.
- The 0 °C rule cannot be recounted from the warehouse, because the zeros are removed at build time. It needs the raw files ([numbers-check, last section](../../../reports/numbers-check.md#not-recomputed-here-they-need-the-raw-files-on-the-mac)).
- Checks find violations of known rules only; an unknown kind of defect needs a new check.

## 9. Evidence and implementation
- Checks: [`sql/checks/`](../../../sql/checks/) (05, 06, 08, 09, 11, 13, 18 for this case)
- Repairs: [`sql/core/02_core_laps.sql`](../../../sql/core/02_core_laps.sql) (team filling), [`sql/core/05_dim_drivers.sql`](../../../sql/core/05_dim_drivers.sql), [`sql/core/06_dim_teams.sql`](../../../sql/core/06_dim_teams.sql), [`sql/marts/02_mart_session_weather.sql`](../../../sql/marts/02_mart_session_weather.sql)
- Runner: [`warehouse.run_checks()`](../../../src/telemetry_core/warehouse.py)
- Tests: [`tests/telemetry_core/test_warehouse.py`](../../../tests/telemetry_core/test_warehouse.py), [`test_marts.py`](../../../tests/telemetry_core/test_marts.py)
- Narrative: [methods.md § 4](../../methods.md#4-messy-data-and-what-i-did-about-it)
- How it works now: [workstream 01 · Data engineering](../../workstreams/01-data-engineering.md)

Previous: [Case 01](01-lap-eligibility.md) · Next: [Case 03 · Practice or qualifying?](03-practice-vs-qualifying.md)
