# How I built it: the method, phase by phase

This is the long version of the project: what I set out to answer, how I got the data, the problems I found in it, the choices I made and the numbers behind them. The README has the results in two minutes; this document has the reasons. Every decision mentioned here has a short record in [`docs/decisions/`](decisions/), and every number can be reproduced with the commands in the README.

---

## 1. The question

Most F1 data projects describe what already happened: lap times, tyre stints, a telemetry trace. I wanted a project that has to be **right about something before it happens**, and is checked afterwards in public.

So the question is the one a race team's engineers ask on Saturday night:

> After practice and qualifying, how fast will each car really be in the race, how sure are we, and what should our team do about tyres and pit stops?

I framed it for one team, "Team DPEC", which adopts Mercedes's two cars (decision 0001). A team view forces real choices: which numbers matter for a decision, what "good enough" means, and what to say when the data can't decide.

"Race pace" has one definition everywhere in the project: a driver's **median clean race lap, as a percentage behind the fastest car that day**. A percentage, not seconds, so a Monaco race and a Monza race can be compared and modelled together.

## 2. How I organised the work

I split the project into five phases, each ending in a gate: a short checklist that must be true before the next phase starts.

| Phase | Gate |
|---|---|
| A · Data | one command rebuilds clean data for 2022–2026, with checks |
| B · History | every "what happened" question answered; research on which signals predict race pace; the app |
| C · Forecast | forecasts with honest ranges and a checkable decision; one forecast frozen in public before a race and scored after |
| D · Explain | a debrief that splits the time; an AI assistant with a measured pass rate |
| E · Public | a live copy and a write-up a stranger understands in two minutes |

Three habits held for the whole project:
- **Decision records.** Each real choice (18 of them) has a one-page record: what I decided, why, what I rejected, and the known limits.
- **Tests and checks on every change.** Unit tests on fake data (127 at the end, no internet needed) and data checks on the real warehouse (21), both in CI on every push.
- **Nothing hard-coded.** Seasons, our team, thresholds and paths live in one settings file, read through typed settings that refuse unknown keys.

## 3. The data

**Source.** Everything comes from the official F1 timing feed through FastF1: laps, sectors, tyres, weather, car telemetry, results. FastF1 also stores the official classification (from the Jolpica service), so I didn't build a second adapter for results (decision 0005). OpenF1 was only used to cross-check a few values.

**Ingest once, never edit.** `dpec ingest` downloads every session of 2022–2026 once, into Parquet files that are never changed afterwards, with a manifest that records row counts and a SHA-256 fingerprint per file. Re-runs only fetch sessions that are new. By October 2026: 545 sessions (practice, sprint, qualifying, race), 297,724 laps, 4.1 GB of raw files (plus 34 GB of FastF1's own cache).

**Warehouse.** `dpec build` rebuilds a DuckDB file from plain SQL (decision 0002: a file, not a database server, because one person runs it and the data fits on a laptop). Core tables hold one clean row per session, lap, result and driver; answer tables ("marts") on top of them answer the common questions: weekends, weather, standings, pace, tyre stints, long runs, track evolution, the forecaster's weekend signals and race strategy.

**Telemetry on a distance grid.** To compare two laps, I put both on the same 5 m distance grid, computed on demand from the raw files instead of stored (decision 0004): storing it would multiply the data for comparisons that are rarely asked.

## 4. Messy data, and what I did about it

This is the part that took the longest, and the part I'd most like to talk about.

**When is a lap "real pace"?** Most laps are not: out-laps, in-laps, laps behind the safety car, laps with a yellow flag, deleted laps, wet laps. I gave every lap exactly **one reason code**: `clean`, or the **first** rule it breaks, in a fixed order (`no_time` → `generated` → `in_lap` → `out_lap` → `lap_one` → `red_flag` → `safety_car` → `vsc` → `yellow` → `deleted` → `inaccurate` → `wet_tyre` → `slow`), decision 0003. The order matters: a lap can break several rules, and a fixed order means every lap is counted once and the counts add up. Each rule is also kept as its own yes/no column, so a later model can be stricter. `slow` means slower than 107% of the session's median clean lap, a limit I picked by looking at the distribution. Result: 55% of all laps are clean, 78% in races and 27% in qualifying (where most laps are out-laps and cool-down laps). Wet races find themselves: Japan 2022 and São Paulo 2024 come out with no clean laps at all.

**Checks as SQL that return the bad rows** (decision 0006). Every rule about the data is a query that returns the rows breaking it; empty means pass. `dpec check` runs all of them on every rebuild, and fails the build if a column is missing from the data dictionary. They caught real problems in the official feed:
- **Sprint-qualifying results with no driver IDs.** A driver code means one driver within a season, so the ID is borrowed from the same driver's other sessions that season.
- **Two 2026 practice sessions with no team names** (FP1 of rounds 5 and 7). Filled from the same driver's team in another session that weekend, or, for practice stand-ins, from the same driver and car number that season.
- **Teams renamed across years** (the same team under three names). A hand-written ID map with each team's lineage, so "team form" follows the team, not the name.
- **A track temperature sensor dropping out:** 47 readings of exactly 0 °C out of 54,295, in 14 sessions. A dry track at 0 °C is impossible, so they are treated as missing (decision 0007), not averaged in.
- **Results must add up:** 101 or 102 points per race (102 when the fastest-lap point was given), 36 per sprint, disqualifications after the flag included (Russell's Spa 2024 win shows as a disqualification).
- **Pit-stop costs must be believable** (15–35 s); anything outside means the in-lap and out-lap were paired wrongly.

**Problems that only showed up in the live path:** Montreal 2026 was 68 laps instead of 70, and Madrid's new Madring circuit had no earlier race at all. A forecast can't know a race's length from history in either case, so the live command takes the official length as an input (`--race-laps`) instead of guessing.

## 5. Analytics: the tables the forecaster stands on

Three tables needed real modelling choices:
- **Tyre stints and practice long runs** (decision 0008). A long run is a practice stint of at least 5 clean laps on one set of tyres, each within 2% of the stint's median lap (both limits are settings). Cars get lighter as they burn fuel, which hides tyre wear, so I correct each lap with an explicit fuel-burn term instead of pretending it isn't there.
- **Track evolution** (decision 0009). The track gets faster as rubber goes down. I measure it **within each driver** (fixed effects), so a fast driver going out late doesn't look like a faster track.
- **Weekend signals**: for each driver and weekend, what was known before the race: the qualifying gap, long-run pace, team form.

## 6. Research: what actually predicts race pace?

Before building a model I asked which signals known before the race predict the race (step B3). Over 86 dry weekends, **qualifying pace put the drivers in race order far better than practice long runs** (median Spearman correlation 0.80 against 0.39), and adding long runs on top of qualifying cut the error by only about 2%. That surprised me, because long runs look like "race practice". The reason: practice runs are done on unknown fuel loads and engine modes, so they are noisy; qualifying is everyone flat out at the same time. The forecaster therefore starts from qualifying and team form (decision 0010).

## 7. The forecaster

**What it predicts:** each driver's race pace (as defined above), once after practice and once after qualifying, with an 80% range and the chances of being fastest, top 3, and ahead of the teammate.

**How it's tested** (decision 0011): a **walk-forward backtest**. Before each race weekend from 2023 on, everything is refitted on earlier races only and then forecasts that weekend, exactly as it would have run live. A test fails if a feature ever sees its own race. Settings were chosen on 2023–24 only; the results are reported on **2025–26** (37 weekends, 726 driver-races), which were never used to choose anything.

**Five baselines,** because an error of 0.5% means nothing alone: no signal (everyone equal), the last race, team form, the signal as is, and a separate model per year. A forecaster that can't beat "the team's recent form" isn't worth having.

**The shared model** (decision 0012): **one** weighted regression for every track and year, refitted before every weekend. Inputs: the team's recent race pace (exponentially weighted), each driver's usual gap to the teammate, and after qualifying the qualifying gap. Newer races weigh more (a half-life of 12 races). I tried separate models per track and per year first; there are too few races per track, and a per-year model starts every season with no data.

| Forecaster | After practice | After qualifying |
|---|---|---|
| **Shared model** | **0.648%** (0.58 s a lap) | **0.548%** (0.49 s a lap) |
| Team form | 0.674% | 0.674% |
| Last race | 0.744% | 0.744% |
| Per-year model | 0.883% | 0.589% |
| The signal as is | 1.071% | 0.594% |
| No signal | 1.047% | 1.047% |

*Mean absolute error on 2025–26, % of a lap.*

**What matters inside it** (ablation, all years): without team form, the after-practice error grows from 0.556% to 0.871%; without the qualifying gap, the after-qualifying error grows from 0.498% to 0.557%.

**Tested, then rejected:** a separate offset per circuit (a mixed model) and a switch for the 2026 rules era both made the forecasts worse on the years used for choosing.

**Where it doesn't win:** the per-year model puts drivers in a slightly better order after qualifying (Spearman 0.843 against 0.821). After the 2026 rules change, simple guesses did as well for the first ~5 races and the ranges were too narrow there (68% inside after practice); the model caught up after that.

**Honest ranges and chances** (decision 0013). The 80% range is split-conformal and walk-forward: the 80th percentile of the model's **own** errors over its last 10 forecast weekends. On 2025–26, 78.5% (after practice) and 79.9% (after qualifying) of real race paces landed inside: the ranges mean what they say. The chances come from 4,000 replays of the race order drawn from those errors; the chance of a top-3 race pace scores 0.077 on the Brier score after qualifying, against 0.132 with no information.

## 8. From a forecast to a decision

A forecast alone doesn't tell a team what to do. For each dry race (decision 0014):
1. **Tyre wear** from the practice long runs, corrected by what earlier races at that circuit taught.
2. **Pit-stop cost** measured at this circuit from earlier races.
3. **1, 2 and 3 stops** costed over 4,000 replays of tyre wear. If no plan is best in at least 65% of the replays, the decision packet says **"no clear decision"**, because a confident wrong call is worse than an honest "it's close".
4. A **first-stop window**: every lap where stopping costs at most 1 s more than the best lap to stop. Low wear gives a wide window: timing barely matters.

The hard part was scoring it. You can't score "did the plan win", because the other plans were never raced. So I score what can be checked: was the tyre wear inside its range, did the number of stops match what the top 10 did, and did the real first stops fall inside the window. Replayed on all 78 dry races since 2023, each with only what was known before it, the stop call matched the top 10 in **58%** of races, against 46% for "always one stop"; 67% against 57% when the call was clear, 41% against 26% when it wasn't.

Example: for Bahrain 2024 the packet said 1 stop (best in 74% of replays) and named the risk: if tyre wear was above 0.093 s a lap, two stops would beat one. The race wore the tyres at 0.100 s a lap, and the top 10 stopped twice. The packet was wrong about the call and right about why.

## 9. In public: frozen before the race, scored after

A backtest, however careful, is run after the races by the person who built the model. Nobody can check that I didn't try twenty models and keep the best. So from Phase C on, forecasts are also made **in public** (decision 0015):
- After qualifying, `dpec freeze` writes every car's forecast, range and chances, the five baselines' guesses and the tyre decision into one JSON file under `ledger/`. The file carries the SHA-256 of its own content.
- I push it before the deadline, 30 minutes before the race. The time that counts is GitHub's, not my laptop's: a CI job fails if a forecast reached GitHub after its deadline, or if any frozen file is ever changed or deleted.
- After the race, `dpec score` writes a separate score file: error, the share inside the ranges, skill against team form, Spearman, the tyre decision's checks, and a one-word verdict (GOOD, OK, MISS).

**Dress rehearsal.** Before the first live weekend I ran the live code on 2026 rounds 1–17 as dry runs (kept apart from the record, labelled "made after the fact"): 16 dry races, 322 driver-races, error 0.573%, exactly the backtest's 0.573% (largest difference 0.0000%), so the live path is the tested path. 81% of real paces landed inside the ranges, the model beat team form on 14 of 16 weekends, and the verdicts were 11 GOOD, 4 OK, 1 MISS.

**Live weekends.** <number> weekends frozen before the race so far, starting from <first live round>. Each one, with its deadline, the time it was frozen and its score, is in [`docs/live-weekends.md`](live-weekends.md).

FastF1 publishes a session about three hours after it starts, so the freeze window runs from qualifying + 3 hours to the race − 30 minutes. A weekend I miss is a gap in the record, not a hidden result; a wet race stays in the record unscored.

## 10. The debrief: where the time went

After a race, the question changes from "how fast?" to "why?" (decision 0016).

**Qualifying:** each of our drivers' best clean lap against the fastest, on the 5 m grid. Every 5 m of the gap is assigned to one kind of track part, read from the faster lap: braking, straight, traction (corner exit), slow, medium or fast corner. Kinds, not corner numbers, because "Turn 4" means nothing at the next track, while "slow corners" points at mechanical grip at every track. The parts add up to the lap gap exactly: nothing is counted twice or lost. Bahrain 2024: Russell was 0.320 s slower than Leclerc, almost all of it on straights (+0.257 s) and corner exits (+0.245 s), partly won back in slow corners (−0.195 s).

**Race:** the gap to the best race pace on **paired laps** (the same lap number, both clean, so fuel burnt and track grip cancel), split by a regression into pace, tyre age difference, compound difference and traffic for each car, with 80% ranges from 1,000 bootstrap resamples.

**What the debrief taught me about my own forecast.** Singapore 2026: Russell's race pace was 1.49 s a lap off the best (Leclerc's), much worse than forecast, at the very top of its 80% range. The debrief split it: about 0.9 s pace, about 0.5 s traffic. He had qualified 6th but started 19th, and spent 76% of his clean laps within 1.5 s of a car ahead. The forecast doesn't know the starting grid after penalties; that's now a written idea for later. The same race taught me a statistics lesson: both cars were in traffic on the same laps, so the regression couldn't separate the two traffic inputs and gave one a "wrong" sign. When two inputs always move together, I read their parts together, and a strange sign is a reason to look at the laps, not a finding.

## 11. The AI race engineer, and its exam

The last piece is an assistant that answers questions about any session since 2022 (decision 0017). The rule I started from: a language model that doesn't know a number makes up a plausible one. So it never answers from memory. It has **eight read-only tools** (the list of tables, a guarded SQL tool, the lap split, the race split, the forecast, the tyre decision, the public record, the data status), every number in an answer names the tool it came from, and for fuel, setups, ERS, tyre temperatures or radio it says "not public".

**The SQL tool is guarded** four ways: SELECT only, one statement, only known tables and no file readers (checked by DuckDB's own parser), and a read-only connection with a 10-second timeout, at most 50 rows and 20,000 characters back.

**It runs on Claude** through Anthropic's API by default, or on a free local model through Ollama, with the same tools and the same loop.

**It has an exam,** because "it seems to work" isn't a result. 50 questions in five kinds (18 lookups, 12 comparisons, 8 forecast questions, 7 decision questions, 5 traps that must be refused). Each right answer is **computed from the warehouse when the exam runs**, so the exam stays correct as races arrive, and a grader reads the numbers and names out of each answer. Results:

- Claude: **<overall>%** overall, <traps> of 5 traps refused, about $<cost> per run of 50 questions.
- Local model (Ollama): <ollama result>.

I didn't build a multi-agent router: one engineer with tools is simpler to test, and a second, specialised agent is only worth adding if the exam shows a kind of question it would fix. The grader has known weak spots (a small number like "2" can appear elsewhere in a sentence; a number written in words isn't read), written down in the decision record.

## 12. The public copy

The app is online, read-only, at <https://f1-pace-intelligence.onrender.com> (decision 0018). Two things stay on my machine: the telemetry traces (they need the 4 GB of raw files) and the race engineer (each question costs money).

Getting it there works like a real release:
1. `dpec snapshot` packs what the public app needs (the warehouse, the saved forecasts and the ledger: about 11 MB) into one file, with a SHA-256 checksum per file and a manifest of the data and the code version.
2. I attach that file to a **GitHub Release**. Data never goes into git: a binary that changes every weekend would stay in the history forever.
3. A workflow builds a **Docker image** from the code at the release's tag. The build stops if one checksum doesn't match. It starts the image and checks that it's the public copy (public mode, the page loads, the weekends are there, the chat answers 403) before it publishes anything.
4. A free **Hugging Face Space** runs that image. It sleeps after two days without visitors…` | `A free **Render** web service runs that image. It sleeps after 15 minutes without visitors and wakes in about a minute.

## 13. Engineering

- **Python 3.12, uv** with a lock file (the same library versions on my Mac, in CI and in the image), **DuckDB**, plain SQL for every table, **FastAPI** for a read-only API (every request opens a read-only connection; every value goes in as a SQL parameter), a plain JavaScript app with linked windows, **statsmodels** for the regressions.
- **127 unit tests** on fake data: they need no internet and no API key, so CI runs them on every push. The AI tests use a stand-in model and a stand-in server that checks the exact request format.
- **21 data checks** on the real warehouse, and a data dictionary that the build checks against the tables.
- **CI:** tests, lint, and the ledger guard on every push; the image build and smoke test on every release.

## 14. What public data can't tell, and other limits

- Fuel loads, setups, engine modes, tyre temperatures and pressures, and in 2026 the battery (ERS) and active-aero state are not public. Practice long runs are noisy for exactly this reason. Where the project estimates an effect, it says "estimated".
- The forecast doesn't know the starting grid after penalties, safety cars or strategy: it forecasts pace, not position.
- The decision layer is scored against what the top 10 did, which is not the same as "the best plan".
- Traffic in the debrief can't tell a fight from a car that was simply close.
- One person runs the public record: a missed weekend is a gap.

## 15. What I'd do next

- **Why one car can't match another:** a car root-cause module comparing two cars' speed traces corner by corner over a season (planned from the start; the architecture keeps a place for it).
- **The starting grid after penalties** as a forecast input (from the Singapore 2026 debrief).
- More live weekends: the record only becomes convincing with time.

## 16. How I used AI

I built this project with an AI assistant (Claude) as a tutor and coding partner. Most of the plumbing (the API, the app's JavaScript, the command line, the Docker and CI files, much of the test scaffolding) was written with it. I chose the problem and the scope, made the decisions in `docs/decisions/`, ran every step on my own data on my own machine, worked through the thinking parts of each phase (the lap rules, the data checks, the forecast target and baselines, the scoring rules, the exam), checked every number in this document against the warehouse, and can explain and defend each decision.
