# 00 · Rules and Purpose (read this first)

> **Short version:** Team DPEC is a race-weekend forecasting system built on real F1 data. It forecasts pace from practice telemetry, publishes every forecast before the session, and scores itself after the race. Every other file in this plan follows the rules on this page. If a file disagrees with this page, this page wins.

Version: plan v4 · 2026-10-05 · owner: SHAVKATJON

---

## 1. Purpose

**One sentence:** *Team DPEC's performance and strategy department needs to know, after every session of a race weekend, how fast each car will really be on Sunday, how sure we are, and why.*

**Why this project exists (for you):** to be the single flagship that proves data analytics, data science, ML and AI-engineering skill at software-engineering quality, for DS/DA/ML jobs in Korea.

**What makes it different:** it forecasts **pace from telemetry** (not winners from tables), on **live seasons**, with **calibrated uncertainty**, and keeps a **public record that cannot be edited afterwards**.

---

## 2. The plan files

| File | Part | One-line summary |
|---|---|---|
| 00 | Rules and purpose | This page. Rules, constraints, decisions. |
| 01 | Master roadmap | The whole project, step by step, in order, with exit tests. |
| 02 | Architecture | How the pieces fit; repo layout; local vs online; plug-in design. |
| 03 | Data sources & ingestion | Where data comes from and how it gets in automatically. |
| 04 | Telemetry Core schema | The canonical tables every other part reads. |
| 05 | Data quality & alignment | Checks, flags, and putting laps on a common distance axis. |
| 06 | Analytics layer | **All the basics** (overview, comparison, tyres, strategy history…) as clean data marts. |
| 07 | Forecasting models | **The core.** Practice → qualifying → race pace forecasts. |
| 08 | Forecast ledger & evaluation | Publishing forecasts before sessions and scoring them after. |
| 09 | Attribution debrief | Where the time went: driver, car, tyre, traffic, track. |
| 10 | AI layer | Race-engineer and strategy assistants (API vs Ollama, multi-layer). |
| 11 | App workspace & windows | Multi-window, multi-monitor, linked views, settings. |
| 12 | Engineering ops & deployment | Tests, CI, tracking, scheduling, local + online running. |
| 13 | Future scenarios | How car root-cause analysis and other ideas plug in later. |

Every part file has the same shape:
1. **Short version** (2–3 lines).
2. **Overview steps** (the 5–10 step list).
3. **Detailed side** (how and why).
4. **Who builds what** (you vs AI).
5. **Exit test** (when this part is done).

---

## 3. Rules (apply everywhere)

### Data rules
1. **Real historical data only.** No live paid feed. A race becomes "historical" minutes after it ends.
2. **Never invent hidden values.** Fuel load, setup, tyre temperatures, ERS state and active-aero state are **not public**. (FastF1 maintainer, 14 Mar 2026: F1 removed active-aero and ERS state from the public feed.) They can be *estimated* and labelled as estimated, never presented as measured.
3. **Every column is tagged** `observed`, `derived`, `estimated` or `unknown`.
4. **Raw data is never edited.** Cleaning happens in later layers; raw stays as it arrived, so everything can be rebuilt.
5. **Rebuildable from zero** with one command.

### Modelling rules
6. **Simplest method that answers the question correctly.** ML only where prediction is the goal.
7. **Baseline first.** No model is reported without a naive baseline beside it.
8. **No leakage.** Split by race weekend and forward in time. Never random-split laps.
9. **Every forecast has an uncertainty range**, and the ranges are checked for calibration.
10. **Forecasts are frozen before the session they predict.** Ledger entries are append-only.
11. **Honest results.** A model that loses to the baseline gets reported as losing.

### Engineering rules
12. **Reusable core.** The Telemetry Core (files 03–05) must not import anything F1-app-specific, so it can serve other telemetry projects.
13. **Plug-in modules.** Forecasting, attribution and future scenarios are modules that read the core and write their own tables. Adding one never requires changing another.
14. **Same code locally and online.** Online is the local system in "read-only, precomputed" mode.
15. **Tested and typed.** pytest, type hints, linting, CI on every push.
16. **Decisions are written down** as short decision records (`docs/decisions/`).

### Effort rules (your time)
17. **AI builds the plumbing**: adapters, ingestion jobs, infra, frontend scaffolding, basic charts.
18. **You build the thinking**: schema decisions, quality rules, alignment, every model, every evaluation, every SQL mart that answers a question.
19. **Every part has an exit test.** When it passes, move on. No polishing beyond it.

### Scope rules
20. **Out of scope now:** live timing, news, 3D/animated cars, deep learning on race results, physics simulators, car-engineering root-cause analysis (planned as a LATER scenario in file 13).

---

## 4. Decisions

| # | Decision | Status |
|---|---|---|
| D1 | Scenario C, Weekend Forecaster, with attribution as the debrief | ✅ **Locked** 2026-10-05 |
| D1b | Include all basic analytics (from the F1 Pit Wall repo) as data marts feeding the forecaster | ✅ **Locked** 2026-10-05 (your message) |
| D2 | DPEC adopts one real team's two cars as "our cars"; the rest are rivals | ⚙️ **Default.** Which team is your pick; the code takes it as a config value, so it can change any time |
| D3 | First live forecasts on the remaining 2026 races; full 2027 season as the main track record | ⚙️ Default |
| D4 | Training data 2022–2025 (ground-effect era) + 2026 for adaptation | ⚙️ Default |
| D5 | AI builds plumbing, you build models/evaluation/schema (rules 17–18) | ⚙️ Default |
| D6 | Visual styling designed in a separate thread; retro race-programme direction from v2 is the starting point | ⚙️ Default |
| D7 | AI layer: Claude API by default, Ollama as local/offline fallback, two-layer design (file 10) | ⚙️ Default |
| D8 | App: web app with linked multi-window workspace; same app local and online (file 11) | ⚙️ Default |
| D9 | Storage: Parquet + DuckDB + dbt (file 04) | ⚙️ Default |

To change a default, say so in the thread. The plan files will be updated in place.

---

## 5. Glossary (short)

- **Session:** FP1/FP2/FP3, Sprint Qualifying, Sprint, Qualifying, Race.
- **Stint:** continuous laps on one set of tyres.
- **Long run:** a practice stint of many laps at race-like pace; the main input for race forecasts.
- **Grain:** what one row of a table means (e.g., one lap of one driver).
- **Ledger:** the append-only file of forecasts, each committed before its session.
- **Calibration:** do 80% intervals contain the truth about 80% of the time?
- **Mart:** a clean, query-ready table built for a specific question.
