# 0011 · What the forecaster predicts, and how it's tested

Date: 2026-10-24
Status: accepted

## Decision
- Target: race_pace_gap_pct, a driver's median clean race lap as % behind the best median
  of that race. Dry races, drivers with 10+ clean laps.
- Checkpoints: after_practice (long runs only) and after_quali (plus quali gap and grid).
  The hidden columns are listed in targets.CHECKPOINTS; a forecaster can't read them.
- Test: walk-forward by race date. History = races strictly before this one. 2022 only
  teaches; every dry race from 2023 is forecast and scored (78 weekends, 1,501 rows).
- Scores: mean absolute error in % and in seconds on a 90 s lap; median per-weekend Spearman.
- Baselines: no signal (the floor), last race, team form, the best signal as it is, and a
  straight line per season (one model per year, as a baseline for the shared model).

## Evidence
reports/backtest/scores.csv: to beat after practice, team form 0.584% (0.53 s);
after quali, the per-year line 0.579% (0.52 s), rho 0.808.

## Rejected
- Random row split: rows of the same race leak in. Copying the teammate's race pace from the
  same race scores 0.51%, better than every honest guess, and is useless on a real Saturday.
- Wet races: a different sport for pace (tyres, spray, safety cars); flagged, not forecast.