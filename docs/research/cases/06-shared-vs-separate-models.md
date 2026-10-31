# Case 06 · One shared model or many, and the 2026 rules change

Decision: [0012 · One shared model for every track and year](../../decisions/0012-shared-model.md) (2026-10-27) · Register: E15–E19, E21

## 1. Research question
Should race pace be forecast with one model for every circuit and season, with separate models per circuit or per year, or with explicit circuit and rules-era terms?

## 2. Initial hypothesis
The original plan was "mixed effects, then Bayesian": a shared model with a per-circuit offset, later a Bayesian version. Circuits differ, so a circuit term should help, and a new rules era (2026) should need its own coefficients.

## 3. Dataset and scope
Dry races 2022–2026 from the forecasting table ([`targets.py`](../../../src/dpec/forecasting/targets.py)); 2022 only trains. Settings chosen on the **tune years** 2023–24; results reported on the **test years** 2025–26 (37 weekends, 726 driver-races per checkpoint).

## 4. Method
- Candidate: one [weighted least-squares](https://en.wikipedia.org/wiki/Weighted_least_squares) regression, refitted before every weekend on all earlier races. After practice: `race gap ~ team_form + driver_vs_team`; after qualifying: `+ quali_gap_pct`. Recency weights halve every *h* races.
- Compared, under the same walk-forward test ([case 07](07-temporal-validation-and-ranges.md)), with five baselines including a **per-year model**, plus three variants: a per-circuit random effect (mixed model), a 2026 rules-era switch, and half-lives of 6, 12, 24 and 48 races or equal weights.
- Ablation: remove one input at a time and rerun the backtest.

## 5. Results

**Accuracy on the test years** (mean absolute error, % of a lap; seconds on a 90 s lap):

| Forecaster | After practice | After qualifying |
|---|---|---|
| Shared model | **0.648%** (0.58 s) | **0.548%** (0.49 s) |
| Team form | 0.674% | 0.674% |
| Per-year model | 0.883% | 0.589% |
| Signal as is | 1.071% | 0.594% |
| Last race | 0.744% | 0.744% |
| No signal | 1.047% | 1.047% |

**Variants:**
- Per-circuit offset: worse at both checkpoints (0.569% vs 0.553% after practice; 0.535% vs 0.513% after qualifying, against the same model without it).
- Rules-era switch: worst of all in 2026 rounds 1–5 (1.034% after practice).
- Half-life: all options within 0.003%; 12 races kept (about half a season).
- One model per circuit: not viable, with 3 to 4 races per circuit in the history.

**Ablation** (all forecast years, after practice / after qualifying): full 0.556 / 0.498; without team form 0.871 / 0.593; without the qualifying gap – / 0.557; without driver-vs-team 0.567 / 0.503; without recency weights 0.553 / 0.513.

**Where it does not win:** the per-year model orders drivers slightly better after qualifying (median Spearman 0.843 vs 0.821). In 2026 rounds 1–5, simpler methods were as good or better (after qualifying: shared 0.626% vs per-year 0.570%); from round 6 the shared model leads again.

## 6. Interpretation
The target is already relative to the fastest car of each race, so a circuit's general speed is removed. What remains of "this car suits this track" is real but small, and an offset learned from 3–4 noisy races mostly fits noise. A rules-era switch learns 2026 coefficients from only 20–100 rows in the first five races. Recency weighting does the same job gently: new races weigh most while older ones keep the fit stable. Because the first step of the mixed-effects plan made forecasts worse, the Bayesian version was not built.

## 7. Decision influenced
- One shared model for every track and year, refitted every weekend ([`src/dpec/forecasting/model.py`](../../../src/dpec/forecasting/model.py)).
- Team form is the dominant input; the forecaster is described honestly as "team form, adjusted by driver and qualifying".
- A written rule for the next rules change: compare the per-year line and the shared model race by race for the first five races, and say which one the decision packet should trust.

## 8. Known limitations
- No inputs for tyres, fuel strategy, weather, upgrades or grid penalties ([model card](../../model-card.md#known-limits)).
- After a regulation change, expect about five races where the model is no better than simple guesses.
- The per-circuit idea may return as a car-and-track interaction in the planned car root-cause module (Future).

## 9. Evidence and implementation
- Notebook (original): [`notebooks/03_forecast/c2_shared_model.ipynb`](../../../notebooks/03_forecast/c2_shared_model.ipynb) (variants and half-life), [`c3_ranges_and_chances.ipynb`](../../../notebooks/03_forecast/c3_ranges_and_chances.ipynb) (ablation)
- Results: [`reports/backtest/scores.csv`](../../../reports/backtest/scores.csv)
- Code: [`features.py`](../../../src/dpec/forecasting/features.py), [`model.py`](../../../src/dpec/forecasting/model.py), [`baselines.py`](../../../src/dpec/forecasting/baselines.py)
- Tests: [`tests/dpec/test_model.py`](../../../tests/dpec/test_model.py), [`test_forecasting.py`](../../../tests/dpec/test_forecasting.py)
- Summary: [model card](../../model-card.md) · Narrative: [methods.md § 7](../../methods.md#7-the-forecaster)
- How it works now: [workstream 03 · Forecasting and machine learning](../../workstreams/03-forecasting-machine-learning.md)

Previous: [Case 05](05-track-evolution.md) · Next: [Case 07 · Temporal validation and ranges](07-temporal-validation-and-ranges.md)
