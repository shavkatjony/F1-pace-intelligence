# Research archive

This archive explains **why** F1 Pace Intelligence was built the way it was: what was investigated, what was expected, what the data showed, what was rejected, and which design each result changed. It is the evidence trail behind the [decision records](../decisions/README.md).

It does not describe how to run the system. That is in the [engineering reference](../engineering/README.md) and, one discipline at a time, in the [workstream documents](../README.md#workstreams-one-discipline-at-a-time).

## How it is organised

| Part | What it holds |
|---|---|
| [experiment-register.md](experiment-register.md) | One-line index of every significant investigation: question, finding, status, evidence, the decision it fed |
| [cases/](#case-studies) | Short case studies of the nine investigations that changed the design the most |
| Original materials (outside this folder) | The notebooks, SQL, reports and code the cases cite. They are kept exactly as written and are not replaced by these summaries |

### Case studies

| # | Case | Decision records |
|---|---|---|
| 01 | [When does a lap count as race pace?](cases/01-lap-eligibility.md) | [0003](../decisions/0003-clean-laps.md) |
| 02 | [Inconsistencies in the official timing feed](cases/02-source-inconsistencies.md) | [0005](../decisions/0005-results-and-log.md), [0006](../decisions/0006-checks-and-id-maps.md), [0007](../decisions/0007-marts.md) |
| 03 | [Does practice or qualifying predict the race?](cases/03-practice-vs-qualifying.md) | [0010](../decisions/0010-forecast-signals.md) |
| 04 | [Tyre wear when fuel loads are unknown](cases/04-fuel-and-tyre-degradation.md) | [0008](../decisions/0008-stints-and-long-runs.md), [0014](../decisions/0014-decision-packet.md) |
| 05 | [Measuring track evolution](cases/05-track-evolution.md) | [0009](../decisions/0009-track-evolution.md) |
| 06 | [One shared model or many, and the 2026 rules change](cases/06-shared-vs-separate-models.md) | [0012](../decisions/0012-shared-model.md) |
| 07 | [Temporal validation, leakage and honest ranges](cases/07-temporal-validation-and-ranges.md) | [0011](../decisions/0011-target-and-fair-test.md), [0013](../decisions/0013-ranges-and-chances.md), [0015](../decisions/0015-public-record.md) |
| 08 | [Scoring a strategy call that was never raced](cases/08-strategy-modelling.md) | [0014](../decisions/0014-decision-packet.md) |
| 09 | [Release, deployment and losing data access](cases/09-release-deployment-data-access.md) | [0015](../decisions/0015-public-record.md), [0018](../decisions/0018-public-copy.md) |

Every case has the same nine parts: research question, initial hypothesis, dataset and scope, method, results, interpretation, decision influenced, limitations, and links to the original evidence.

## Where the original evidence lives

| Material | Location |
|---|---|
| Research notebooks | [`notebooks/`](../../notebooks/): data exploration, practice versus race, shared model, ranges and chances |
| Research reports | [`reports/b3-practice-vs-race.md`](../../reports/b3-practice-vs-race.md) |
| Backtest and replay results | [`reports/backtest/`](../../reports/backtest/) |
| AI exam runs | [`reports/ai/`](../../reports/ai/README.md) |
| Number traceability | [`reports/numbers-check.md`](../../reports/numbers-check.md) |
| Implementation of each method | [`sql/`](../../sql/), [`src/`](../../src/), mapped in the [codebase map](../engineering/codebase-map.md) |
| Raw working notes, early plans | [`notes/`](../../notes/README.md) |
| Dates | each decision record's first-commit date; `git log --follow <file>` for any file |

## Evidence levels

Each finding is labelled so that a reader can tell a measured result from an assumption.

| Label | Meaning |
|---|---|
| **Validated** | Measured on held-out data or checked against the warehouse; reproducible with a command |
| **Implemented** | In the code and tested, but not separately validated on real outcomes |
| **Exploratory** | Seen in the data during an investigation; not used for a decision on its own |
| **Assumed** | A fixed value or rule that public data cannot measure (for example the fuel effect) |
| **Future** | Identified and written down, not built |

## What this archive does not claim

- It does not reconstruct a day-by-day chronology. Dates come from decision records and git history only.
- Results are on public timing data. Fuel loads, setups, engine modes, tyre temperatures and, in 2026, battery and active-aero state are not public, and several limitations below follow from that.
- The dry runs of the 2026 season were replayed after the races. They show that the live code reproduces the backtest; they are not a live forecasting record ([live-weekends.md](../live-weekends.md)).
