# 07 · Forecasting Models (the core)

> **Short version:** After each session of a weekend, forecast every car's **qualifying pace** and **race pace**, with uncertainty ranges. The hard parts are: practice hides fuel loads and programmes; every circuit is different; and 2026 keeps changing. Start with baselines, then a statistical model, and add ML only where it beats them. **This is where your time goes.**

---

## Overview steps

1. Define the targets exactly (below).
2. Build the baselines.
3. Build the **practice-pace model**: real pace from noisy practice laps.
4. Add **cross-circuit transfer** features.
5. Add **in-season updating** for regime changes.
6. Turn pace forecasts into session forecasts (qualifying order, race pace and finishing range) by simulation.
7. Walk-forward backtest on 2022–2026 with baselines alongside.
8. Calibrate the intervals.
9. Package as `dpec forecast --event X --after FP2`.

---

## 1. Targets (what exactly is forecast)

| Target | Definition | When forecast |
|---|---|---|
| **Q pace** | each driver's best qualifying lap, as a gap (%) to the session's fastest | after FP1, FP2, FP3 / SQ |
| **Race pace** | each driver's median clean race lap, fuel-corrected, as a gap (%) to the field median | after practice, after qualifying |
| **Degradation** | race stint slope per compound (s/lap) | after practice |
| **Finishing range** | 80% range of finishing position, from simulation | after qualifying |

Gaps in **% of lap time** make circuits comparable (1% at Monaco is not the same number of seconds as 1% at Spa).

---

## 2. Baselines (always reported)

| Baseline | Rule |
|---|---|
| B1 · Last race | same gaps as the previous race |
| B2 · Season form | each team's average gap over the last 3 races |
| B3 · Practice best | rank by best practice lap |
| B4 · Practice long-run median | raw long-run medians, no corrections |

If the model can't beat B2 and B4, it isn't adding value. Rule 11: say so.

---

## 3. Practice-pace model (the latent-variable problem)

**The problem:** a practice lap time = true car pace + fuel load effect + tyre age effect + track evolution + engine mode + traffic + noise. Only the lap time, tyre and conditions are observed. Fuel and programme are hidden.

**Approach: a hierarchical (mixed-effects / Bayesian) model, step by step**
1. Start with a mixed-effects regression on clean long-run laps:
   `lap_time ~ compound + tyre_age×compound + session_progress + track_temp + (1 | driver) + (1 | team) + (1 | run)`
   The **run-level random effect** absorbs each run's unknown fuel level and engine mode. That's the key idea: you don't need fuel data, you let each run have its own offset and learn its distribution.
2. **Team pace** = the team random effect, with uncertainty. That's the forecast input.
3. Upgrade to a Bayesian version (PyMC or NumPyro) when you need full posterior intervals, and to use **priors from previous races** (step 5).
4. Validate: does practice team pace predict race team pace better than B4?

---

## 4. Cross-circuit transfer

**The problem:** a car fast at Monza may be slow in Hungary.

**Approach:**
1. Describe each circuit with features: % of lap at full throttle, average corner speed, number of slow / medium / fast corners, longest straight, braking events, surface abrasiveness (where public), typical temperature.
2. Describe each car by its **profile** across past races: performance in slow, medium and fast corners, straight-line speed, traction (from corner and straight-line marts).
3. Model: car pace at circuit c ≈ base pace + profile · circuit features. This is a **matrix-factorisation / interaction** idea, fitted as a regression with interaction terms first, then optionally as gradient boosting on the same features.
4. Evaluate on circuits held out entirely ("leave-one-circuit-out").

This gives a **prior** for a weekend before any practice lap is run, and practice updates it.

---

## 5. In-season updating (2026 non-stationarity)

**The problem:** teams bring upgrades, and the FIA changed the energy rules mid-season in 2026 (qualifying recharge 8 → 7 MJ, race boost capped at +150 kW from Miami). Old races become less relevant.

**Approach:**
1. Weight past races by recency (exponential decay; half-life tuned in backtest).
2. Treat each team's pace as a **slowly drifting state**: a simple state-space or Kalman-style update. Last weekend's posterior becomes this weekend's prior, plus some extra variance.
3. **Change-point flags:** when a team's observed pace jumps far outside its forecast interval, mark a possible upgrade or regime change and widen uncertainty.
4. Report the "2026 shift" experiment: how much the 2025-trained model degraded at the start of 2026, and how fast updating recovered it.

---

## 6. From pace to session forecasts

- **Qualifying:** sample each driver's pace from the posterior plus driver-level lap noise → rank → probability of each position.
- **Race:** a light race simulation per draw: grid, race pace, degradation, strategy from `mart_strategy_history` patterns, pit loss per circuit, safety-car probability per circuit. Output an 80% finishing range per driver.
- Keep the simulation simple. It's a tool for turning pace into positions, not a strategy optimiser (that space is crowded, see v3).

---

## 7. Validation (rule 8)

- **Walk-forward:** for each weekend W in 2023–2026, train on everything before W and forecast W at each checkpoint (after FP1, FP2, FP3, Q).
- **Metrics:** MAE of gap %, Spearman rank correlation, interval coverage (80% target), CRPS (a score for whole forecast distributions), each per checkpoint.
- **Ablations:** remove fuel/run correction, transfer features, updating, one at a time, to show what each adds.
- **Experiment tracking:** every run logged with MLflow 

---

## 8. Calibration

Check the coverage of the 80% intervals over the backtest. If they're too narrow or too wide, fix it with **conformal calibration** on the walk-forward residuals. That's simple, robust, and easy to explain in an interview.

---

## Detailed side: where ML (vs statistics) is actually used

| Part | Method | Why |
|---|---|---|
| Practice pace | mixed-effects → Bayesian hierarchical | small groups, hidden offsets, needs uncertainty |
| Transfer | regression with interactions → gradient boosting (LightGBM) | non-linear profile × circuit effects, enough rows |
| Updating | state-space / Kalman | drifting quantity over time |
| Session outcome | Monte Carlo simulation | turns pace distributions into position distributions |
| Calibration | conformal prediction | honest intervals |



-
