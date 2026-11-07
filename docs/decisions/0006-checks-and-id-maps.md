# 0006 · Data checks and ID maps

Date: 2026-10-21
Status: accepted
Builds on: [0003](0003-clean-laps.md) clean laps, [0005](0005-results-and-log.md) results and log

## Decision
- `dpec check` runs every SQL file in sql/checks. A check returns the rows that break
  its rule; empty = pass. It also fails if a warehouse column is missing from
  docs/data-dictionary.md. `make data` = ingest, build, check.
- Driver ID map (dim_drivers): a driver code is one driver within a season. Missing
  driver_id (all sprint qualifying, 6 qualifying no-shows) is borrowed from the same season.
- Team ID map (dim_teams, from seeds/teams.csv): one lineage per team across name changes.
- Empty team names (2026 R5 and R7 FP1): same driver, same weekend first; then same
  driver, same car number, same season (FP1 stand-ins).

## Why "return the bad rows"
A failed check then shows which rows broke the rule and how many, so it can be read and fixed
at once; a query that returns true or false only says that something is wrong somewhere.

## Lineage choices
- Audi (2026) continues the Sauber lineage (with Alfa Romeo and Kick Sauber): the same
  factory in Hinwil, with a new owner and name.
- Racing Bulls (with AlphaTauri and RB) is its own lineage, not Red Bull Racing's: the same
  owner, but a different factory and car.
This gives 11 lineages for 15 team names.

## Three messy races, checked by hand
- Australia 2023 (three red flags): 49 laps ran under a red flag, yet none is labelled
  `red_flag`: 48 have no lap time, and the first rule that matches wins, so they are
  `no_time`. 1,003 laps, 737 clean; 3 retired (Russell, Albon, Leclerc); 102 points
  (101 plus the fastest-lap point that 2023 still had).
- Spain 2025: only 19 cars in the race results. Stroll (Aston Martin) is in qualifying but
  has no race row, because he didn't start. 1,203 laps, 980 clean, 101 points.
- Las Vegas 2025: Norris and Piastri were disqualified after the race. Both have 0 points,
  are classified `D`, and sit at finish positions 19 and 20, after the three retirements.
  886 laps, 760 clean, 5 not classified, 101 points.

## Gate A
`make data` from an empty warehouse: 10 of 10 checks pass. A fresh clone: 41 tests pass.
(That was the gate on 21 October; the project now has 21 checks.)
