-- mart_driver_session_pace: one row per session + driver, and exactly one driver at 0%.
SELECT session_key, count(*) FILTER (WHERE gap_to_best_pct = 0) AS fastest, count(*) AS n,
    count(DISTINCT driver_code) AS drivers
FROM mart_driver_session_pace
GROUP BY session_key
HAVING fastest < 1 OR n <> drivers
