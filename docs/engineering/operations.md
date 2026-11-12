# Operations

How to set up, rebuild, validate, evaluate, release and deploy F1 Pace Intelligence. Every command here exists in the [`Makefile`](../../Makefile) or the [`dpec` CLI](codebase-map.md#command-line-clipy). Run them from the repository root.

**Status, November 2026.** New sessions cannot be downloaded: F1's timing service has required a login since October 2026, and FastF1 3.9+ needs a paid F1TV Access subscription. Everything below works on the data already saved (545 sessions, up to the 2026 Singapore Grand Prix). Steps that need new data are marked **(needs new data)**. Background: [live-weekends.md](../live-weekends.md).

## 1. Environment

| Need | Version / source |
|---|---|
| Python | 3.12 ([`.python-version`](../../.python-version)) |
| Package manager | [uv](https://docs.astral.sh/uv/). The Docker image pins uv 0.12.24 |
| Dependencies | locked in [`uv.lock`](../../uv.lock); runtime list in [`pyproject.toml`](../../pyproject.toml) |
| Docker | only for building or running the public image locally |
| AI assistant | `ANTHROPIC_API_KEY` in the environment (Claude), or [Ollama](https://ollama.com) with `ollama pull qwen3:8b` |
| Disk | about 4.1 GB for raw Parquet plus 34 GB for FastF1's cache, for all of 2022–2026 |

```bash
git clone https://github.com/shavkatjony/F1-pace-intelligence.git
cd F1-pace-intelligence
make setup          # uv sync: creates .venv from uv.lock
uv run dpec info    # prints team, seasons, mode and raw-data path
```

Check: `uv run dpec info` prints `Team: DPEC (our cars: Mercedes)` and `Mode: local`.

## 2. Data pipeline

```bash
make data           # = dpec ingest, dpec build, dpec check
```

| Step | Command | What happens | Output |
|---|---|---|---|
| Ingest **(needs data access)** | `uv run dpec ingest` | Downloads every session of every configured season not yet saved | `data/raw/fastf1/season=…/event=…/session=…/*.parquet` + `manifest.json`; a line per attempt in `data/ingest_log.csv` |
| One weekend | `uv run dpec ingest --season 2026 --round 17` | Only that round (add `--session Race` for one session, `--force` to download again) | as above |
| Build | `make build` or `uv run dpec build` | Drops and recreates every table from SQL: `sql/core`, then `sql/marts`; prints each table's row count | `data/warehouse.duckdb` |
| Check | `make check` or `uv run dpec check` | 20 SQL checks + data dictionary check; prints `PASS` or `FAIL (n rows)` with sample rows | exit code 0 only if all pass |

Expected on the saved data: `core_sessions` 545 rows, `core_laps` 297,724 rows, and `21 passed, 0 failed` (verified in [numbers-check.md](../../reports/numbers-check.md)).

The build is a full rebuild and is safe to repeat: raw files are never modified. To start over, delete `data/warehouse.duckdb` and run `make build`. **Never delete `data/raw/` or `data/cache/`**: new sessions cannot currently be downloaded again.

Ad-hoc questions: `uv run dpec sql "SELECT season, count(*) FROM core_sessions GROUP BY 1"`.

## 3. Validate data after a change

1. `make build && make check`. A failing check prints the offending rows. Fix the SQL or add an expected gap to [`seeds/known_gaps.csv`](../../seeds/known_gaps.csv) with the reason.
2. A new column must be documented in [`docs/data-dictionary.md`](../data-dictionary.md), otherwise `data_dictionary_covers_every_column` fails.
3. A new rule about the data becomes a new file in `sql/checks/` that returns the rows breaking it ([decision 0006](../decisions/0006-checks-and-id-maps.md)).

## 4. Forecast backtest and strategy replay

```bash
uv run dpec backtest      # walk-forward: every dry race from 2023, every forecaster
uv run dpec replay        # tyre and stop decision for every dry race from 2023
uv run dpec packet --season 2024 --round 1    # one race's decision packet
```

| Command | Writes | Check |
|---|---|---|
| `backtest` | `data/forecasts/backtest.parquet` (every guess, not in git); [`reports/backtest/scores.csv`](../../reports/backtest/scores.csv) and [`ranges.csv`](../../reports/backtest/ranges.csv) (in git) | test years 2025–26, after qualifying: shared model `mae_pct` 0.548, ranges `inside` 0.799 |
| `replay` | `data/forecasts/decisions.parquet`; [`reports/backtest/decisions.csv`](../../reports/backtest/decisions.csv) | all races: `stops_right` 0.577, `always_one_stop_right` 0.462 |
| `packet` | `reports/packets/<season>-<round>-<circuit>.md` | needs `backtest` first |

Options: `--first-season` (first season forecast; earlier ones only train) and `--test-from` (start of the reported test years). Settings are chosen on the tune years only ([decision 0011](../decisions/0011-target-and-fair-test.md)). If you change the model, rerun `backtest` and compare `scores.csv` on the **tune** years before looking at the test years.

## 5. Forecast freeze, scoring and dry runs

The public-record workflow ([decision 0015](../decisions/0015-public-record.md)). It is complete and tested, but has not been used live **(needs new data)**.

```bash
# After qualifying, before the deadline (race start minus 30 minutes):
make freeze ROUND=19                 # ingest, build, check, then dpec freeze
git add ledger/ && git commit -m "Freeze ..." && git push   # GitHub's push time is the proof

# After the race:
make score ROUND=19                  # ingest, build, check, then dpec score
```

- `SEASON` defaults to 2026 and `CHECKPOINT` to `after_quali` (`after_practice` freezes before qualifying).
- At a new circuit or a changed race length, pass the official length: `uv run dpec freeze --season <year> --round <n> --race-laps <official race laps>`. Otherwise there is no tyre decision, or it uses the last race's length.
- FastF1 publishes a session about three hours after it starts, so the freeze window is qualifying + 3 h to race − 30 min.

**Dry runs** use the same code on past weekends and never touch `ledger/`:

```bash
uv run dpec freeze --season 2026 --round 3 --dry-run
uv run dpec score  --season 2026 --round 3 --dry-run
uv run dpec pretend --season 2026     # every dry race of a season; compares with the backtest
```

`pretend` prints the largest difference between the frozen and backtest forecasts. It should be 0.0000% (the live path is the tested path).

**Ledger integrity:** `uv run dpec ledger` validates every file and its hash. In CI, `dpec ledger --since <before> --late-check` also fails on any changed, deleted or late file. Do not add non-JSON files (such as a README) under `ledger/`: the CI job parses every added file there.

## 6. AI assistant and its evaluation

```bash
export ANTHROPIC_API_KEY=...                       # or use --provider ollama
uv run dpec ask "Who was fastest in Bahrain 2024 qualifying?"
uv run dpec eval-ai --dry-run                      # print the computed right answers; no model call
uv run dpec eval-ai --only L01,C05,T01             # three questions (cheap smoke test)
uv run dpec eval-ai                                # all 50 questions
uv run dpec eval-ai --provider ollama              # the same exam on the local model
uv run dpec eval-report                            # every saved run side by side
```

Each run writes `reports/ai/eval-<provider>-<model>-<date>.csv` with every question, answer, tool call, time and token count. `eval-report` rewrites [`reports/ai/README.md`](../../reports/ai/README.md). The newest run is what the public copy shows in the assistant window. Reference result: 50 of 50, US$1.53 by the project's cost formula (US$1.45 to 1.67 at the published prices, [workstream 06 § 5.11](../workstreams/06-applied-ai.md#511-cost-and-latency)), 6.7 s median per question (8 November 2026). No full Ollama run has been made yet.

## 7. Tests and linting

```bash
make test       # uv run pytest -q   → 129 passed
make lint       # uv run ruff check .
make format     # uv run ruff format .
```

Tests use fake data built in the test files, so they need no raw data, internet or API key. Ruff uses a line length of 100 and skips `notebooks/`. CI ([`ci.yml`](../../.github/workflows/ci.yml)) runs `uv sync --locked`, `ruff check` and `pytest` on every push and pull request, plus the ledger guard on every push. `--locked` fails if `uv.lock` is out of date with `pyproject.toml`.

## 8. Run the app

```bash
make run        # local, full system: http://127.0.0.1:8000  (API docs: /api/docs)
make public     # the same app with config/public.yaml: what visitors see online
```

The app reads the warehouse, `data/forecasts/` and the ledger. Run `make data` and `uv run dpec backtest` first, or the forecast windows say there is nothing to show yet.

## 9. Release and deployment

The online copy is a versioned snapshot, never a live feed ([decision 0018](../decisions/0018-public-copy.md)).

**Step 1. Pack the data**

```bash
make snapshot   # dist/dpec-data-<date>.tar.gz with SHA256SUMS and manifest.json
```

**Step 2. Try the image locally (optional, needs Docker)**

```bash
make image      # snapshot → unpack into snapshot/ → docker build -t dpec-public .
make image-run  # http://localhost:7860
```

**Step 3. Publish a GitHub Release**

1. Create a release with a new tag (for example `v1.3`) on GitHub.
2. Attach the `dist/dpec-data-<date>.tar.gz` file as an asset. Upload it as is: do not open or re-save it.
3. Publish. [`release.yml`](../../.github/workflows/release.yml) then:
   - downloads the asset and unpacks it;
   - builds the image; the build runs `sha256sum -c SHA256SUMS` and stops on any mismatch;
   - starts the container and checks `/api/health` reports `"mode":"public"` and a snapshot date, the page loads, `/api/weekends` and `/api/chat/recorded` return data, and `POST /api/chat` returns 403;
   - pushes `ghcr.io/shavkatjony/f1-pace-intelligence:<tag>` and `:latest`.

**Step 4. Deploy on Render**

The free Render web service runs the public `:latest` image (Singapore region, port 7860, health check `/api/health`). Render does not redeploy when `:latest` changes: open the service and choose **Manual Deploy → Deploy latest reference**. Then open <https://f1-pace-intelligence.onrender.com> and check that the footer shows the new snapshot date.

The same image runs on any Docker host. [`deploy/huggingface/`](../../deploy/huggingface/) still works for an account with a paid Hugging Face plan.

## 10. Public versus local functionality

| Function | Local | Public copy |
|---|---|---|
| All analysis windows, forecasts, record, dry runs, race debrief | ✓ | ✓ |
| Telemetry traces, lap delta, track map, corner table, qualifying lap split | ✓ | ✗ (a picture is shown; API returns 404 with the reason) |
| Live AI questions | ✓ | ✗ (recorded exam answers are shown; API returns 403) |
| Data freshness | last `dpec build` | snapshot date in the footer |

## 11. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `dpec ingest` asks for a login or returns no data | F1 timing now needs authentication; FastF1 3.9+ needs F1TV Access, 3.8 gets nothing | Work with the saved data. To restart live data: an F1TV Access subscription or a new source such as OpenF1 ([live-weekends.md](../live-weekends.md)) |
| `FastF1 rate limit reached` | Too many requests | Run the same command later; saved sessions are skipped |
| One session `FAILED` during ingest | A source problem for that session | The rest continue; the error is in `data/ingest_log.csv`; rerun with `--season --round --session` |
| `FAIL (n rows) data_dictionary_covers_every_column` | A new warehouse column is not documented | Add it to `docs/data-dictionary.md` |
| `FAIL (n rows) no_unexpected_empty_tables` | A raw table is empty | If the source genuinely has no data, add it to `seeds/known_gaps.csv` with the reason |
| Settings error on start | A typo or out-of-range value in the YAML (unknown keys are rejected) | Fix the key named in the error |
| `uv sync --locked` fails in CI | `uv.lock` out of date | Run `uv lock` locally and commit the lock file |
| `dpec ask` fails with a provider error | No `ANTHROPIC_API_KEY`, Ollama not running, or the model not pulled | Set the key, start Ollama, or `ollama pull qwen3:8b` |
| Forecast window empty | No `data/forecasts/backtest.parquet` | `uv run dpec backtest` |
| `dpec freeze` refuses | Past the deadline (race − 30 min) | Expected: a late forecast proves nothing. Use `--dry-run` for past weekends |
| Ledger CI job fails | A ledger file was changed, deleted, arrived late, or is not valid JSON | Never edit frozen files; a score is a new file |
| Release workflow: no assets to download | The snapshot file was not attached | Published releases cannot be changed: make a new release with the file attached |
| Release workflow: checksum or unpack error | The `.tar.gz` was opened and re-saved (it must start with the gzip bytes `1f 8b`) | Upload the file from `dist/` unchanged, in a new release |
| Online copy takes about a minute to open | Render's free tier sleeps after 15 minutes without visitors | Expected |
| Online copy shows old data | Render was not redeployed | Manual Deploy → Deploy latest reference |

## See also

- [architecture.md](architecture.md) · [codebase-map.md](codebase-map.md)
- [Decision 0015: the public record](../decisions/0015-public-record.md) · [Decision 0018: the public copy](../decisions/0018-public-copy.md)
- [Research case 09: release, deployment and data access](../research/cases/09-release-deployment-data-access.md)
- [Workstream documents](../README.md#workstreams-one-discipline-at-a-time): [01 data](../workstreams/01-data-engineering.md) · [02 analytics](../workstreams/02-data-analytics-statistics.md) · [03 forecasting](../workstreams/03-forecasting-machine-learning.md) · [04 ML engineering](../workstreams/04-ml-engineering.md) · [05 backend](../workstreams/05-backend-engineering.md) · [06 applied AI](../workstreams/06-applied-ai.md)
