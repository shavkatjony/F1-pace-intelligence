# 0013 · Ranges and chances from the model's own past errors

Date: 2026-10-24
Status: accepted

## Decision
- 80% range = guess ± the 80th percentile of the size of the model's errors over the last
  10 forecast weekends (same checkpoint). Split-conformal, walk-forward: nothing from the
  weekend itself or later. No range until 5 weekends have passed.
- Chances = 4,000 replays of the race order, each driver's guess plus a past error drawn at
  random; seed 0, so a forecast is repeatable.

## Evidence
- Test years 2025–26: 78.5% inside after practice, 79.9% after qualifying (goal 75–85%).
- Window, on the tune years only: 10 weekends is closest to 80% at both checkpoints
  (0.800 / 0.810) and nearly the narrowest. Longer windows forget a rules change more slowly:
  2026 races 1–5 after practice, 68% inside with 10, 61% with all weekends.
- Top-3 chances: Brier 0.077 after qualifying against 0.132 with no information.

## Known limits
- The first ~5 races of a new rules era: ranges too narrow (68% inside).
- Chances a bit too flat (favourites under-rated); errors are drawn one driver at a time.

## What would change it
A next rules change: widen the ranges by hand for its first races, or draw a whole
weekend's errors together if that fixes the flat chances.
