# F1 Pace Intelligence · Team DPEC Weekend Forecaster
 
> After each practice session, how fast will each car really be on Sunday, how sure are we, and what should the team do about its tyres and pit stops?
 
DPEC is a solo end-to-end project in data engineering, analytics, machine learning and AI, built on public Formula 1 timing data (2022–2026). It treats the project like a small race-team engineering office: one data foundation, clear rules for what counts as "real pace", forecasts saved **before** each session, and an honest score **after** the race.
 
**Status:** Phase A (data foundation) is almost done. The forecaster (Phase C) has not started yet. Everything below marked ✅ runs today.
 
![VER pole lap vs LEC's best lap, Bahrain 2024 qualifying, on a 5 m distance grid](docs/images/bahrain-pole.png)
 
*Bahrain 2024 qualifying: Verstappen's pole lap against Leclerc's best Q2 lap, aligned metre by metre. Top: speed. Bottom: the running gap. The grid reproduces the official lap times to the millisecond (89.179 s vs 89.165 s), and every corner lines up within 10 m.*
 
---
 
## What works today
 
| | Command | What it does |
|---|---|---|
| ✅ | `dpec ingest` | Downloads every session of every season in the config from FastF1, once, into immutable Parquet files with a manifest (row counts + SHA-256). Re-runs only fetch new sessions; rate limits stop cleanly and resume |
| ✅ | `dpec build` | Rebuilds the DuckDB warehouse from plain SQL files: sessions, laps with quality flags, official results, and a file inventory |
| ✅ | `dpec sql "…"` | Runs any read-only SQL query on the warehouse |
| ✅ | `dpec compare` | Puts two laps on a 5 m distance grid and shows where one gains or loses time, corner by corner |
 
### The data, in numbers
 
| | |
|---|---|
| Seasons | 2022–2026 (ground-effect era, plus the 2026 rules) |
| Sessions saved | 545 (practice, qualifying, sprint, race) |
| Laps | 297,724, of which 163,599 (55%) are clean race pace |
| Raw Parquet on disk | 4.1 GB |
| Full rebuild of the warehouse | seconds |
 
---
 
## How it works
 
```text
FastF1 (official F1 timing feed)
      │  dpec ingest: only file that talks to the internet
      ▼
data/raw/fastf1/season=…/event=…/session=…/*.parquet + manifest.json   (never edited)
      │  dpec build: plain SQL run by DuckDB
      ▼
core_sessions · core_laps · core_results · core_files      (data/warehouse.duckdb)
      │
      ├── distance grid → dpec compare               ✅
      ├── analytics: long runs, tyre stints, track evolution     (Phase B)
      ├── forecaster: one shared model for all tracks and years (Phase C)
      └── decisions, debrief, AI assistant                       (Phases C–D)
```
 
### When is a lap "real pace"?
 
Every lap gets exactly one reason code: `clean`, or the **first** rule it breaks, in this order:
 
`no_time` → `generated` → `in_lap` → `out_lap` → `lap_one` → `red_flag` → `safety_car` → `vsc` → `yellow` → `deleted` → `inaccurate` → `wet_tyre` → `slow`
 
`slow` means slower than 107% of the session's median clean lap. That limit was picked from the data: in races it flags 395 laps at 107%, but 3,445 at 103%, which would throw away the old-tyre laps the tyre model needs. Every rule is also kept as its own yes/no column, so later models can be stricter or looser.
 
### Checks that make the data trustworthy
 
- The grain is tested: one row per driver, per lap, per session, with no duplicates.
- Results add up: every race hands out 101 or 102 points (102 with the fastest-lap point until 2024) and every sprint 36.
- Penalties decided after the flag are in: for example, Russell's win at Spa 2024 shows as a disqualification.
- An empty table from FastF1 is listed, not hidden (1 of about 3,800 saved tables).
- 35 unit tests run in CI on every push; none of them need the internet.
---
 
## Design decisions
 
Short records of what was decided, why, and what was rejected: [`docs/decisions/`](docs/decisions/)
 
| # | Decision |
|---|---|
| 0001 | Team DPEC adopts Mercedes's two cars |
| 0002 | Parquet files + DuckDB, no database server |
| 0003 | Clean tables and the ordered lap rules |
| 0004 | Distance grid: computed on demand, not stored |
| 0005 | Results come from FastF1 (which already carries the official classification); no second adapter |
 
---
 
## Quick start
 
Needs [uv](https://docs.astral.sh/uv/) and Python 3.12.
 
```bash
git clone https://github.com/shavkatjony/F1-pace-intelligence.git
cd F1-pace-intelligence
make setup                 # install everything with uv
make test                  # 35 tests, no internet needed
make data                  # first run downloads 2022–2026: hours, about 40 GB of FastF1 cache
uv run dpec compare 2024_01_Q VER 16 LEC 12
```
 
Settings (seasons, our team, the slow-lap limit, the grid step, paths) live in [`config/dpec.yaml`](config/dpec.yaml). Nothing is hard-coded.
 
---
 
## Roadmap
 
| Phase | Goal | State |
|---|---|---|
| **A · Data** | One command rebuilds clean F1 data for 2022–2026 | 🔶 ingest ✅, clean laps ✅, distance grid ✅, results + download log ✅, final checks next |
| **B · History** | Every "what happened" question answered; which practice signals predict Sunday | ⬜ |
| **C · Forecast** | Race pace and tyre wear with honest ranges, saved publicly before each session, scored after | ⬜ |
| **D · Explain** | Where the time went, plus an AI race engineer that says "not public" when it doesn't know | ⬜ |
| **E · Public** | Live app and write-up | ⬜ |
 
How the forecaster will be judged: simple baselines first, walk-forward backtests (never random lap splits, which leak the future), calibrated 80% ranges, and a public record of every forecast.
 
---
 
## What public data can't tell us
 
Fuel load, car setup, tyre temperatures and pressures, and in 2026 the battery (ERS) and active-aero state are not public. Where the project estimates their effect, it is labelled **estimated**, never shown as measured.
 
---
 
## Project layout
 
```text
config/dpec.yaml              all settings
sql/core/                     the SQL that builds the warehouse
src/telemetry_core/           reusable data layer: ingestion, warehouse, alignment
src/dpec/cli.py               the dpec commands
tests/                        unit tests (fake data, no internet)
docs/decisions/               decision records
web/prototype/                look-only prototype of the pit-wall app
```
 
---
 
**Author:** Shavkatjon Yuldashev · Data Science, ML, Analytics and AI Engineering · Korea
 
 