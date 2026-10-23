# Case 05 · Measuring track evolution

Decision: [0009 · Track evolution](../../decisions/0009-track-evolution.md) (2026-10-22) · Register: E12

## 1. Research question
How much faster does the track become during a session as rubber is laid down, and how can that be measured without confusing it with who happens to drive late?

## 2. Initial hypothesis
The slope of lap time against time-in-session measures track evolution directly.

## 3. Dataset and scope
Practice and qualifying sessions, 2022–2026; push laps only (within `push_lap_band_pct`, 1.5%, of the driver's best on that tyre). Races are excluded because fuel burn and tyre wear dominate their lap times.

## 4. Method
- `evo_s_per_10min` = slope of push-lap time against time in session, estimated **within each driver and compound** ([fixed effects](https://en.wikipedia.org/wiki/Fixed_effects_model)), so differences between cars, drivers and tyres drop out.
- A reliability rule, added after the first version failed its check: no rain at any point, fewer than 10% of laps on wet tyres, and at least 10 drivers with push laps.
- Check 16: reliable sessions must fall within ±1 s per 10 minutes.

## 5. Results
- The first version **failed** check 16 on 12 sessions: almost all had rain or a drying track, and a few had only one or two drivers with push laps (a slope from two laps is meaningless).
- After the rule: the track got faster in **87 of 87** reliable qualifying sessions, median **−0.15 s per 10 minutes**.
- Sprint qualifying evolves about twice as fast (**−0.33 s per 10 min**): only one practice session precedes it, so the track is greener.
- FP2 is the noisiest session (13 of 74 sessions show the track getting *slower*), because high-fuel long runs mix fuel and tyre wear into lap times.

## 6. Interpretation
A naive slope would be biased by run order: fast drivers often go out late, which looks like a faster track. Estimating within driver and compound removes that. The failed check was useful: it showed that the method breaks under changing weather, and that sessions should be **flagged rather than deleted**, so every session stays visible with a reason.

## 7. Decision influenced
- `mart_track_evolution` keeps every session with an `is_reliable` flag ([`sql/marts/07_mart_track_evolution.sql`](../../../sql/marts/07_mart_track_evolution.sql)).
- Runs from different times in a session should be corrected by evolution × minutes between them before comparison.
- The app's weather window shows evolution next to weather for each session.

## 8. Known limitations
- The `is_reliable` rule itself is not unit-tested (noted in decision 0009).
- A linear slope per session ignores non-linear effects (for example a sudden rubber gain after a red flag).
- FP2 estimates are contaminated by fuel and tyre programmes.

## 9. Evidence and implementation
- SQL: [`sql/marts/07_mart_track_evolution.sql`](../../../sql/marts/07_mart_track_evolution.sql), [`sql/checks/16_track_evolution_believable.sql`](../../../sql/checks/16_track_evolution_believable.sql)
- Tests: [`tests/telemetry_core/test_marts.py`](../../../tests/telemetry_core/test_marts.py) (the fixed-effects estimate ignores who is faster)
- Columns: [data dictionary § mart_track_evolution](../../data-dictionary.md#mart_track_evolution)
- Narrative: [methods.md § 5](../../methods.md#5-analytics-the-tables-the-forecaster-stands-on)
- How it works now: [workstream 02 · Analytics and statistics](../../workstreams/02-data-analytics-statistics.md)

Previous: [Case 04](04-fuel-and-tyre-degradation.md) · Next: [Case 06 · Shared versus separate models](06-shared-vs-separate-models.md)
