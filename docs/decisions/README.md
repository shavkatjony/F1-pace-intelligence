# Decision records

One file per decision: what was decided, why, the evidence, and the known limits.

- **Date** is the day the record was first committed (Korea time), so anyone can check it:
  `git log --follow docs/decisions/<file>`.
- **Builds on** names the earlier decisions it depends on.
- A later change gets its own dated **Update** section at the end; nothing is rewritten
  silently.

## How they fit together

| Layer | Decisions |
|---|---|
| Data: what is collected, cleaned and checked | 0001 to 0006 |
| Analysis tables: the questions the data answers | 0007 to 0010 |
| Forecast: one model, a fair test, honest ranges | 0011 to 0013 |
| Decisions and the public record | 0014, 0015 |
| Debrief and the AI race engineer | 0016, 0017 |
| The online copy | 0018 |

## All records

| # | Decision | Date | Builds on | Later updates |
|---|---|---|---|---|
| [0001](0001-dpec-team.md) | Our cars: Team DPEC follows Mercedes's two cars | 2026-10-11 | | |
| [0002](0002-storage.md) | Storage: Parquet files and DuckDB | 2026-10-11 | | |
| [0003](0003-clean-laps.md) | Clean tables and one reason code per lap | 2026-10-18 | 0002 | |
| [0004](0004-distance-grid.md) | Laps compared on a 5 m distance grid | 2026-10-19 | 0002, 0003 | |
| [0005](0005-results-and-log.md) | Official results, data inventory, download log | 2026-10-19 | 0002, 0003 | |
| [0006](0006-checks-and-id-maps.md) | Data checks and driver and team ID maps | 2026-10-21 | 0003, 0005 | |
| [0007](0007-marts.md) | Answer tables (marts), and no dbt yet | 2026-10-22 | 0003, 0005, 0006 | 2026-10-27 |
| [0008](0008-stints-and-long-runs.md) | Tyre stints, long runs and the fuel effect | 2026-10-22 | 0003, 0007 | |
| [0009](0009-track-evolution.md) | Track evolution | 2026-10-22 | 0003, 0007, 0008 | |
| [0010](0010-forecast-signals.md) | Qualifying pace as the main signal | 2026-10-24 | 0007, 0008, 0009 | |
| [0011](0011-target-and-fair-test.md) | What is forecast, and the walk-forward test | 2026-10-27 | 0010 | |
| [0012](0012-shared-model.md) | One shared model for every track and year | 2026-10-27 | 0010, 0011 | |
| [0013](0013-ranges-and-chances.md) | 80% ranges and chances from past errors | 2026-10-28 | 0011, 0012 | 2026-11-08: Brier by years |
| [0014](0014-decision-packet.md) | Tyre and stop decisions, the decision packet | 2026-10-28 | 0008, 0012, 0013 | |
| [0015](0015-public-record.md) | The public record: frozen before, scored after | 2026-10-29 | 0011 to 0014 | 2026-11-05: paused, no live data |
| [0016](0016-debrief.md) | The debrief: where our cars' time went | 2026-11-03 | 0003, 0004, 0011, 0015 | |
| [0017](0017-race-engineer.md) | The race engineer: one model, read-only tools, an exam | 2026-11-04 | 0007, 0011, 0014 to 0016 | 2026-11-08: first full exam |
| [0018](0018-public-copy.md) | The public copy: what's online and how | 2026-11-04 | 0002, 0015, 0017 | 2026-11-05: Render; 2026-11-08: visitor copy |
