# 0009 · Track evolution

Date: 2026-10-18
Status: accepted

## Decision
mart_track_evolution: one row per practice and qualifying session. evo_s_per_10min = slope
of push-lap time vs time in the session, measured within each driver + compound
("fixed effects"), so car, driver and tyre drop out. Races are left out.

## Flag, don't delete
The first version failed its check on 12 sessions: almost all had rain or a drying track,
and a few had only 1-2 drivers with push laps (a slope from 2 laps is meaningless).
Rule: reliable = no rain at any point, fewer than 10% of laps on wet tyres, and at least
10 drivers. Every session stays in the table; is_reliable says whether to use the number.

## What the data showed
- Qualifying: track faster in 87 of 87 reliable sessions, median -0.15 s per 10 min.
- Sprint qualifying evolves about twice as fast (-0.33), because only one practice runs before it, so the track is greener.
- FP2 is the noisiest practice session (13 of 74 "slower"), because high-fuel long runs mix fuel and tyre wear into the lap times.

## For the forecaster
Correct for evolution before comparing runs from different times: a late FP2 run had a faster
track, so subtract evolution x minutes between the runs.

## What is tested, and what is not
| table | data check | unit test | not tested yet |
|---|---|---|---|
| mart_stints | 14 one row per stint, laps add up | stints split by tyre set | deg on a real race |
| mart_long_runs | 15 practice only, enough laps, within 10% | drops push lap, adds fuel effect | fuel loads across teams |
| mart_track_evolution | 16 reliable sessions within 1 s/10 min | ignores who is faster (-0.1) | the is_reliable rule itself |
