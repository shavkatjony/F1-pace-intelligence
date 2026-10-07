# 01 · Master Roadmap

> **Short version:** Build in 9 stages. Each stage ends with a test you can run, and the next stage starts only after that test passes. The first 4 stages build the foundation and the basics. Stages 5–7 are the real work: the forecaster, the ledger and the debrief. Stages 8–9 add the AI and make it public.

Priority tags: **NOW** (start here) · **SOON** · **LATER**.

---

## The whole project on one page

```
 STAGE 0  Skeleton            repo, CI, rules, decisions            NOW
 STAGE 1  Telemetry Core       sources → canonical tables            NOW
 STAGE 2  Quality & alignment  flags, clean laps, distance grid      NOW
 STAGE 3  Analytics marts      all the basics, as clean tables       SOON
 STAGE 4  App shell            linked windows reading the marts      SOON
 ───────────────────────────── the foundation is done ─────────────
 STAGE 5  Forecaster           practice → quali → race pace          SOON   ★ core
 STAGE 6  Ledger & scoring     freeze before, score after            SOON   ★ core
 STAGE 7  Attribution debrief  where the time went                   LATER  ★
 STAGE 8  AI layer             race engineer + strategist            LATER
 STAGE 9  Go public            deploy, weekly runs, write-up         LATER
```

Dependencies: 1 → 2 → 3 → (4 and 5 in parallel) → 6 → 7 → 8 → 9.
Stage 4 only needs the marts from stage 3, so app work (mostly AI-built) can run beside your model work in stage 5.

---

## Stage by stage

### Stage 0 · Skeleton (NOW) · file 02, 12
**Steps**
1. Create the GitHub repo and connect it 
2. Python project with `uv`, `src/` layout, ruff, pytest, pre-commit.
3. GitHub Actions: lint + tests on every push.
5. `config/dpec.yaml` with the team name, adopted team (D2), seasons and paths.

**Exit test:** a fresh clone runs `make test` green locally and in CI.

### Stage 1 · Telemetry Core (NOW) · files 03, 04
**Steps**
1. FastF1 adapter for one race weekend (all sessions).
2. Jolpica adapter for results, standings and calendar.
3. Write raw data to Parquet (untouched).
4. Build the canonical tables in DuckDB via dbt (staging → core).
5. Widen to 2022–2026.

**Exit test:** `make data` rebuilds every season from scratch; row counts match the sources; a different person could read the data dictionary and know what each column means.

### Stage 2 · Quality & alignment (NOW) · file 05
**Steps**
1. Track-status flags (SC/VSC/red/yellow) on every lap.
2. Pit in/out, deleted laps, outliers, traffic flags.
3. A quality score per session plus a quality report.
4. A distance grid: every lap resampled to fixed steps along a reference lap.
5. Tests on known tricky sessions (wet race, red-flag race).

**Exit test:** for any session, `is_clean_lap` and the quality report match what you see when you check by hand on 3 known messy races.

### Stage 3 · Analytics marts (SOON) · file 06
**Steps**
1. Session overview, results, standings, calendar marts
2. Lap and sector comparison, speed traps, telemetry overlays.
3. Corner analysis, tyre stints, track evolution, weather context.
4. Strategy history (actual pit stops, stint lengths).
5. **Long-run pace mart** : the bridge into the forecaster.

**Exit test:** every question in file 06's question list is answered by one SQL query against a mart.

### Stage 4 · App shell (SOON) · file 11
**Steps**
1. FastAPI read-only API over the marts.
2. Web app with a workspace of linked windows and a shared context (event, session, drivers, lap, cursor).
3. Layout presets and saved settings.
4. Pop-out windows that stay in sync across monitors.

**Exit test:** open 3 windows on 2 monitors; changing the driver in one changes all three.

### Stage 5 · Forecaster ( the core) · file 07
**Steps**
1. Baselines (previous race pace, practice best, team median).
2. Long-run pace model with fuel/programme correction.
3. Qualifying-pace and race-pace forecasts with intervals.
4. Cross-circuit transfer features (circuit types, similarity).
5. In-season updating for 2026-style rule changes.
6. Backtest walk-forward over 2022–2026.

**Exit test:** a walk-forward backtest table where the model beats every baseline on held-out weekends, and its 80% intervals cover between 75% and 85% of outcomes. If it doesn't, the report says so honestly and stage 5 iterates.

### Stage 6 · Ledger & scoring (SOON, core) · file 08
**Steps**
1. Ledger format and the freeze-before-session job.
2. Automatic scoring after each session.
3. Season scoreboard (error, coverage, calibration, versus baselines).
4. First live forecasts on the remaining 2026 races.

**Exit test:** at least one real weekend forecast, committed before the session (the git timestamp proves it) and scored automatically afterwards.

### Stage 7 · Attribution debrief () · file 09
**Steps**
1. Teammate gap decomposition (same car).
2. Gap to rival split into straight-line, braking, corner-speed and traction parts.
3. Traffic and track-evolution adjustments.
4. Weekend debrief report.

**Exit test:** for one weekend, the parts of the gap add up to the total gap within a stated tolerance, with uncertainty.

### Stage 8 · AI layer (LATER) · file 10
**Steps**
1. Tools over the marts, forecasts and ledger (read-only).
2. Race-engineer assistant, then strategy assistant.
3. Router on top of them (two layers).
4. Eval set, about 50 questions with known answers.
5. Ollama fallback for offline use.

**Exit test:** the eval score is reported in the README, and on every "hidden variable" question the assistant answers "not public" instead of inventing a value.

### Stage 9 · Go public (LATER) · file 12
**Steps**
1. Deploy the read-only online version.
2. Scheduled job after each session: ingest → forecast → freeze → score.
3. README leading with the scoreboard, plus a 3-minute demo video and a write-up.
4. Optional Korean summary for Korean employers.

**Exit test:** a stranger can open the public link, see the season scoreboard, and verify a forecast's timestamp on GitHub in under 2 minutes.

---

## What you'll be able to say in an interview, per stage

| Stage | Evidence |
|---|---|
| 1–2 | "I designed a source-independent telemetry schema with data-quality flags and rebuilt it reproducibly." |
| 3 | "I modelled the data at the right grain and answered real questions in SQL." |
| 5 | "I built forecasts that beat baselines on held-out race weekends, with calibrated intervals, under a regulation change." |
| 6 | "Every forecast was public before the session. Here's the scoreboard." |
| 7 | "I split the time gaps between drivers into their causes, with uncertainty." |
