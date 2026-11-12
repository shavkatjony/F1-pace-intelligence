# Engineering reference

This section is for engineers who want to run, change or debug F1 Pace Intelligence. It covers the system **as it exists today**. The reasons behind it, meaning what was investigated, what failed and what evidence changed the plan, are in the [research archive](../research/README.md) and the [decision records](../decisions/README.md).

## The system in one paragraph

A command-line tool (`dpec`) downloads every Formula 1 session from 2022 to 2026 through [FastF1](https://docs.fastf1.dev/) and saves each one once, unchanged, as Parquet files with a checksum manifest. Plain SQL files rebuild a [DuckDB](https://en.wikipedia.org/wiki/DuckDB) warehouse from those files: clean core tables, then analysis tables ("marts"). Twenty SQL data checks run on every rebuild. Python modules on top of the warehouse produce race-pace forecasts with 80% ranges, tyre and pit-stop decisions, post-race debriefs and a tool-using AI assistant. A read-only FastAPI service and a plain JavaScript app serve all of this locally. A versioned data snapshot and a Docker image, built by GitHub Actions, serve a read-only public copy.

## Documents

| Document | Read it when you want to know |
|---|---|
| [architecture.md](architecture.md) | How the parts fit together: data flow, stores, runtime modes, design boundaries |
| [codebase-map.md](codebase-map.md) | Where something is implemented: every package, module group, SQL group, command, endpoint, setting and test group |
| [operations.md](operations.md) | How to set up, rebuild, validate, backtest, evaluate, release and deploy, and what to do when something breaks |

For one discipline at a time, with its own evidence and limits, read the six [workstream documents](../README.md#workstreams-one-discipline-at-a-time): [data engineering](../workstreams/01-data-engineering.md), [analytics and statistics](../workstreams/02-data-analytics-statistics.md), [forecasting and ML](../workstreams/03-forecasting-machine-learning.md), [ML engineering](../workstreams/04-ml-engineering.md), [backend](../workstreams/05-backend-engineering.md) and [applied AI](../workstreams/06-applied-ai.md). They build on these three documents and do not repeat them.

## Related references (one home per fact)

These already exist and are not repeated here. Engineering documents link to them.

| Fact | Its home |
|---|---|
| Every table and column in the warehouse | [data-dictionary.md](../data-dictionary.md) (`dpec check` fails if a column is missing from it) |
| What the forecaster is for, its accuracy and limits | [model-card.md](../model-card.md) |
| The full story: question, data problems, method, numbers | [methods.md](../methods.md) |
| Why each design choice was made | [decisions/](../decisions/README.md) (18 records) |
| Where every published number comes from | [numbers-check.md](../../reports/numbers-check.md) |
| Live forecasts versus backtest versus dry runs | [live-weekends.md](../live-weekends.md) |

## Quick orientation

| If you want to… | Start at |
|---|---|
| Rebuild the data from scratch | [operations.md § Data pipeline](operations.md#2-data-pipeline), details in [workstream 01](../workstreams/01-data-engineering.md) |
| Add a warehouse table | [codebase-map.md § SQL](codebase-map.md#sql) and [decision 0007](../decisions/0007-marts.md) |
| Change a threshold (slow lap, long run, fuel effect) | [`config/dpec.yaml`](../../config/dpec.yaml), see [codebase-map.md § Configuration](codebase-map.md#configuration) |
| Change the forecaster | [`src/dpec/forecasting/`](../../src/dpec/forecasting/), then rerun the backtest ([operations.md § 4](operations.md#4-forecast-backtest-and-strategy-replay)); see [workstream 03](../workstreams/03-forecasting-machine-learning.md) and [workstream 04](../workstreams/04-ml-engineering.md) |
| Add an API endpoint | [`src/dpec/api/routes/`](../../src/dpec/api/routes/), tests in [`tests/dpec/test_api.py`](../../tests/dpec/test_api.py); see [workstream 05](../workstreams/05-backend-engineering.md) |
| Add a tool for the AI assistant | [`src/dpec/assistant/tools.py`](../../src/dpec/assistant/tools.py), then rerun the exam ([operations.md § 6](operations.md#6-ai-assistant-and-its-evaluation)); steps in [workstream 06 § 8](../workstreams/06-applied-ai.md#8-how-to-run-or-use-the-functionality) |
| Publish new data online | [operations.md § 9](operations.md#9-release-and-deployment) |
