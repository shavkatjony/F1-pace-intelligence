# 0014 · Tyre and stop decisions, and the decision packet

Date: 2026-10-24
Status: accepted

## Decision
- Race tyre wear = regression on earlier races: practice wear + this circuit's earlier race
  wear (practice alone says about 1.6x too much). 80% range from its last 20 errors.
- Pit loss = in-lap + out-lap - 2 normal laps, median of green-flag stops at this circuit in
  earlier races (all circuits for a new one).
- Plans: 1, 2 or 3 stops, equal stints, cost = wear x laps of tyre age + stops x pit loss.
  4,000 replays of tyre wear. Clear decision if the best plan wins in at least 65%;
  otherwise "no clear decision" and the two closest plans.
- First-stop window: laps within 1 s of the best timing, moved earlier by the undercut that
  earlier races showed (once 20 real first stops of that plan were seen).

## Why no compounds
The pace gap between compounds can't be measured reliably from public data (fuel loads and
engine modes are hidden, and practice runs mix both). A wrong compound model would look
precise and be wrong. Stops are what the data can support.

## How it's scored
Tyre wear error and range, stops against the top 10's most common number, real first stops
inside the window. Never "did the plan win": the other plans were not raced.

## Evidence
78 dry races 2023-2026, each from earlier races only: stops right 58% (always one stop: 46%);
clear calls 67% (51 races), no clear decision 41% (27 races). Wear error 0.028 s/lap.
65% threshold: the most right clear calls of 50-80% (same races: a sanity check).

## Known limits
- Wear ranges a bit narrow: 73% inside instead of 80%.
- Half of real first stops fall inside the window: no safety cars, traffic or rivals.
- Never picks 3 stops, though the top 10 made 3 or more in 10 of the 78 races.
- Wet races: no packet.
