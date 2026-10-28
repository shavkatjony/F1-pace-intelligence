-- mart_race_strategy has one row per race weekend. Returns the weekends that appear twice.
SELECT season, round, count(*) AS n_rows
FROM mart_race_strategy
GROUP BY ALL
HAVING count(*) > 1
