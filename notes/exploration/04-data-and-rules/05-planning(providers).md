# 01 · Data providers: 

> **Short version:** We don't download "all F1 data". We download only the seasons we need (2022–2026), **once**, by asking each provider's API session by session, and save it as files on your Mac. After that we work from our own files, never from the internet. FastF1 is the only big source. Jolpica (results, standings, calendar) is tiny. OpenF1 is **not downloaded at all**: we only ask it about one specific number when a FastF1 value looks wrong. Each source gets its own small "adapter", and one ID table joins them.

---

## 1. API or download? Both, and here's why

- An **API** is a web address you ask for a piece of data, and it answers. Nobody offers "one big zip of all F1". So *downloading* means *asking the API many times*, one session at a time.
- **FastF1** is not a website. It's a Python library that does the asking for you, and keeps a **cache** (a local copy) so the same session is never downloaded twice.
- So our plan is: **ask once → save to disk → use forever.**
- **History** (past seasons) is downloaded **once**, because models learn from past races.
- **After that, one new session at a time:** when a session ends, only that session is downloaded (about 20–30 MB as Parquet).

```
Internet (APIs)          Your Mac
──────────────           ─────────────────────────────────────
FastF1  ─┐
Jolpica ─┼─ adapters ──▶ data/raw/   (files, never edited)
OpenF1  ─┘                   │
                             ▼
                     DuckDB (one database file) ──▶ your analysis, models, app
```

---

## 2. The three providers

| | **FastF1** | **Jolpica** | **OpenF1** |
|---|---|---|---|
| What it is | Python library | Web API (JSON) | Web API (JSON or CSV) |
| Where the data comes from | F1's official live-timing feed (the same data behind the TV graphics) | A community database of results. It replaced "Ergast", which shut down | Also F1's live-timing feed |
| What it gives | laps, sector times, tyres and stints, car telemetry, car position on track, weather, race-control messages, track status | results, grid, qualifying, standings, pit stops, calendar, drivers, teams | similar to FastF1, plus intervals and team radio |
| Years | telemetry from 2018 | 1950 to now | free history from 2023 |
| Size | **big** (telemetry) | tiny (KB per race) | **nothing stored** by default |
| Our use | **main source** | results, standings, calendar | asked about one number when a FastF1 value looks wrong |
| When | **NOW** (Lesson 1) | SOON (step A5) | LATER, only if a check finds a gap |

**Why OpenF1 is "backup only":** it reads the same official feed as FastF1, so most numbers are the same. Using both everywhere doubles the work for almost no new information. So we don't download it. We **ask it** about one specific value when FastF1 looks wrong, like a second opinion, and only add an adapter if a check finds a real gap.

**Why Jolpica matters:** final results include penalties applied after the race (e.g. +5 seconds). The timing feed shows the on-track order; Jolpica shows the official result. **Update (Lesson 6):** FastF1 already fetches Jolpica's official results and saves them in `results.parquet`, so we don't need our own Jolpica adapter. We add one only if a check finds missing results, or later for championship standings.

---

## 3. How big is it?

Rows per session (estimate), and the size you **measured** in Lesson 1:

| Piece | Rows per race session (about) | Why |
|---|---|---|
| Laps | ~1,100 | 20 drivers × ~57 laps |
| Car telemetry | ~400,000 | ~4 samples per second × 20 cars × ~1.5 hours |
| Car position on track | similar to telemetry | x, y, z coordinates over time |
| Weather | ~150 | one row per minute |
| Results (Jolpica) | 20 | one row per driver |

- One weekend ≈ 5 sessions. One season ≈ 24 weekends. 2022–2026 ≈ 600 sessions.
- **Measured (Lesson 1):** one race in FastF1's cache ≈ **100 MB** (80 MB files + 20 MB sqlite). Practice and qualifying are smaller.
- Our own Parquet copy (`data/raw`) is much smaller than the cache; Lesson 3 measures it. The cache is only FastF1's working copy, and it can be deleted after ingest, because `data/raw` holds everything we need.
- So all of 2022–2026 is tens of GB of cache at most, and much less as Parquet. That fits on a laptop. No server, no cloud database needed.
- Check your Mac's free disk space before the full download (step A5). If space is tight, start with 2024–2026 only.
- Telemetry is 99% of the size. Laps, results and weather are tiny.

**Rule of thumb:** most questions use **laps** (small). Only alignment and corner-by-corner comparisons need **telemetry** (big). So most of your daily work is on small tables.

---

## 4. How we manage 3 different providers (the 4 layers)

Each provider names things differently. Example: the same driver is

| Source | How it names him |
|---|---|
| FastF1 | `VER` (three letters) and car number |
| Jolpica | `max_verstappen` |
| OpenF1 | car number |

And car numbers can change between seasons. So we never join on these directly. We do this instead:

| Layer | What happens | Example |
|---|---|---|
| **1. Raw** | Each adapter saves its data exactly as it came, in its own folder. Never edited | `data/raw/fastf1/season=2024/event=01_bahrain_grand_prix/session=race/laps.parquet` |
| **2. Staging** | Same column names, same units, our own IDs | `LapTime` (timedelta) → `lap_time_s` (seconds, a number) |
| **3. Core** | One set of main tables every other part uses | `core_laps`, `core_stints`, `core_results` |
| **4. Marts** | Small tables that each answer one question | `mart_long_runs`, `mart_tyre_stints` |

The ID map (made in staging) looks like this:

| driver_id (ours) | fastf1_code | jolpica_id | season | car_number |
|---|---|---|---|---|
| `verstappen` | VER | max_verstappen | 2024 | 1 |

Everything after staging uses only `driver_id`. Same idea for teams, events and sessions.

**Four rules that keep this sane:**
1. One adapter per provider. Adding a provider = adding one file, nothing else changes.
2. Raw is never edited. If something is wrong, fix it in staging, so you can always rebuild.
3. Every download writes one line in an **ingestion log**: what, when, from where, how many rows, any error.
4. Running the download twice changes nothing (idempotent).

---

## 5. What no provider has (and never will, for free)

Fuel load, car setup, tyre temperatures and pressures, brake pressure, steering angle, and in 2026 the battery (ERS) state and active-aero state. Teams keep these private.

That's why some things in the project are **estimated** (e.g. fuel effect) and labelled "estimated", never shown as measured. Every column is tagged `observed`, `derived`, `estimated` or `unknown`.

---
