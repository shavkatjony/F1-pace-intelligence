# 0015 · The public record: frozen before the race, scored after

Date: 2026-11-01
Status: accepted

## Decision
- After qualifying (and before the race) I freeze every car's race pace forecast with its
  80% range and chances, the five baselines' guesses, and the tyre and stop decision, into
  ledger/<season>/<round>-<circuit>/after_quali.json. An after-practice forecast
  (before qualifying) is optional.
- Deadline: 30 minutes before the target session starts. `dpec freeze` refuses later.
- The file is pushed to GitHub at once. The time that counts is GitHub's: a CI job
  (`dpec ledger --late-check`) fails if a new forecast reached GitHub after its deadline.
- Write-once: each file carries the sha256 of its content; the CI job also fails if any
  ledger file is changed or deleted after it was pushed. A score is a new file (score.json).
- Dry runs (past weekends, made after the fact) go to reports/dry-runs/, never ledger/,
  and the app labels them "made after the fact".

## Why
A backtest is run after the races by the person who built the model, so a reader can't
rule out tuning on the test races. A forecast that reached GitHub before the race can't
have been tuned on it, and the git history shows any change made later.

## How it's scored
Error (MAE, % of a lap), Spearman, the share of real race paces inside the 80% ranges, each
baseline's error on the same drivers, skill = 1 - error / team_form's error. Tyre decision:
wear error and range, stops against the top 10, first stops inside the window.
Verdict: MISS if error > 1.05% (no better than "no signal") or under half inside the ranges;
GOOD if error <= 0.55% after quali (0.65% after practice) and at least 70% inside; else OK.

## Evidence
Pretend season (2026 rounds 1-17, the live code run as dry runs): 16 dry races, 322
drivers. Error 0.573%, exactly the backtest's 0.573% (largest difference 0.0000%), so the
live path is the tested path. 81% of real paces inside the 80% ranges. Better than
team_form on 14 of 16 weekends. Verdicts: 11 GOOD, 4 OK, 1 MISS (Catalunya).
Stop call right on 9 of 15 races with a decision.

## Known limits
- Wet races have no race pace: their frozen files stay in the record, unscored.
- A new circuit (Madring 2026) has no earlier race, so no race length: pass the official
  length with --race-laps, or there is no tyre decision.
- A changed race length (Montreal 2026: 68 laps, 70 before): the live path uses the last
  race's length. Lesson 16's replay used the real one, a small leak; the live path is the
  honest one. Pass the official length with --race-laps when it changed.
- FastF1 has a session about 3 hours after it starts, so the freeze window is from
  qualifying + 3 h to race - 30 min.
- One person runs it: a missed weekend is a gap in the record, not a hidden result.
