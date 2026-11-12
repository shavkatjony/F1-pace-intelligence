# Codebase map

A practical guide to the repository: what each directory and module group is responsible for, what it reads and writes, how it is started, and where its tests and design records are. It explains functionality, not individual lines. For how the parts connect, see [architecture.md](architecture.md).

## Repository layout

```text
F1-pace-intelligence/
├── src/
│   ├── telemetry_core/     data layer: settings, ingestion, warehouse runner, telemetry alignment
│   └── dpec/               product layer: CLI, forecasting, decisions, record, debrief, AI, API, publishing
├── sql/
│   ├── core/               6 clean tables (sessions, laps, results, files, drivers, teams)
│   ├── marts/              9 answer tables
│   └── checks/             20 data checks (each returns the rows that break a rule)
├── seeds/                  small hand-written CSVs: team lineages, known source gaps
├── config/                 dpec.yaml (local) and public.yaml (online copy)
├── web/app/                the pit wall front end (plain HTML/CSS/JS)
├── web/prototype/          the first static UI prototype (fictional data, kept for history)
├── tests/                  129 unit tests on fake data (no internet, no API key)
├── evals/questions.yaml    the AI assistant's 50-question exam
├── notebooks/              exploration and research notebooks (original, not rewritten)
├── reports/                small evidence files kept in git (backtest scores, AI exam runs, research reports)
├── schemas/                JSON Schema of the public-record files
├── docs/                   documentation (this folder)
├── notes/                  raw lab notebook (unpolished working notes)
├── deploy/huggingface/     Hugging Face Space files (kept, not in use)
├── Dockerfile, .dockerignore
├── .github/workflows/      ci.yml (every push), release.yml (every published release)
├── Makefile                shortcuts for the common commands
└── pyproject.toml, uv.lock package definition and locked dependencies
```

The split between the two packages is deliberate. `telemetry_core` knows about F1 data but nothing about forecasting or the app, so it can be reused by a future module (for example the planned car root-cause comparison, [methods.md § 15](../methods.md#15-what-id-do-next)). `dpec` depends on `telemetry_core`, never the other way round.

## `src/telemetry_core/`: the data layer

| Module | Purpose | Inputs → outputs | Entry point | Tests | Record |
|---|---|---|---|---|---|
| [`config.py`](../../src/telemetry_core/config.py) | Typed settings. Pydantic models with `extra="forbid"`, so a misspelt key is an error; ranges are validated (for example `slow_lap_pct` between 100 and 150, seasons from 2018) | YAML file → `Settings` | `load_settings()`, used by every command | [`test_config.py`](../../tests/test_config.py) | |
| [`paths.py`](../../src/telemetry_core/paths.py) | Hive-style raw folder names: `season=2024/event=01_bahrain_grand_prix/session=race` | season, round, names → `Path` | used by `ingest` | [`test_paths.py`](../../tests/telemetry_core/test_paths.py) | [0002](../decisions/0002-storage.md) |
| [`ingestion/fastf1_source.py`](../../src/telemetry_core/ingestion/fastf1_source.py) | The only module that talks to FastF1: schedule, session list, session start times, and `fetch_session()` returning seven untouched tables | FastF1 → DataFrames + session info | `dpec ingest`, `dpec freeze` | [`test_cli_ingest.py`](../../tests/dpec/test_cli_ingest.py) | [0005](../decisions/0005-results-and-log.md) |
| [`ingestion/writer.py`](../../src/telemetry_core/ingestion/writer.py) | Writes each table as Parquet (time spans become float seconds), plus `manifest.json` with rows, columns and SHA-256 per file; `is_saved()` makes re-runs skip | DataFrames → `data/raw/...` | `dpec ingest` | [`test_writer.py`](../../tests/telemetry_core/test_writer.py) | [0002](../decisions/0002-storage.md) |
| [`ingestion/log.py`](../../src/telemetry_core/ingestion/log.py) | Append-only download log: one line per attempt (`ok`, `failed`, `rate_limited`) | → `data/ingest_log.csv` | `dpec ingest` | [`test_cli_ingest.py`](../../tests/dpec/test_cli_ingest.py) | [0005](../decisions/0005-results-and-log.md) |
| [`warehouse.py`](../../src/telemetry_core/warehouse.py) | The SQL runner: `build()` runs a folder's `.sql` files in name order with `{{ }}` placeholders; `run_checks()`; `undocumented_columns()` compares the warehouse against the data dictionary; `query()` | SQL + Parquet → DuckDB file | `dpec build`, `dpec check`, `dpec sql` | [`test_warehouse.py`](../../tests/telemetry_core/test_warehouse.py), [`test_marts.py`](../../tests/telemetry_core/test_marts.py) | [0003](../decisions/0003-clean-laps.md), [0006](../decisions/0006-checks-and-id-maps.md), [0007](../decisions/0007-marts.md) |
| [`alignment/lap_telemetry.py`](../../src/telemetry_core/alignment/lap_telemetry.py) | Loads one lap's car telemetry and track position from the raw files, using lap facts from `core_laps` | warehouse + raw → telemetry rows | `dpec compare`, API `/compare`, debrief | [`test_distance_grid.py`](../../tests/telemetry_core/test_distance_grid.py) | [0004](../decisions/0004-distance-grid.md) |
| [`alignment/distance_grid.py`](../../src/telemetry_core/alignment/distance_grid.py) | Puts a lap on a fixed grid (default 5 m), interpolated so the grid lap time equals the official one; stretches the second lap to the reference length; finds apexes; computes the time delta | telemetry → grid table | as above | [`test_distance_grid.py`](../../tests/telemetry_core/test_distance_grid.py) | [0004](../decisions/0004-distance-grid.md) |
| [`alignment/compare.py`](../../src/telemetry_core/alignment/compare.py) | Two laps side by side and a per-corner table | two lap ids → comparison | API `/compare` | [`test_api.py`](../../tests/dpec/test_api.py) | [0004](../decisions/0004-distance-grid.md) |

## SQL

All SQL runs inside DuckDB through `warehouse.build()`. Placeholders (`{{ raw }}`, `{{ seeds }}`, `{{ slow_lap_pct }}`, `{{ fuel_effect_s_per_lap }}`, `{{ long_run_min_laps }}`, `{{ long_run_band_pct }}`, `{{ push_lap_band_pct }}`) come from `sql_params()` in [`cli.py`](../../src/dpec/cli.py). Columns of every table are documented in the [data dictionary](../data-dictionary.md).

| Group | Files | What it does | Record |
|---|---|---|---|
| [`sql/core/`](../../sql/core/) | `01_core_sessions` … `06_dim_teams` | Reads the raw Parquet with `read_parquet(..., hive_partitioning = true, union_by_name = true)`; renames and types columns; assigns lap reason codes; fills missing team names; builds the driver and team ID maps | [0003](../decisions/0003-clean-laps.md), [0005](../decisions/0005-results-and-log.md), [0006](../decisions/0006-checks-and-id-maps.md) |
| [`sql/marts/`](../../sql/marts/) | `01_mart_weekends` … `09_mart_race_strategy` | Weekend overview, weather summary, championship standings (window functions), session pace, tyre stints and wear, practice long runs, track evolution, pre-race signals, race strategy and pit loss | [0007](../decisions/0007-marts.md) to [0010](../decisions/0010-forecast-signals.md), [0014](../decisions/0014-decision-packet.md) |
| [`sql/checks/`](../../sql/checks/) | `01` … `20` | One rule per file, returning the offending rows. Grain checks (01–03, 10, 12, 14, 17, 19), completeness (05, 07–09, 13), arithmetic (06, 11), allowed values and plausibility (04, 15, 16, 18, 20) | [0006](../decisions/0006-checks-and-id-maps.md) |
| [`notebooks/02_analytics/b1_questions.sql`](../../notebooks/02_analytics/b1_questions.sql) | one file | Exploratory questions on the marts (wet races, pole-to-win share, title margins) | |

**Seeds.** [`seeds/teams.csv`](../../seeds/teams.csv) maps 15 team names to 11 lineages (for example Alfa Romeo, Kick Sauber and Audi are one lineage). [`seeds/known_gaps.csv`](../../seeds/known_gaps.csv) lists source gaps that are expected, so check 07 does not flag them.

## `src/dpec/`: the product layer

### Command line: [`cli.py`](../../src/dpec/cli.py)

Built with Typer. Most commands take `--config` (default `config/dpec.yaml`). Imports of the forecasting, decision and AI modules happen inside the commands that use them.

| Command | What it does | Writes | Record |
|---|---|---|---|
| `dpec info` | Prints the active settings | | |
| `dpec ingest [--season --round --session --force]` | Downloads sessions not yet saved; continues past a failed session; stops cleanly on a FastF1 rate limit | `data/raw/`, `data/ingest_log.csv` | [0002](../decisions/0002-storage.md), [0005](../decisions/0005-results-and-log.md) |
| `dpec build` | Rebuilds the warehouse: `sql/core`, then `sql/marts` | `data/warehouse.duckdb` | [0003](../decisions/0003-clean-laps.md), [0007](../decisions/0007-marts.md) |
| `dpec check` | 20 SQL checks + data dictionary check; exits 1 on any failure and prints sample bad rows | | [0006](../decisions/0006-checks-and-id-maps.md) |
| `dpec sql "<query>"` | Runs one query and prints the result | | |
| `dpec compare <session_key> <drv> <lap> <drv2> <lap2>` | Two laps on the distance grid, corner alignment table, chart | `reports/figures/` (not in git) | [0004](../decisions/0004-distance-grid.md) |
| `dpec backtest [--first-season 2023 --test-from 2025]` | Walk-forward forecast of every past dry race by every forecaster, ranges and chances, scores by tune/test years | `data/forecasts/backtest.parquet`, `reports/backtest/scores.csv`, `ranges.csv` | [0011](../decisions/0011-target-and-fair-test.md)–[0013](../decisions/0013-ranges-and-chances.md) |
| `dpec replay` | Replays the tyre and stop decision for every past dry race | `data/forecasts/decisions.parquet`, `reports/backtest/decisions.csv` | [0014](../decisions/0014-decision-packet.md) |
| `dpec packet --season --round` | One race's decision packet as a page | `reports/packets/` | [0014](../decisions/0014-decision-packet.md) |
| `dpec freeze --season --round [--checkpoint --race-laps --dry-run]` | Freezes a forecast and tyre decision; refuses after the deadline (30 min before the session) | `ledger/…` or `reports/dry-runs/…` | [0015](../decisions/0015-public-record.md) |
| `dpec score --season --round [--dry-run]` | Scores a frozen weekend into a new `score.json` | next to the frozen files | [0015](../decisions/0015-public-record.md) |
| `dpec ledger [--since <commit> --late-check]` | Validates every ledger file and its hash; in CI, rejects changed, deleted or late files | | [0015](../decisions/0015-public-record.md) |
| `dpec pretend --season` | Freezes and scores every dry race of a past season the live way, and compares with the backtest | `reports/dry-runs/`, `reports/pretend-ledger/` | [0015](../decisions/0015-public-record.md) |
| `dpec schema` | Exports the ledger file formats as JSON Schema | `schemas/` | [0015](../decisions/0015-public-record.md) |
| `dpec debrief --season --round` | Post-race debrief for the adopted team's cars | `reports/debriefs/` | [0016](../decisions/0016-debrief.md) |
| `dpec ask "<question>" [--provider]` | One question to the AI assistant, printing tools used, time and tokens | | [0017](../decisions/0017-race-engineer.md) |
| `dpec eval-ai [--provider --only --dry-run]` | Runs the 50-question exam; `--dry-run` prints the computed right answers without calling a model | `reports/ai/eval-<provider>-<model>-<date>.csv` | [0017](../decisions/0017-race-engineer.md) |
| `dpec eval-report` | Compares all saved exam runs | `reports/ai/README.md` | [0017](../decisions/0017-race-engineer.md) |
| `dpec snapshot` | Packs the public copy's data with checksums | `dist/dpec-data-<date>.tar.gz` | [0018](../decisions/0018-public-copy.md) |
| `dpec serve [--host --port --config]` | Starts the API and the app (default `127.0.0.1:8000`; API docs at `/api/docs`) | | [0018](../decisions/0018-public-copy.md) |

### Forecasting: [`forecasting/`](../../src/dpec/forecasting/)

| Module | Responsibility |
|---|---|
| [`targets.py`](../../src/dpec/forecasting/targets.py) | The target `race_pace_gap_pct` and the single training table (one row per driver per dry race weekend). `CHECKPOINTS` lists the columns hidden at each checkpoint; `hide_answers()` removes them |
| [`features.py`](../../src/dpec/forecasting/features.py) | `team_form` (exponentially weighted team race gap, shifted so a race never sees itself) and `driver_vs_team`, from earlier races only |
| [`baselines.py`](../../src/dpec/forecasting/baselines.py) | Five reference forecasters with one signature, `forecaster(history, today)`: no signal, last race, team form, signal as is, per-year model |
| [`model.py`](../../src/dpec/forecasting/model.py) | The shared model: one weighted least-squares formula per checkpoint, recency weights with a 12-race half-life, at least 50 training rows |
| [`backtest.py`](../../src/dpec/forecasting/backtest.py) | `walk_forward()`: for each dry weekend from 2023, history = earlier weekends only; `score()`: MAE in % and in seconds on a 90 s lap, median per-weekend Spearman |
| [`ranges.py`](../../src/dpec/forecasting/ranges.py) | 80% ranges from the 80th percentile of absolute errors over the last 10 forecast weekends (none until 5 have passed); coverage table |
| [`simulate.py`](../../src/dpec/forecasting/simulate.py) | 4,000 replays of the race order (seed 0) → chance of best pace, top 3, beating the teammate |

Tests: [`test_forecasting.py`](../../tests/dpec/test_forecasting.py), [`test_model.py`](../../tests/dpec/test_model.py), [`test_ranges.py`](../../tests/dpec/test_ranges.py). Design: [0010](../decisions/0010-forecast-signals.md)–[0013](../decisions/0013-ranges-and-chances.md), [model card](../model-card.md).

### Strategy decisions: [`decisions/`](../../src/dpec/decisions/)

| Module | Responsibility |
|---|---|
| [`tyres.py`](../../src/dpec/decisions/tyres.py) | Race tyre wear forecast `race_deg ~ practice_deg + circuit_deg` from earlier races (needs 15); pit loss as the circuit's historical median; useful tyre life |
| [`plans.py`](../../src/dpec/decisions/plans.py) | Cost of 1, 2 and 3-stop plans (wear × laps of tyre age + stops × pit loss); comparison over draws; the 65% "clear decision" threshold; first-stop window; the wear level at which another plan wins |
| [`replay.py`](../../src/dpec/decisions/replay.py) | Decision for any past race from earlier data only; scoring against top-10 stops, wear range and first-stop window; `decide_next()` for a race not yet run |
| [`packet.py`](../../src/dpec/decisions/packet.py) | The one-page decision packet: forecast, tyres, plan, computed risks, then what happened |

Tests: [`test_decisions.py`](../../tests/dpec/test_decisions.py). Design: [0014](../decisions/0014-decision-packet.md).

### Public record: [`record/`](../../src/dpec/record/)

| Module | Responsibility |
|---|---|
| [`ledger.py`](../../src/dpec/record/ledger.py) | Pydantic models of the forecast and score files (`Forecast`, `Score`, …); content hash; `write_once()`; validation; git-based change and deadline checks; `code_version()` |
| [`live.py`](../../src/dpec/record/live.py) | A weekend as it looks before its target session (for a race that has not run yet) |
| [`freeze.py`](../../src/dpec/record/freeze.py) | Builds and deadline-checks the frozen record: forecasts, ranges, chances, baselines, tyre decision |
| [`score.py`](../../src/dpec/record/score.py) | Scores a frozen weekend with the backtest's measures; verdict GOOD / OK / MISS |

Tests: [`test_record.py`](../../tests/dpec/test_record.py). Design: [0015](../decisions/0015-public-record.md). Formats: [`schemas/forecast.schema.json`](../../schemas/forecast.schema.json), [`schemas/score.schema.json`](../../schemas/score.schema.json).

### Debrief: [`debrief/`](../../src/dpec/debrief/)

| Module | Responsibility |
|---|---|
| [`segments.py`](../../src/dpec/debrief/segments.py) | Classifies each 5 m grid step as braking, straight (throttle ≥ 95%), traction, slow (< 120 km/h), medium or fast (≥ 200 km/h) corner, and splits a lap gap by kind; the parts add up to the gap |
| [`attribution.py`](../../src/dpec/debrief/attribution.py) | Paired clean laps (same lap number, both dry); regression into pace, tyre age, compound and traffic (within 1.5 s of a car ahead); 1,000 bootstrap resamples for 80% ranges; needs 10 paired laps |
| [`report.py`](../../src/dpec/debrief/report.py) | Combines both parts with the forecast (frozen if one exists, else the backtest's) into a page of templated sentences |

Tests: [`test_debrief.py`](../../tests/dpec/test_debrief.py). Design: [0016](../decisions/0016-debrief.md).

### AI assistant: [`assistant/`](../../src/dpec/assistant/)

| Module | Responsibility |
|---|---|
| [`tools.py`](../../src/dpec/assistant/tools.py) | Eight read-only tools: `tables`, `sql`, `lap_split`, `race_gap`, `forecast`, `tyre_decision`, `public_record`, `data_status`. The SQL guard: one `SELECT`/`WITH` statement, known tables only (checked with DuckDB's parser), a blocked list of file-reading functions (`read_*`, `*_scan`, `glob`, `sniff_csv`; one gap in [workstream 06 § 12](../workstreams/06-applied-ai.md#12-limitations-and-operational-considerations)), read-only connection, 10 s timeout, 50 rows, 20,000 characters |
| [`engineer.py`](../../src/dpec/assistant/engineer.py) | The system prompt and the loop `ask()`: send question, run requested tools, return results, repeat up to `max_tool_calls` |
| [`chat.py`](../../src/dpec/assistant/chat.py) | One conversation interface for every provider; `ScriptedChat` stand-in for tests; `ProviderError` for missing key, server or model |
| [`claude.py`](../../src/dpec/assistant/claude.py) | Anthropic SDK adapter (key from `ANTHROPIC_API_KEY`, never from config) |
| [`ollama.py`](../../src/dpec/assistant/ollama.py) | Local model adapter (`qwen3:8b` by default) |
| [`evals.py`](../../src/dpec/assistant/evals.py) | The exam: loads [`evals/questions.yaml`](../../evals/questions.yaml), computes right answers from the warehouse at run time, grades numbers, words and refusals, estimates cost at list prices, saves and compares runs |

Tests: [`test_assistant.py`](../../tests/dpec/test_assistant.py). Design: [0017](../decisions/0017-race-engineer.md). Results: [`reports/ai/`](../../reports/ai/README.md). Details: [workstream 06](../workstreams/06-applied-ai.md).

### API: [`api/`](../../src/dpec/api/)

[`main.py`](../../src/dpec/api/main.py) builds the app with `create_app(config)` (tests pass a config that points at a fake warehouse) and mounts the static app at `/`. All routes are under `/api`; interactive docs at `/api/docs`. Path parameters are typed (a bad session type returns 422; an unknown weekend returns 404).

| Method and path | Returns | Router |
|---|---|---|
| `GET /health` | status, mode, session count, latest event and date, snapshot info | [`analytics.py`](../../src/dpec/api/routes/analytics.py) |
| `GET /settings` | team name and adopted team | analytics |
| `GET /weekends[?season=]` | every weekend, newest first | analytics |
| `GET /weekends/{season}/{round}` | overview and sessions in time order | analytics |
| `GET /weekends/{season}/{round}/pace?session=Q` | best and median clean lap per driver | analytics |
| `GET /weekends/{season}/{round}/laps?driver=&session=R` | every lap of one driver, with long-run flags | analytics |
| `GET /weekends/{season}/{round}/long-runs?session=FP2` | practice long runs | analytics |
| `GET /weekends/{season}/{round}/stints?session=R` | tyre stints in finishing order | analytics |
| `GET /weekends/{season}/{round}/weather` | weather and track evolution per session | analytics |
| `GET /weekends/{season}/{round}/quality` | lap reason counts and empty tables | analytics |
| `GET /weekends/{season}/{round}/results?session=R` | official classification | analytics |
| `GET /standings/{season}/{round}` | drivers' and teams' championship after the round | analytics |
| `GET /weekends/{season}/{round}/compare?a=&b=` | two laps on one distance grid (local only) | analytics |
| `GET /weekends/{season}/{round}/forecast` | the shared model's forecast at both checkpoints | [`forecasts.py`](../../src/dpec/api/routes/forecasts.py) |
| `GET /record?source=ledger\|dry-runs` | frozen weekends with scores, or the dry runs | [`record.py`](../../src/dpec/api/routes/record.py) |
| `GET /weekends/{season}/{round}/debrief?a=&b=&session=Q` | lap split by track section, and the race part | [`debrief.py`](../../src/dpec/api/routes/debrief.py) |
| `POST /chat` `{"question": "..."}` | answer and tools used (local only; 403 in public mode) | [`chat.py`](../../src/dpec/api/routes/chat.py) |
| `GET /chat/recorded` | the newest exam run joined with its questions | chat |

Tests: [`test_api.py`](../../tests/dpec/test_api.py), including a test that the API is read-only and that the public copy refuses telemetry and chat.

### Publishing: [`publish/snapshot.py`](../../src/dpec/publish/snapshot.py)

Collects the warehouse, `data/forecasts/*.parquet`, `ledger/**/*.json` and `reports/dry-runs/**/*.json`; writes `SHA256SUMS` and `manifest.json` (snapshot date, data range, code version); `verify()` re-checks an unpacked snapshot. Tests: [`test_publish.py`](../../tests/dpec/test_publish.py), including that a one-character change is caught.

## Front end: [`web/app/`](../../web/app/)

| File | Responsibility |
|---|---|
| [`index.html`](../../web/app/index.html) | Page shell: weekend picker, session and driver selectors, layout bar |
| [`app.js`](../../web/app/app.js) | Window definitions (15 window types), layout presets (a separate set in public mode), linked selection, settings and layouts saved in `localStorage` |
| [`api.js`](../../web/app/api.js) | The only file that calls the server: a cached `get()` for `/api/...`; errors keep status and detail so a window can show the full text locally or one plain sentence online |
| [`style.css`](../../web/app/style.css) | Retro "race programme" visual style |
| [`img/telemetry-example.png`](../../web/app/img/telemetry-example.png) | The picture shown online in place of live telemetry windows |

## Configuration

Both files are read through [`config.py`](../../src/telemetry_core/config.py). Nothing below is hard-coded elsewhere.

| Key | Default | Meaning | Record |
|---|---|---|---|
| `team_name` | `DPEC` | display name of the fictional team | [0001](../decisions/0001-dpec-team.md) |
| `adopted_team` | `Mercedes` | the real team whose two cars are "ours" | [0001](../decisions/0001-dpec-team.md) |
| `seasons` | 2022–2026 | seasons to ingest and model (2018 or later) | |
| `grid_step_m` | 5 | distance grid spacing | [0004](../decisions/0004-distance-grid.md) |
| `slow_lap_pct` | 107 | a lap slower than this % of the session's clean median is `slow` | [0003](../decisions/0003-clean-laps.md) |
| `fuel_effect_s_per_lap` | 0.06 | assumed lap-time gain per lap of fuel burnt (fuel loads are not public) | [0008](../decisions/0008-stints-and-long-runs.md) |
| `long_run_min_laps` | 5 | minimum clean laps in a practice long run | [0008](../decisions/0008-stints-and-long-runs.md) |
| `long_run_band_pct` | 2 | long-run laps stay within this % of the stint median | [0008](../decisions/0008-stints-and-long-runs.md) |
| `push_lap_band_pct` | 1.5 | push laps are within this % of the driver's best on that tyre (used for track evolution) | [0008](../decisions/0008-stints-and-long-runs.md), [0009](../decisions/0009-track-evolution.md) |
| `mode` | `local` / `public` | full system or read-only online copy | [0018](../decisions/0018-public-copy.md) |
| `paths.*` | `data/…`, `sql`, `seeds`, `docs/data-dictionary.md` | locations of every store | |
| `assistant.provider` | `claude` | `claude` or `ollama` | [0017](../decisions/0017-race-engineer.md) |
| `assistant.claude_model`, `effort` | `claude-opus-5-5`, `medium` | Claude model and reasoning effort | [0017](../decisions/0017-race-engineer.md) |
| `assistant.ollama_model`, `ollama_url` | `qwen3:8b`, `http://localhost:11434` | local model | [0017](../decisions/0017-race-engineer.md) |
| `assistant.max_tool_calls` | 8 | tool calls allowed before the model must answer (1–20) | [0017](../decisions/0017-race-engineer.md) |

Environment variable: `ANTHROPIC_API_KEY` (only for the Claude provider; never stored in the project).

## Tests

129 tests, all on small fake data built in the tests themselves (`tests/telemetry_core/test_warehouse.py` provides a fake race weekend that other tests reuse through `pythonpath` in `pyproject.toml`). They need no internet, no raw data and no API key.

| Group | Files | Covers |
|---|---|---|
| Settings and paths | `test_config.py`, `test_paths.py` | the real config loads; typos, a wrong mode or out-of-range values fail |
| Ingestion | `test_writer.py`, `test_cli_ingest.py` | Parquet + manifest; skip on re-run; failure logging; rate-limit handling |
| Warehouse and data | `test_warehouse.py`, `test_marts.py` | lap reason codes, grain, ID maps, mart logic, checks |
| Telemetry | `test_distance_grid.py` | grid lap time equals the official lap time; alignment |
| Forecasting | `test_forecasting.py`, `test_model.py`, `test_ranges.py` | no leakage across weekends, baselines, the shared model, range coverage |
| Decisions and record | `test_decisions.py`, `test_record.py` | plan costs, threshold, write-once ledger, hash, deadline, scoring |
| Debrief | `test_debrief.py` | effects planted on purpose are recovered; parts add up |
| AI | `test_assistant.py` | SQL guard, tool loop limit, both providers' request formats against stand-in servers, grader |
| API and publishing | `test_api.py`, `test_publish.py` | read-only API, 404/422 behaviour, public-mode refusals; public settings differ only in `mode`; snapshot checksums catch a change |

The data checks in `sql/checks/` complement the tests: tests prove the logic on fake data, checks prove the real warehouse obeys the rules.

## Notebooks and reports

Original research material, kept as it was written. The [research archive](../research/README.md) explains what each investigation found.

| File | What it is |
|---|---|
| [`notebooks/01_data/01_meet_the_data.ipynb`](../../notebooks/01_data/01_meet_the_data.ipynb) | First look at FastF1's tables, their shapes and grain |
| [`notebooks/02_research/b3_practice_vs_race.ipynb`](../../notebooks/02_research/b3_practice_vs_race.ipynb) | Which pre-race signal predicts race pace; summary in [`reports/b3-practice-vs-race.md`](../../reports/b3-practice-vs-race.md) |
| [`notebooks/03_forecast/c2_shared_model.ipynb`](../../notebooks/03_forecast/c2_shared_model.ipynb) | Shared versus separate models, circuit offsets |
| [`notebooks/03_forecast/c3_ranges_and_chances.ipynb`](../../notebooks/03_forecast/c3_ranges_and_chances.ipynb) | Range calibration, chances, input ablation |
| [`reports/backtest/`](../../reports/backtest/) | `scores.csv`, `ranges.csv`, `decisions.csv` from the latest backtest and replay |
| [`reports/ai/`](../../reports/ai/README.md) | Every exam answer, tool call, time and token count |
| [`reports/numbers-check.md`](../../reports/numbers-check.md) | Every published number traced to its source |

## See also

- [architecture.md](architecture.md) · [operations.md](operations.md)
- [Data dictionary](../data-dictionary.md) · [Decision records](../decisions/README.md)
- [Workstream documents](../README.md#workstreams-one-discipline-at-a-time): [01 data](../workstreams/01-data-engineering.md) · [02 analytics](../workstreams/02-data-analytics-statistics.md) · [03 forecasting](../workstreams/03-forecasting-machine-learning.md) · [04 ML engineering](../workstreams/04-ml-engineering.md) · [05 backend](../workstreams/05-backend-engineering.md) · [06 applied AI](../workstreams/06-applied-ai.md)
