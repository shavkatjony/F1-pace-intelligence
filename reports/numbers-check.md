# Numbers check

Date: 2026-11-08 · Every number shown in the README, recomputed from the data and compared with
what the README says. Data: the warehouse (545 sessions, up to the 2026 Singapore Grand Prix),
the saved backtest forecasts and tyre decisions, the 2026 dry runs, and the newest exam run.

**Result: every number matches, after three corrections (below). Two numbers need the 4 GB of
raw files, so they were not recomputed here; how to check them is at the end.**

## Corrections made

| Where | Was | Now | Why |
|---|---|---|---|
| README, method, model card, decision 0013 | top-3 Brier 0.077 against 0.132, in a section about 2025–26 | 0.070 against 0.129 on 2025–26 (0.077 against 0.131 over 2023–26) | 0.077 is the score over all forecast years, not the test years; no information is 0.1315, which rounds to 0.131 |
| README | "21 data checks + the data dictionary" | 20 data checks + the data dictionary check (21 in all) | `dpec check` runs 20 SQL checks and 1 dictionary check |
| README, method | 127 tests | 129 tests | the tests added on 8 November |

## At a glance and results

| Number | Source | Check | Result |
|---|---|---|---|
| 545 sessions, 297,724 laps | `core_sessions`, `core_laps` | row counts | ✓ 545 · 297,724 |
| Data up to the Singapore GP, 11 October 2026 | `core_sessions` | last `session_date_utc` | ✓ 2026-10-11 |
| Error after practice / qualifying, 2025–26: shared model 0.648% / 0.548% (0.58 / 0.49 s); team form 0.674%; last race 0.744%; per-year 0.883% / 0.589%; signal as is 1.071% / 0.594%; no signal 1.047% | `data/forecasts/backtest.parquet`, [`backtest/scores.csv`](backtest/scores.csv) | mean absolute error on the test years (37 weekends, 726 rows per checkpoint); seconds on a 90 s lap | ✓ all 12 values |
| 78.5% / 79.9% inside the 80% ranges | `backtest.parquet`, [`backtest/ranges.csv`](backtest/ranges.csv) | share of real paces between low and high, shared model, test years | ✓ 0.785 · 0.799 |
| Top-3 Brier 0.070, no information 0.129 | `backtest.parquet` | (chance − happened)², after qualifying, test years; no information = 3 / drivers | ✓ 0.0697 · 0.1294 (corrected, see above) |
| Spearman 0.843 (per-year) against 0.821 (shared), after qualifying | `backtest.parquet` | median per-weekend Spearman, test years | ✓ |
| 2026 rules, first 5 races: simpler methods as good or better | `backtest.parquet` | error, 2026 rounds 1–5: after qualifying shared 0.626% vs per-year 0.570% and signal as is 0.579%; after practice shared 0.838% vs last race 0.794% and team form 0.803% | ✓ |
| Stop call right in 58% of 78 races against 46%; 67% against 57% when clear | `data/forecasts/decisions.parquet`, [`backtest/decisions.csv`](backtest/decisions.csv) | `dpec replay` | ✓ 0.577 · 0.462 · 0.667 · 0.569 |
| Dry runs: error 0.573% (backtest 0.573%), 81% inside, better than team form on 14 of 16 | the 2026 dry runs (`reports/pretend-ledger/2026-after_quali.csv`) | error weighted by drivers; skill above 0 | ✓ 0.5735 · 0.807 · 14 |
| 0 live weekends | `ledger/` | frozen forecast files | ✓ none |
| Exam: 50 of 50 (18, 12, 8, 7, 5), $1.53, median 7 s | [`ai/eval-claude-claude-opus-5-5-2026-11-08.csv`](ai/eval-claude-claude-opus-5-5-2026-11-08.csv), [`ai/README.md`](ai/README.md) | passed per kind; cost from `dpec eval-report` | ✓ 6.7 s median |
| 21 data checks | `uv run dpec check` | on the warehouse | ✓ 21 passed, 0 failed |
| 129 tests | `uv run pytest` | | ✓ 129 passed |

## The pictures and examples

| Number | Source | Result |
|---|---|---|
| Bahrain 2024, Hamilton after qualifying: forecast +0.69%, range +0.01% to +1.37%, real +1.21% | `backtest.parquet` | ✓ 0.688 · 0.006 to 1.370 · 1.211 |
| Singapore 2026, Russell: 1.49 s a lap off the leader (Leclerc), about 0.9 s pace and 0.5 s traffic, qualified 6th, started 19th, 76% of clean laps in traffic | `dpec.debrief` race part on `core_laps`; `core_results` | ✓ 1.492 · 0.936 · 0.262 + 0.223 · 6th · 19th · 75.5% |
| Singapore 2026, Russell's forecast miss +0.93% | `backtest.parquet` | ✓ 1.552 − 0.619 |
| Bahrain 2024, the packet's call: 1 stop, best in 74% of replays; real wear 0.100 s a lap | the exam's answer D01, from the tyre_decision tool | ✓ 0.739 · 0.0995 |

## Messy data

| Number | Source | Result |
|---|---|---|
| 55% of laps clean, 78% in races, 27% in qualifying | `core_laps` | ✓ 54.9% · 78.2% · 26.7% |
| Japan 2022 and São Paulo 2024: no clean race laps | `core_laps` | ✓ 0 of 507 · 0 of 1,134 |
| 54,295 weather readings | `mart_session_weather` | ✓ sum of `n_samples` |
| 101 or 102 points per race, 36 per sprint; 2,212 race and 552 sprint rows, all with points | `core_results` | ✓ |
| Montreal 2026: 68 laps, 70 before | `core_laps` | ✓ 70 in 2022–25, 68 in 2026 |
| Madring, a new circuit in 2026 | `core_sessions` | ✓ round 14, the Spanish Grand Prix |

## Not recomputed here (they need the raw files on the Mac)

- **47 track temperatures of exactly 0 °C, in 14 sessions.** The total (54,295) is checked
  above; the zeros are turned into missing values when the warehouse is built, so only the raw
  weather files can count them. On the Mac:
  ```bash
  uv run python -c "import duckdb; print(duckdb.sql(\"SELECT count(*) FILTER (WHERE TrackTemp = 0) AS zeros, count(DISTINCT CASE WHEN TrackTemp = 0 THEN concat(season, '/', event, '/', session) END) AS sessions, count(*) AS readings FROM read_parquet('data/raw/fastf1/*/*/*/weather.parquet', hive_partitioning = true, union_by_name = true)\").fetchall())"
  ```
- **Bahrain 2024 qualifying, Russell against Leclerc, split by track part** (the method's
  example: straights +0.257 s, corner exits +0.245 s, slow corners −0.195 s). The total gap,
  0.320 s, is checked here (Leclerc 1:29.165, Russell 1:29.485, best clean laps); the split
  needs the telemetry. On the Mac: `uv run dpec debrief --season 2024 --round 1`.
