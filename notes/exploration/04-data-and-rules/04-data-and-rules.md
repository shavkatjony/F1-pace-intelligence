# 02 · F1 rules that matter for this project

> **Short version:** You don't need to read the whole FIA rulebook (hundreds of pages). About 12 rules change what the data looks like. This file lists them, says what each does to the data, and what we do about it. Car-building rules (Technical Regulations) are **LATER**, for the car-performance module.

---

## The rulebooks, and which ones you need

| Rulebook | What it covers | For us |
|---|---|---|
| **Sporting Regulations** | how the weekend runs: sessions, tyres, parc fermé, safety car, penalties, points | **NOW**, but only the sections below |
| **Technical Regulations** | how the car is built: size, weight, engine, aero | **LATER** (car-performance module) |
| Financial Regulations | cost cap | never |

Where to read: fia.com → Regulations → Formula 1. Pirelli's race preview each weekend says which tyre compounds were brought. Numbers in rules change between seasons, so check the current version before you put a number in code. This file explains the *ideas*, not the exact numbers.

---

## The 12 rules

| # | Rule (plain) | What it does to the data | What we do |
|---|---|---|---|
| 1 | **Two weekend formats.** Normal: FP1, FP2, FP3, Qualifying, Race. Sprint: FP1, Sprint Qualifying, Sprint, Qualifying, Race | Sprint weekends have only one practice → far fewer long runs | Session list always comes from the calendar, never hard-coded. Forecasts on sprint weekends get wider ranges |
| 2 | **Pirelli brings 3 dry compounds per race**, labelled Soft / Medium / Hard for that weekend, chosen from a wider range (C1 = hardest … C6 = softest) | "Soft" in Bahrain can be a different rubber than "Soft" in Monaco. FastF1 only says SOFT/MEDIUM/HARD | Small hand-made table: event → which C-number was Soft/Medium/Hard (from Pirelli previews). **This was missing from the plan** |
| 3 | **Two-compound rule.** In a dry race each driver must use at least two different dry compounds | Almost everyone stops at least once. Shapes every strategy | The strategy model must respect it. A "no-stop" plan is not allowed |
| 4 | **Wet tyres** (Intermediate, Wet). If used, rule 3 no longer applies | Wet laps are much slower and follow different patterns | Flag wet sessions; don't mix them into dry pace |
| 5 | **Limited tyre sets per weekend** | Teams save new tyres in practice, so practice runs often use old tyres. Practice doesn't show everything | Record each stint's tyre age at the start (`TyreLife` in FastF1) and use it in models |
| 6 | **Parc fermé.** From qualifying on, the setup basically can't change | The qualifying car ≈ the race car. Practice cars may differ | Qualifying is a strong update to the forecast. Practice carries more noise |
| 7 | **No refuelling.** Cars start the race heavy and get lighter every lap | Lap times improve as fuel burns, even while tyres wear. Fuel load is **not public**, and teams run different fuel in practice | Fuel effect is **estimated** and labelled so. It's the biggest hidden noise in practice long runs |
| 8 | **Safety car, Virtual Safety Car, red flag** | Slow laps that are not pace. Pit stops under SC cost less time | Flag these laps (track status codes). Exclude from pace. Keep them for strategy history |
| 9 | **Track limits.** Lap times can be deleted | Deleted laps look valid in raw data | Flag deleted laps (race-control messages, `Deleted` column) |
| 10 | **Pit lane speed limit** | Each circuit has its own "time lost by pitting" | Measure pit loss per circuit from the data. A key input for pit windows |
| 11 | **Penalties after the race** (time penalties, disqualification) | On-track order ≠ official result | Official results come from Jolpica |
| 12 | **2026 new car rules.** New engines with about half the power electric, moving wings (active aero), DRS replaced by an overtake/boost system, smaller and lighter cars | 2026 data behaves differently from 2022–2025. Battery and wing state are **not** in public data. The meaning of the old DRS channel changed | Treat 2026 as a new era: the model updates during the season (step C2). Write a decision record on what each 2026 channel means (step A5) |

---

## Rules can change during a season

They did in 2026: the energy rules were adjusted mid-season (the plan's earlier research found a cut in qualifying recharge energy and a cap on race boost from the Miami round). A change like that makes data before and after it differ.

**Missing from the plan, added now:** a small file `docs/f1-rules/rule-changes.csv`

| date | event | rule change (plain) | which data it affects | source link |
|---|---|---|---|---|

Add a row whenever you find a change. The forecaster can then mark races before/after a change.

---

## What you don't need (protect your focus)

- Exact car dimensions, engine details, aero rules → LATER (car-performance module).
- Points tables beyond "results come from Jolpica" → not needed for forecasting.
- Financial rules, driver licences, protest procedures → never.

---

## Done when (exit condition)

You can explain rules 2, 3, 6, 7, 8 and 12 in 2 minutes, each in the form "the rule is X, so the data does Y, so we do Z". Then move on. You'll meet the others naturally in the steps.

