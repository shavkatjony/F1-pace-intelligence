# 0001 · DPEC adopts Mercedes's two cars

Date: 2026-10-11
Status: accepted
Updated: 2026-11-09 (how the choice is used in the code, and race wins from 2022 to 2026)
Builds on: nothing earlier (a starting decision)

## Decision
Team DPEC adopts Mercedes as the official real-world constructor whose telemetry and race data we track, model, and forecast.

## Why
- Provides an incredible multi-year engineering narrative, tracking their championship contention, the ground-effect regulation puzzle (porpoising), and their relentless development race back to regular race wins.
- Maintains consistent team identity and history across the 2022–2026 seasons without name changes breaking telemetry continuity.

## Rejected options
- Red Bull: Too dominant during large portions of this era, making competitive forecasting and performance anomaly detection less interesting.
- Haas: Limited development budgets and data consistency make deep telemetry insights harder to benchmark consistently.
- Ferrari: I follow it as a fan, so I'd be too emotionally involved to judge its data neutrally.

## Changing it later
Edit `adopted_team` in config/dpec.yaml. No code change.

## Update (9 November 2026): how the choice is used, and what the data shows
The decision is unchanged. This section records where the code uses it and what the saved
data says about the reasons above.

How it works:
- One setting, `adopted_team: Mercedes`, in config/dpec.yaml and config/public.yaml. The
  settings check only that it isn't empty.
- `our_lineage()` in src/dpec/decisions/packet.py turns the name into a lineage from
  dim_teams, so a team's cars stay "ours" across its renames. Mercedes has one name, one id
  and one lineage (`mercedes`) from 2022 to 2026.
- The lineage decides which cars the decision packet and the debrief are about, which
  drivers carry `ours = true` in a frozen forecast and in the race engineer's forecast tool,
  and what `/api/settings` and `dpec info` report. The race engineer's system prompt names
  the team.
- The forecasting model does not depend on it: it is fitted on every driver (decision 0012).
- No other code names Mercedes (only a docstring example, the app's colour for each team and
  test data), so "Changing it later" above holds.

Race wins in the saved warehouse (core_results, races only; 2026 up to the Singapore Grand
Prix, 11 October 2026):

| Season | Races | Mercedes | Red Bull | Ferrari | McLaren |
|---|---|---|---|---|---|
| 2022 | 22 | 1 | 17 | 4 | 0 |
| 2023 | 22 | 0 | 21 | 1 | 0 |
| 2024 | 24 | 4 | 9 | 5 | 6 |
| 2025 | 24 | 2 | 8 | 0 | 14 |
| 2026 | 17 | 11 | 2 | 2 | 2 |

- Red Bull won 38 of the 44 races of 2022 and 2023: the dominance given above as the reason
  not to pick it. Mercedes went from 1 and 0 wins in those years to 11 of 17 in 2026: the
  comeback in the first reason. Haas won no race in the period.
- Name continuity holds for Mercedes but is not special to it. Eight of the eleven team
  lineages kept one name from 2022 to 2026, and Cadillac joined in 2026. The two renamed
  teams (AlphaTauri, RB, Racing Bulls; Alfa Romeo, Kick Sauber, Audi) are joined by the
  lineage column in dim_teams (decision 0006), so their cars would also have stayed "ours"
  across the renames.

Known limits:
- A name that matches no team is not rejected: `our_lineage()` returns nothing and no car is
  marked as ours. Checked on 9 November 2026: "Mercedes" and "mercedes" give `mercedes`,
  "Audi" and "Kick Sauber" give `sauber`, "Mercedez" gives none.
- Any season's name of a team selects its whole lineage: "Audi" also selects the Kick Sauber
  and Alfa Romeo years.