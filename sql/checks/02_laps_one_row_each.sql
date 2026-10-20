-- core_laps: one row per session + driver + lap.
SELECT session_key, driver_code, lap_number, count(*) AS n
FROM core_laps
GROUP BY ALL
HAVING n > 1
