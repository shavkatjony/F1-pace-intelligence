# 11 · App Workspace & Windows

> **Short version:** The app is a **workspace of linked windows**, like a pit-wall setup. You can open as many windows as you want, drag them across monitors, and every window follows one shared context (event, session, drivers, lap, distance cursor). Change the driver in one window and every window updates. Layouts and settings are saved. It's the same web app locally and online. **This file covers structure and behaviour. Visual styling is designed in a separate thread (D6).**

---

## Overview steps

1. Define the **shared context** (the state every window listens to).
2. Define the **window types** (below), each reading one or more marts through the API.
3. Build the workspace: tiled panels inside one browser tab.
4. Add **pop-out windows**: a panel can open as its own browser window and stays in sync.
5. Add **layout presets** and **multi-monitor** placement.
6. Add **settings** (units, theme, density, refresh, default team).
7. Add **local vs public mode** differences (writes, AI, data freshness).

---

## The shared context (what links all windows)

```
context = {
  season, event, session,
  drivers: [primary, compare...],
  lap_selection, distance_cursor_m, time_cursor,
  checkpoint (after FP1/FP2/FP3/Q),
  units, theme
}
```

- One **context store** in the app.
- Windows **subscribe** to the parts they care about (a telemetry window listens to `distance_cursor_m`; a scoreboard ignores it).
- **Sync across browser windows** uses the `BroadcastChannel` web API (same-origin windows message each other instantly; no server needed). Every pop-out joins the same channel.
- **Link groups:** a window can be "linked" (follows the context) or "pinned" (keeps its own context, e.g. to compare two sessions side by side). Each window shows a small link icon.

---

## Window types

| Window | Shows | Reads |
|---|---|---|
| Session board | timing tower, results, gaps | `mart_session_overview` |
| Telemetry traces | speed / throttle / brake / gear vs distance, overlaid | `mart_telemetry_overlay` |
| Track map | circuit coloured by speed or delta, cursor dot | `mart_track_map` |
| Lap delta | cumulative delta trace, gain/loss zones | `mart_lap_delta` |
| Corner table | per-corner entry/min/exit, braking points | `mart_corner_summary` |
| Long runs & tyres | practice long runs, degradation with intervals | `mart_long_runs`, `mart_tyre_stints` |
| Weekend forecast | current forecast at this checkpoint, intervals, position probabilities | ledger / forecaster |
| Scoreboard | season forecast accuracy vs baselines | ledger scores |
| Debrief | attribution table and text | file 09 |
| Weather & track | conditions, track evolution | `mart_weather`, `mart_track_evolution` |
| Data quality | quality score, flags, coverage | `mart_data_quality` |
| Standings & calendar | championship, next sessions | `mart_standings`, `mart_calendar` |
| Race engineer chat | AI assistant (file 10) | AI layer |

The cursor is synced: hover at 1,840 m in the telemetry window, and the track-map dot, the delta window and the corner table all move to 1,840 m.

---

## Layouts and monitors

| Preset | Windows | Use |
|---|---|---|
| **Pit wall** (2–3 monitors) | M1: session board + forecast · M2: telemetry + track map + delta · M3: chat + quality | race weekend |
| **Performance** (1 large monitor) | telemetry, delta, track map, corner table tiled | driver comparison |
| **Strategy** | long runs, tyres, forecast, scoreboard | before quali/race |
| **Laptop** (1 small screen) | tabs instead of tiles, one window at a time | travel, demo |
| **Phone** | read-only scoreboard + forecast | quick check |

- Layouts are saved as JSON (window type, position, size, monitor, linked/pinned).
- Multi-monitor placement uses the browser's **Window Management API** where supported (currently Chromium-based browsers). Elsewhere, pop-outs open and you place them yourself, and the layout remembers their size. Treat this as an enhancement, not a requirement.
- Optional LATER: wrap the same web app in a small desktop shell (e.g. Tauri) for native multi-window control. Not needed for the flagship.

---

## Settings

Units (km/h or mph, seconds or %), theme (from the design thread), density (compact or comfortable), default team (D2), refresh behaviour (local: on new ingest; public: daily), number formats, colour-blind-safe palette on/off. Settings live in browser storage, and an export/import file carries them between machines.

---

## Local vs public behaviour

| | Local | Public |
|---|---|---|
| Data | full warehouse | precomputed marts + ledger |
| Actions | ingest, forecast, freeze buttons | none (read-only) |
| AI chat | Claude or Ollama | Claude with a cap, or a recorded demo |
| Layouts | all presets | all presets |

---


