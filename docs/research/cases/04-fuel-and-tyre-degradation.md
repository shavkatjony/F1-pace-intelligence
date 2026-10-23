# Case 04 · Tyre wear when fuel loads are unknown

Decisions: [0008 · Tyre stints, long runs and the fuel effect](../../decisions/0008-stints-and-long-runs.md) (2026-10-22), [0014 · Tyre and stop decisions](../../decisions/0014-decision-packet.md) (2026-10-28) · Register: E08–E11

## 1. Research question
How much time does a tyre lose per lap of age, and can that be estimated from public timing data when the fuel load, which makes the car faster as it burns, is not published?

## 2. Initial hypothesis
The slope of lap time against tyre age within a stint measures wear. Fuel burn works in the opposite direction and would hide part of the wear, so it must be corrected, but the exact value might matter a lot.

## 3. Dataset and scope
- Race stints with at least 4 clean laps (`mart_stints`); wear medians use stints with 8+ clean laps.
- Practice long runs (`mart_long_runs`), 2022–2026.
- 78 dry races from 2023 for the race-wear forecast.

## 4. Method
- **Fuel correction:** a constant lap-time gain per lap of fuel burnt (`fuel_effect_s_per_lap`, default 0.06 s), added to every stint's slope. Sensitivity tested across 0.04–0.08.
- **Long-run definition:** at least `long_run_min_laps` (5) clean laps on one set, each within `long_run_band_pct` (2%) of the stint's median; compared only on the same compound; non-standard compound names become `UNKNOWN`.
- **Race-wear forecast:** a regression on earlier races only, `race_deg ~ practice_deg + circuit_deg`, where `circuit_deg` is this circuit's earlier race wear; 80% range from the last 20 errors.

## 5. Results
- The constant fuel term shifts every stint by the same amount, so the compound order (soft > medium > hard) and the gaps between compounds are unchanged for any value from 0.04 to 0.08. Absolute wear does change.
- Median race wear: **soft 0.085, medium 0.065, hard 0.057** s per lap of tyre age.
- Practice wear alone overstates race wear by about **1.6×**; with the circuit's history, the race-wear error is **0.028 s/lap** over 78 races, but only 73% of real values fall inside the 80% range.
- 8 of 85 FP2 sessions have no long run: rain (Japan 2022 and 2024, Canada 2024), red-flag interruptions (Miami 2022 and 2023, Japan 2025, Singapore 2025) and a Pirelli prototype-tyre test (Mexico 2024).
- Band choice: 2% leaves room for normal wear over a 10-lap run (about 1%) while excluding traffic and push laps; a minimum of 8 laps would lose about 60% of runs.

## 6. Interpretation
The fuel value is an assumption that cannot be validated with public data, but the analysis shows *where* it matters: not for comparing tyres or cars, only for absolute wear, and so for predicting the pit-stop lap. That made it acceptable to keep one documented constant rather than invent a per-team fuel model. Practice overstates wear because practice runs mix fuel, engine modes and programme choices; calibrating against each circuit's earlier races corrected most of it.

## 7. Decision influenced
- `fuel_effect_s_per_lap = 0.06` stays a setting labelled as an assumption ([`config/dpec.yaml`](../../../config/dpec.yaml)).
- The decision layer models **stops, not compounds**: compound pace gaps cannot be measured reliably without fuel and engine-mode data, and a precise-looking wrong compound model would be worse than none ([decision 0014](../../decisions/0014-decision-packet.md)).
- Race wear is forecast from practice *and* circuit history, never from practice alone ([`src/dpec/decisions/tyres.py`](../../../src/dpec/decisions/tyres.py)).

## 8. Known limitations
- **Assumed:** the fuel effect is one constant for all cars, circuits and seasons.
- Wear ranges are too narrow (73% inside instead of 80%).
- Fuel differences *between* teams' long runs are unknown, so long-run pace comparisons across teams carry that noise ([case 03](03-practice-vs-qualifying.md)).
- Tyre temperatures and pressures are not public.

## 9. Evidence and implementation
- SQL: [`sql/marts/05_mart_stints.sql`](../../../sql/marts/05_mart_stints.sql), [`06_mart_long_runs.sql`](../../../sql/marts/06_mart_long_runs.sql), [`09_mart_race_strategy.sql`](../../../sql/marts/09_mart_race_strategy.sql); checks 14, 15, 19, 20
- Code: [`src/dpec/decisions/tyres.py`](../../../src/dpec/decisions/tyres.py)
- Results: [`reports/backtest/decisions.csv`](../../../reports/backtest/decisions.csv)
- Tests: [`tests/telemetry_core/test_marts.py`](../../../tests/telemetry_core/test_marts.py), [`tests/dpec/test_decisions.py`](../../../tests/dpec/test_decisions.py)
- Narrative: [methods.md § 5](../../methods.md#5-analytics-the-tables-the-forecaster-stands-on), [§ 8](../../methods.md#8-from-a-forecast-to-a-decision)
- How it works now: [workstream 02 · Analytics and statistics](../../workstreams/02-data-analytics-statistics.md) · [workstream 03 · Forecasting and machine learning](../../workstreams/03-forecasting-machine-learning.md)

Previous: [Case 03](03-practice-vs-qualifying.md) · Next: [Case 05 · Track evolution](05-track-evolution.md)
