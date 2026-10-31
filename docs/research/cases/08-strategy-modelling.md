# Case 08 · Scoring a strategy call that was never raced

Decision: [0014 · Tyre and stop decisions, and the decision packet](../../decisions/0014-decision-packet.md) (2026-10-28) · Register: E25, E26

## 1. Research question
Can public data support a useful pre-race decision on the number of pit stops, and how can such a decision be scored when the alternative plans were never raced?

## 2. Initial hypothesis
Costing 1, 2 and 3-stop plans from forecast tyre wear and pit-stop loss would give a clear best plan for most races, and "did the chosen plan win?" would be the score.

## 3. Dataset and scope
78 dry races from 2023 to 2026, each decided with only earlier races and that weekend's practice (`mart_race_strategy`, `mart_long_runs`). Race wear comes from [case 04](04-fuel-and-tyre-degradation.md).

## 4. Method
- **Pit loss:** in-lap + out-lap − 2 normal laps, the median of green-flag stops at this circuit in earlier races (all circuits for a new one). Check 20 keeps values between 15 and 35 s.
- **Plan cost:** wear × laps of tyre age (equal stints) + stops × pit loss, for 1, 2 and 3 stops, over 4,000 draws of tyre wear from its 80% range.
- **Call:** a plan is "clear" if it is best in at least 65% of draws; otherwise "no clear decision" plus the two closest plans.
- **First-stop window:** laps where stopping costs at most 1 s more than the best lap, shifted by the undercut seen in earlier races once 20 real first stops of that plan exist.
- **Scoring what can be checked:** wear error and range coverage; the call against the top-10 finishers' most common stop count; real first stops inside the window. Never "did the plan win".
- Baseline: always one stop.

## 5. Results

| Group | Races | Stop count right | Always one stop | Wear inside range | First stops inside window |
|---|---|---|---|---|---|
| All | 78 | **58%** | 46% | 73% | 52% |
| Clear call | 51 | **67%** | 57% | 69% | 47% |
| No clear decision | 27 | 41% | 26% | 82% | 67% |

- Wear error: 0.028 s/lap.
- The 65% threshold gave the most correct clear calls among thresholds from 50% to 80% (checked on the same races, so a sanity check, not a tuned result).
- Example, Bahrain 2024: the packet called 1 stop (best in 74% of draws) and named the risk that 2 stops would win if wear exceeded 0.093 s/lap. Real wear was 0.100 s/lap and the top 10 stopped twice. Wrong call, correct stated reason.

## 6. Interpretation
Scoring against the plans that were raced (the top 10's stop counts) is not the same as scoring against the best plan, but it is the only outcome public data can check. The value of the packet lies as much in the "no clear decision" label as in the calls: when races are close, it says so, and its accuracy drops in exactly those races. Compounds were left out because their pace gaps cannot be measured without fuel and engine-mode data, and a confident wrong compound model would mislead.

## 7. Decision influenced
- The decision packet: forecast, tyre wear, plan comparison, computed risks, then what happened ([`src/dpec/decisions/packet.py`](../../../src/dpec/decisions/packet.py)).
- The 65% "clear" threshold and the "no clear decision" output ([`plans.py`](../../../src/dpec/decisions/plans.py)).
- The same decision is frozen with each live forecast and scored after the race ([decision 0015](../../decisions/0015-public-record.md)).

## 8. Known limitations
- Wear ranges too narrow (73% inside instead of 80%).
- Only about half of real first stops fall inside the window: no safety cars, traffic or rivals are modelled.
- The model never chooses 3 stops, although the top 10 made 3 or more in 10 of the 78 races.
- No packet for wet races. A new circuit has no earlier race length, so the live path needs `--race-laps`.

## 9. Evidence and implementation
- Code: [`tyres.py`](../../../src/dpec/decisions/tyres.py), [`plans.py`](../../../src/dpec/decisions/plans.py), [`replay.py`](../../../src/dpec/decisions/replay.py), [`packet.py`](../../../src/dpec/decisions/packet.py)
- SQL: [`sql/marts/09_mart_race_strategy.sql`](../../../sql/marts/09_mart_race_strategy.sql), checks 19 and 20
- Results: [`reports/backtest/decisions.csv`](../../../reports/backtest/decisions.csv)
- Tests: [`tests/dpec/test_decisions.py`](../../../tests/dpec/test_decisions.py)
- Narrative: [methods.md § 8](../../methods.md#8-from-a-forecast-to-a-decision)
- How it works now: [workstream 03 · Forecasting and machine learning](../../workstreams/03-forecasting-machine-learning.md)

Previous: [Case 07](07-temporal-validation-and-ranges.md) · Next: [Case 09 · Release, deployment and data access](09-release-deployment-data-access.md)
