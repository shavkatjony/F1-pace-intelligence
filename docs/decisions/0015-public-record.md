# 0015 · The public record: frozen before the race, scored after

Date: 2026-10-29
Status: accepted; paused since 5 November 2026 (see the update at the end)
Updated: 2026-11-05 (no live weekends: F1's timing data now needs a login)
Builds on: [0011](0011-target-and-fair-test.md) target and fair test, [0012](0012-shared-model.md) shared model, [0013](0013-ranges-and-chances.md) ranges and chances, [0014](0014-decision-packet.md) decision packet

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
Dry runs of the 2026 season (rounds 1-17, replayed afterwards with the live code; round 16
was wet, so it isn't scored): 16 races, 322 drivers. Error 0.573%, exactly the backtest's
0.573% (largest difference 0.0000%), so the live path is the tested path. 81% of real paces
inside the 80% ranges. Better than team_form on 14 of 16 weekends. Verdicts: 11 GOOD, 4 OK,
1 MISS (Catalunya). Stop call right on 9 of the 15 races with a tyre call (the new Madring
circuit had none). These are dry runs, not live forecasts: they show the pipeline works.

## Known limits
- Wet races have no race pace: their frozen files stay in the record, unscored.
- A new circuit (Madring 2026) has no earlier race, so no race length: pass the official
  length with --race-laps, or there is no tyre decision.
- A changed race length (Montreal 2026: 68 laps, 70 before): the live path uses the last
  race's length. The decision packet's replay (decision 0014) used the real one, a small
  leak; the live path is the honest one. Pass the official length with --race-laps when it
  changed.
- FastF1 has a session about 3 hours after it starts, so the freeze window is from
  qualifying + 3 h to race - 30 min.
- One person runs it: a missed weekend is a gap in the record, not a hidden result.

## Update (5 November 2026): no live weekends
- Since October 2026, Formula 1's timing service needs a login. FastF1 3.9 and later ask for
  a paid F1TV Access subscription, and 3.8 gets no data at all. So no forecast could be
  frozen before a race.
- The project stops at the races already saved: 545 sessions, up to the Singapore Grand Prix
  (11 October 2026). No forecast was frozen, so ledger/ has none in it: 0 live weekends.
- What the record shows instead: the 2026 dry runs above, always labelled as replayed
  afterwards, and the backtest (decision 0011). Neither is called a live record.
- To restart: an F1TV Access subscription, or OpenF1 as a new source. `dpec freeze`,
  `dpec score` and the CI checks are unchanged and ready.
