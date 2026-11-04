# F1 Pace Intelligence · Team DPEC Weekend Forecaster

> Before each Formula 1 race, how fast will each car really be, how sure are we, and what should the team do about tyres and pit stops? Then, after the race: were we right, and where did the time go?

**Live, read-only:** https://<my-hf-name soon >-dpec-pit-wall.hf.space · **3-minute video:** <my video link> · **한국어 요약:** [mydocs/summary-ko.md](docs/summary-ko.md) · **The method, in full:** [docs/methods.md](docs/methods.md)

DPEC is a solo end-to-end project in data engineering, analytics, machine learning and AI, built on public Formula 1 timing data (2022–2026). It works like a small race-team engineering office for one adopted team (Mercedes's two cars): one trusted data foundation, forecasts made only with what was known at the time, **forecasts frozen in public before each race and scored after it**, a debrief of where the time went, and an AI race engineer that answers from the data or says "not public".

![The forecast window: race pace forecast for Bahrain 2024 after qualifying, with 80% ranges and what happened](docs/images/race-pace-forecast.png)

*Bahrain 2024 as the model saw it after qualifying, before the race. For each car: the race pace forecast (○, % behind the fastest car), its 80% range (bar) and what happened (◆). Hamilton: forecast +0.69%, range +0.01% to +1.37%, real +1.21%. Made by the same walk-forward test as every number below: only races before this one.*

---

## Results

### 1. Race pace forecasts beat every simple guess, on years never used to build them

Walk-forward backtest: before each race weekend from 2023 on, the model is refitted on earlier races only, then forecasts that weekend after practice and after qualifying. Settings were chosen on 2023–24; results are reported on **2025–26** (37 weekends, 726 driver-races), never used to choose anything. Race pace = a driver's median clean race lap, as % behind the fastest car that day.

| Forecaster | After practice | After qualifying |
|---|---|---|
| **Shared model** (one regression for every track and year) | **0.648%** (0.58 s a lap) | **0.548%** (0.49 s a lap) |
| Team form (the team's recent races) | 0.674% | 0.674% |
| Per-year model | 0.883% | 0.589% |
| The signal as is (long runs / qualifying gap) | 1.071% | 0.594% |
| No signal (everyone equal) | 1.047% | 1.047% |

- **Honest ranges:** 78.5% (after practice) and 79.9% (after qualifying) of real race paces landed inside the 80% ranges.
- **Honest chances:** chances of a top-3 race pace score 0.077 on the Brier score after qualifying, against 0.132 with no information.
- **Where it doesn't win:** the per-year model orders drivers slightly better after qualifying (Spearman 0.843 vs 0.821), and after the 2026 rules change simple guesses did as well for the first ~5 races.

### 2. From forecast to a decision you can check

For each dry race: tyre wear from practice, the pit-stop cost at this circuit, and 1, 2 and 3 stops costed over 4,000 replays. If no plan wins at least 65% of the replays, the packet says **"no clear decision"**. Replayed on all 78 dry races since 2023: the stop call matched the top 10 in **58%** of races, against 46% for "always one stop" (67% vs 57% when the call was clear). Scored on what can be checked (wear, stops, real first stops inside the window), never on "did the plan win".

### 3. In public: frozen before the race, scored after

After qualifying, `dpec freeze` writes every car's forecast, range, chances and the tyre decision into [`ledger/`](ledger/), with the SHA-256 of its own content, and I push it before the deadline (30 minutes before the race). A CI job fails if a forecast reached GitHub late, or if any frozen file is ever changed. After the race, `dpec score` adds a separate score file.

- **Dress rehearsal:** the live code, run on 2026 rounds 1–17 as dry runs: error 0.573%, exactly the backtest's 0.573% (so the live path is the tested path), 81% inside the 80% ranges, better than team form on 14 of 16 weekends.
- **Live weekends:** <number> weekends frozen before the race so far; log in [docs/live-weekends.md](docs/live-weekends.md).

### 4. Where the time went

![The debrief window: lap gap by kind of track part, and the race gap split into pace, tyres and traffic](docs/images/debrief.png)

Qualifying: our drivers' best laps against the fastest, on a 5 m grid, every metre's gap assigned to a kind of track part (braking, straight, traction, slow, medium or fast corner); the parts add up to the lap gap exactly. Race: the gap split by a regression on paired laps into pace, tyre age, compound and traffic, with bootstrap ranges. Singapore 2026: Russell was 1.49 s a lap off the leader's pace, about 0.9 s of it pace and about 0.5 s traffic (he started 19th and spent 76% of his clean laps in traffic).

### 5. An AI race engineer with an exam

An LLM agent with eight **read-only tools** (a guarded SQL tool, the lap and race splits, the forecasts, the tyre decision, the public record) answers questions about any session since 2022. Every number names the tool it came from; fuel, setups or ERS get "not public". A 50-question exam, whose right answers are computed from the warehouse each run, grades it automatically: Claude passed **<overall>%** with **<traps> of 5** traps refused, at about $<cost> a run. Results: [`reports/ai/`](reports/ai/README.md).

---

## Try it

**Online:** https://<your-hf-name>-dpec-pit-wall.hf.space (read-only; it may take a minute to wake up). Telemetry traces and the race engineer run only on the local app.

![The public copy of the pit wall](docs/images/public-copy.png)

**On your machine** (needs [uv](https://docs.astral.sh/uv/) and Python 3.12):
```bash
git clone https://github.com/shavkatjony/F1-pace-intelligence.git
cd F1-pace-intelligence
make setup                 # install everything with uv
make test                  # 127 tests, no internet needed
make data                  # download, build, check. First run: hours, about 40 GB of FastF1 cache
uv run dpec backtest       # forecast and score every past dry race
uv run dpec replay         # replay every past tyre and stop decision
make run                   # the pit wall app: http://127.0.0.1:8000
```
Settings live in [`config/dpec.yaml`](config/dpec.yaml); nothing is hard-coded.

---

## How it works

```text
FastF1 (official F1 timing feed)
      │  dpec ingest: the only part that talks to the internet
      ▼
data/raw/…/*.parquet + manifest.json                         (never edited, SHA-256 per file)
      │  dpec build: plain SQL run by DuckDB
      ▼
core tables → answer tables (weekends, weather, pace, stints, long runs, track evolution,
              weekend signals, race strategy)                (data/warehouse.duckdb)
      │  dpec check: 21 data checks + the data dictionary
      │
      ├── forecasting/  baselines → shared model → ranges → chances      dpec backtest
      ├── decisions/    tyre wear → pit loss → stop plans → packet        dpec replay, dpec packet
      ├── record/       freeze before the race → score after → ledger/    dpec freeze, dpec score
      ├── debrief/      lap gap by track part, race gap by cause          dpec debrief
      ├── assistant/    8 read-only tools → Claude or Ollama → exam       dpec ask, dpec eval-ai
      ├── api/ + web/   read-only API → pit wall app (linked windows)     make run
      └── publish/      data snapshot → GitHub release → Docker image → Hugging Face Space
```

| Command | What it does |
|---|---|
| `dpec ingest` · `build` · `check` | Download once, rebuild the warehouse from SQL, run every data check |
| `dpec backtest` · `replay` · `packet` | Walk-forward forecasts and scores; tyre and stop decisions; one race's decision packet |
| `dpec freeze` · `score` · `ledger` | The public record: freeze before the race, score after, verify every frozen file |
| `dpec debrief` | Where our cars' time went, in qualifying and in the race |
| `dpec ask` · `eval-ai` · `eval-report` | The race engineer, and its exam |
| `dpec snapshot` · `make public` | Pack the data for the public copy; run the public copy locally |

### The data, in numbers

| | |
|---|---|
| Seasons | 2022–2026 (ground-effect era, plus the 2026 rules) |
| Sessions | 545 by October 2026, plus each new weekend |
| Laps | 297,724, of which 55% are clean race pace (78% in races, 27% in qualifying) |
| Data checks | 21, all passing on every rebuild |
| Tests | 127, run in CI on every push, no internet and no API key needed |

### Messy data, found and handled

- Every lap gets exactly one reason code: `clean`, or the **first** rule it breaks, in a fixed order (`no_time` → `generated` → `in_lap` → `out_lap` → `lap_one` → `red_flag` → `safety_car` → `vsc` → `yellow` → `deleted` → `inaccurate` → `wet_tyre` → `slow`). Wet races are caught automatically (Japan 2022 and São Paulo 2024: no clean laps).
- Gaps in the official feed, fixed from the data: sprint-qualifying results with no driver IDs, 2026 practice sessions with no team names, teams renamed across years (an ID map).
- A track temperature sensor dropping out: 47 readings of exactly 0 °C in 14 sessions, now treated as missing.
- Results add up: 101 or 102 points per race, 36 per sprint, disqualifications after the flag included.
- A race whose length changed (Montreal 2026: 68 laps, 70 before) and a new circuit (Madrid's Madring, 2026): the live path takes the official length as an input instead of guessing.

---

## Design decisions

Short records of what was decided, why, and what was rejected: [`docs/decisions/`](docs/decisions/)

| # | Decision |
|---|---|
| 0001 | Team DPEC adopts Mercedes's two cars |
| 0002 | Parquet files + DuckDB, no database server |
| 0003 | Clean tables and the ordered lap rules |
| 0004 | Distance grid: computed on demand, not stored |
| 0005 | Results come from FastF1; no second adapter |
| 0006 | Data checks as SQL that return bad rows; driver and team ID maps |
| 0007 | Answer tables in plain SQL; pace in % of the session's best; weather dropouts as missing |
| 0008 | Tyre stints, practice long runs, and an explicit fuel-burn correction |
| 0009 | Track evolution measured within each driver; wet sessions flagged, not deleted |
| 0010 | Which signals the forecaster starts with |
| 0011 | What the forecaster predicts, and how it's tested (walk-forward, five baselines) |
| 0012 | One shared model for every track and year |
| 0013 | Ranges and chances from the model's own past errors |
| 0014 | Tyre and stop decisions, and the decision packet |
| 0015 | The public record: frozen before the race, scored after |
| 0016 | The debrief: where our cars' time went |
| 0017 | The race engineer: one model, read-only tools, and an exam |
| 0018 | The public copy: what's online, how it gets there, where it runs |

The whole forecaster on one page: [model card](docs/model-card.md). Every table and column: [data dictionary](docs/data-dictionary.md).

---

## Roadmap

| Phase | Goal | State |
|---|---|---|
| **A · Data** | One command rebuilds clean F1 data for 2022–2026 | ✅ |
| **B · History** | Every "what happened" question answered; which practice signals predict Sunday; the pit wall app | ✅ |
| **C · Forecast** | Race pace and tyre wear with honest ranges and decisions; frozen in public before each race, scored after | ✅ live from <first live round> |
| **D · Explain** | Where the time went; an AI race engineer with a measured pass rate | ✅ |
| **E · Public** | Live app and write-up | ✅ |
| Later | Why one car can't match another (a car root-cause module); the starting grid after penalties as a forecast input | ⬜ |

---

## What public data can't tell us

Fuel load, car setup, tyre temperatures and pressures, engine modes, and in 2026 the battery (ERS) and active-aero state are not public. Where the project estimates their effect, it says **estimated**; where it can't, the race engineer says **not public**.

---

## Project layout

```text
config/                       all settings (dpec.yaml local, public.yaml for the online copy)
sql/core/ · sql/marts/        the SQL that builds the warehouse and the answer tables
sql/checks/                   data checks: each returns the rows that break a rule
src/telemetry_core/           reusable data layer: ingestion, warehouse, alignment
src/dpec/forecasting/         baselines, shared model, backtest, ranges, chances
src/dpec/decisions/           tyre wear, stop plans, replay, decision packet
src/dpec/record/              freeze, score, the ledger guard
src/dpec/debrief/             lap gap by track part, race gap by cause
src/dpec/assistant/           the race engineer's tools, providers and exam
src/dpec/api/ · web/app/      the read-only API and the pit wall app
src/dpec/publish/             the data snapshot for the public copy
ledger/                       forecasts frozen before each race, and their scores (never edited)
evals/ · reports/ai/          the 50-question exam and every run's results
docs/                         decisions, model card, data dictionary, method, live weekends log
Dockerfile · deploy/          the public image and the Hugging Face Space
tests/                        unit tests (fake data, no internet)
```

---

**Author:** Shavkatjon Yuldashev · Data Science, ML, Analytics and AI Engineering · Korea · [GitHub](https://github.com/shavkatjony)