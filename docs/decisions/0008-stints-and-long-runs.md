# 0008 · Tyre stints, long runs and the fuel effect

Date: 2026-10-18
Status: accepted

## Decision
- mart_stints: one row per tyre set per driver per session. deg = slope of clean lap
  time vs tyre age, plus the fuel effect. Needs 4+ clean laps.
- mart_long_runs: practice stints on slicks with at least long_run_min_laps clean laps
  within long_run_band_pct % of the stint's median. Compared only on the same compound.
- Tyre names other than the five real compounds become UNKNOWN.

## The fuel effect
fuel_effect_s_per_lap = 0.06, an assumption (fuel loads are not public).
It adds the same constant to every stint, so the compound order (SOFT > MEDIUM > HARD)
and the gaps between compounds don't change for any value from 0.04 to 0.08. It does change
absolute deg, so it matters for predicting the pit-stop lap, not for comparing tyres or cars.

## The long-run rule
Band 2%: room for normal wear over a 10-lap run (~1%), but cuts traffic and push laps.
Min 5 laps: longer than a qualifying run plus cool-down, but short programmes keep their runs (8 loses ~60%).

## What the data showed
- Race deg per lap (median, 8+ clean laps): SOFT 0.085, MEDIUM 0.065, HARD 0.057.
- 8 of 85 FP2 sessions have no long run, for three reasons: rain (Japan 2022 and 2024,
  Canada 2024), interrupted sessions with red flags (Miami 2022 and 2023, Japan 2025,
  Singapore 2025), and a Pirelli prototype-tyre test (Mexico 2024, almost all TEST_UNKNOWN).
