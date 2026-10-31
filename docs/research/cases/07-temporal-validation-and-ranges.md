# Case 07 · Temporal validation, leakage and honest ranges

Decisions: [0011 · Target and fair test](../../decisions/0011-target-and-fair-test.md) (2026-10-27), [0013 · Ranges and chances](../../decisions/0013-ranges-and-chances.md) (2026-10-28), [0015 · Public record](../../decisions/0015-public-record.md) (2026-10-29) · Register: E14, E20–E24

## 1. Research question
How can a race-pace forecaster be evaluated so that the score reflects what it would have achieved before each race, and how can its uncertainty be stated so that an "80% range" really contains about 80% of outcomes?

## 2. Initial hypothesis
A standard train/test split of driver-race rows, plus prediction intervals from the regression's residuals, would be adequate.

## 3. Dataset and scope
Every dry race from 2023 to 2026 (78 weekends, 1,501 driver-races per checkpoint); 2022 only trains. Two checkpoints: *after practice* and *after qualifying*.

## 4. Method
- **Leakage probe:** score a deliberately leaky "forecaster" that copies the teammate's race pace from the same race under a random row split.
- **[Walk-forward](https://en.wikipedia.org/wiki/Walk_forward_optimization) backtest:** for each weekend W, history = races strictly before W; the columns not yet known at the checkpoint are removed by code (`targets.CHECKPOINTS`, `hide_answers()`); everything is refitted; W is forecast. Tests fail if a feature ever sees its own race.
- **Tune/test separation:** settings chosen on 2023–24 only; 2025–26 reported and never used for choices.
- **Ranges:** split-[conformal](https://en.wikipedia.org/wiki/Conformal_prediction), walk-forward: guess ± the 80th percentile of the absolute errors over the previous 10 forecast weekends (none until 5 have passed). Window length chosen on the tune years.
- **Chances:** 4,000 simulated race orders, each driver's guess plus a past error drawn at random (seed 0); evaluated with the [Brier score](https://en.wikipedia.org/wiki/Brier_score).
- **Live-path check:** freeze and score every 2026 dry race with the live code (`dpec pretend`) and compare with the backtest.

## 5. Results
- The leaky teammate copy scores **0.51%**, better than every honest forecaster, and would be useless on a real Saturday. A random split was rejected.
- Range coverage on the test years: **78.5%** after practice and **79.9%** after qualifying (goal 75–85%). On the tune years, a 10-weekend window was closest to 80% (0.800 / 0.810) and nearly the narrowest.
- 2026 rounds 1–5: only **68%** inside after practice with the 10-weekend window (61% with all weekends). The window still held mostly 2025 errors, which were smaller.
- Top-3 chance after qualifying: Brier **0.070** against **0.129** with no information on the test years (0.077 against 0.131 over 2023–26). Calibration is too flat (all forecast years, after qualifying): drivers given 0.4–0.6 finish top 3 more often than stated (0.49 → 0.62), as do those given 0.6–0.8 (0.67 → 0.79), while drivers given 0.2–0.4 do so less often (0.31 → 0.21).
- Live path: 16 dry races, 322 driver-races, error **0.573%**, identical to the backtest (largest difference 0.0000%).
- A small leak found later: the decision replay used each race's real length, which differed at Montreal 2026 (68 laps instead of 70). The live path does not know this and takes `--race-laps`.

## 6. Interpretation
Rows from the same race share conditions, so a random split rewards copying rather than forecasting. Ordering by race date and hiding checkpoint columns in code makes leakage a test failure, not a matter of discipline. Building ranges from the model's own recent errors makes them widen when the model becomes less accurate, which is the honest behaviour after a rules change, at the cost of a lag of a few races. Flat chances are probably caused by drawing each driver's error independently: a shared weekend error moves everyone together and should not reshuffle the order.

## 7. Decision influenced
- Walk-forward backtesting by race date is the only evaluation used for model choices ([`src/dpec/forecasting/backtest.py`](../../../src/dpec/forecasting/backtest.py)).
- Ranges and chances as implemented in [`ranges.py`](../../../src/dpec/forecasting/ranges.py) and [`simulate.py`](../../../src/dpec/forecasting/simulate.py); a forecast is repeatable because the seed is fixed.
- The same functions run in `dpec freeze`, so the live path is the tested path ([decision 0015](../../decisions/0015-public-record.md)).
- Published guidance: for the first races of a new rules era, treat ranges as too narrow.

## 8. Known limitations
- A backtest is still run after the fact by the model's author. The public record was built to address this, but has 0 live weekends ([case 09](09-release-deployment-data-access.md), [live-weekends.md](../../live-weekends.md)).
- Chances are too flat. Future fix: draw a whole past weekend's errors together.
- Beating the teammate is barely better than a coin (Brier 0.219 against 0.25).
- The replay's race-length leak is documented, not removed, in the replay results.

## 9. Evidence and implementation
- Code: [`targets.py`](../../../src/dpec/forecasting/targets.py), [`backtest.py`](../../../src/dpec/forecasting/backtest.py), [`ranges.py`](../../../src/dpec/forecasting/ranges.py), [`simulate.py`](../../../src/dpec/forecasting/simulate.py), [`record/freeze.py`](../../../src/dpec/record/freeze.py)
- Results: [`reports/backtest/scores.csv`](../../../reports/backtest/scores.csv), [`ranges.csv`](../../../reports/backtest/ranges.csv)
- Notebook (original): [`notebooks/03_forecast/c3_ranges_and_chances.ipynb`](../../../notebooks/03_forecast/c3_ranges_and_chances.ipynb). It shows an earlier no-information Brier of 0.132; the corrected value is 0.131 ([numbers-check](../../../reports/numbers-check.md#corrections-made))
- Tests: [`tests/dpec/test_forecasting.py`](../../../tests/dpec/test_forecasting.py) (`test_walk_forward_never_sees_the_future`, `test_a_forecaster_cannot_read_todays_answer`), [`test_ranges.py`](../../../tests/dpec/test_ranges.py), [`test_record.py`](../../../tests/dpec/test_record.py)
- Summary: [model card](../../model-card.md) · Narrative: [methods.md § 7](../../methods.md#7-the-forecaster), [§ 9](../../methods.md#9-in-public-frozen-before-the-race-scored-after)
- How it works now: [workstream 03 · Forecasting and machine learning](../../workstreams/03-forecasting-machine-learning.md) · [workstream 04 · ML engineering](../../workstreams/04-ml-engineering.md)

Previous: [Case 06](06-shared-vs-separate-models.md) · Next: [Case 08 · Strategy modelling](08-strategy-modelling.md)
