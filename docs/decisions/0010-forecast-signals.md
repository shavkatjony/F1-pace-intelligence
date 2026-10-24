# 0010 · Which signals the forecaster starts with

Date: 2026-10-22
Status: accepted

## Decision
Qualifying pace is the main signal. FP2 long runs are a second input and a sanity check;
FP1 long runs are not used.

## Evidence
reports/b3-practice-vs-race.md: median Spearman quali 0.80 vs long runs 0.39 (86 weekends);
bootstrap 95% CI of the difference -0.48 to -0.34; leave-one-weekend-out error 0.597% (quali)
vs 0.586% (quali + long runs).

## What would change it
If the Phase C backtest shows FP2 long runs cut the race-pace error by more than 5% on top of
qualifying, give them a bigger role.
