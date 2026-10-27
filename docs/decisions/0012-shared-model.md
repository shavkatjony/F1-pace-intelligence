# 0012 · One shared model for every track and year

Date: 2026-10-24
Status: accepted

## Decision
- After practice: race gap ~ team_form + driver_vs_team. After quali: + quali_gap_pct.
- team_form: the team's race gaps, exponentially weighted, half-life 3 races, shifted so a
  race never sees itself; a new team gets the average of all earlier races.
  driver_vs_team: the driver's gap minus his team's average, half-life 6 races; rookies 0.
- Weighted least squares, refitted before every weekend on all earlier races; weights halve
  every 12 races (about half a season).

## Evidence
- Test years 2025–26 (37 weekends): after practice 0.648% (0.58 s) vs team form 0.674%;
  after quali 0.548% (0.49 s) vs the per-year line 0.589%. Best at both checkpoints.
- Not best everywhere: the per-year line orders drivers better after quali (rho 0.843 vs
  0.821), team form after practice (0.776 vs 0.767).
- 2026 rules change: simple guesses win the first 5 races; from race 6 the shared model beats them.

## Rejected
- One model per track: 3 to 4 races per circuit in history.
- Circuit offset (mixed model): worse at both checkpoints (0.569 vs 0.553; 0.535 vs 0.513).
- Rules-era switch: worst of all in 2026 races 1–5 (1.034 after practice): too few rows.
- Bayesian version (the plan's "mixed effects → Bayesian"): not built; its first step, the mixed
  model, made things worse.
- Half-life 6, 24, 48 or none: within 0.003% on the tune years; 12 kept.

## What would change it
A next rules change: then compare the per-year line and the shared model race by race for
the first 5 races, and say which one the packet should trust.
