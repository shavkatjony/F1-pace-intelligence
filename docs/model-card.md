# Model card · DPEC race pace forecaster

Updated: 2026-10-24 · Decisions 0011, 0012, 0013

## What it forecasts
Each car's race pace in a dry Grand Prix: the median clean race lap, in % behind the fastest
car that day. Made twice per weekend, after practice and after qualifying, with an 80% range
and chances: best race pace, top-3 race pace, beating the teammate.

## Use it for / not for
- For: what to expect on Sunday, before the race; the input to the decision packet (step C4).
- Not for: wet races (not forecast, decision 0011); finishing positions (starts, safety cars,
  strategy and reliability decide those); one-lap pace; the first races of a new rules era
  without extra care (see limits).

## Data
FastF1 timing, 2022–2026 (545 sessions). Dry races only. 2022 only teaches; forecasts start
in 2023. 1,846 driver-weekends.

## How it works
One weighted regression for every track and year (decision 0012). After practice: team form
+ driver vs team. After qualifying: + the qualifying gap. Inputs come only from earlier races;
refitted before every weekend; newer races weigh more (half-life 12 races).
Ranges: the 80th percentile of the size of its errors over the last 10 forecast weekends
(split-conformal, walk-forward). Chances: 4,000 replays of the race order (decision 0013).

## How good it is (settings chosen on 2023–24, reported on 2025–26: 37 weekends)
|                         | after practice   | after qualifying  |
|-------------------------|------------------|-------------------|
| shared model, error     | 0.648% (0.58 s)  | 0.548% (0.49 s)   |
| best simple guess       | 0.674% team form | 0.589% per-year   |
| order (median Spearman) | 0.767            | 0.821             |
| inside the 80% range    | 78.5%            | 79.9%             |
| top-3 chance, Brier (all years) | 0.084 (none: 0.132) | 0.077 (none: 0.132) |

## Which inputs matter (all years, error after practice / after qualifying)
Full 0.556 / 0.498 · without team form 0.871 / 0.593 · without the quali gap – / 0.557 ·
without driver vs team 0.567 / 0.503 · without recency weights 0.553 / 0.513.

## Known limits
- New rules era: in 2026 races 1–5, simple guesses did as well, and only 68% of race paces
  were inside the range after practice (the ranges catch up a few races later).
- Chances are a bit too flat: favourites make the top 3 more often than said (0.67 → 0.79),
  the next group less (0.31 → 0.21). Probably because each driver's error is drawn on its own.
- Beating the teammate: barely better than a coin (Brier 0.219 vs 0.25).
- Order: the per-year line ranks drivers slightly better after qualifying (0.843 vs 0.821).
- No inputs for tyres, fuel strategy, weather, upgrades or penalties.