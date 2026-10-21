# 0006 · Data checks and ID maps

Date: 2026-10-15
Status: accepted

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
(your Part 1 question 2)

## Lineage choices
(your two decisions from Part 3, one line each)

## Three messy races, checked by hand
- Australia 2023: (your two lines)
- Spain 2025: (your two lines)
- Las Vegas 2025: (your two lines)

## Gate A
`make data` from an empty warehouse: 10 of 10 checks pass. A fresh clone: 41 tests pass.
