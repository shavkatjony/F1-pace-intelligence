-- mart_weekend_signals: one row per weekend + driver, and one driver at 0% race pace per weekend.
SELECT season, round, count(*) AS n, count(DISTINCT driver_code) AS drivers,
    count(*) FILTER (WHERE race_pace_gap_pct = 0) AS fastest
FROM mart_weekend_signals
GROUP BY ALL
HAVING n <> drivers OR fastest < 1
