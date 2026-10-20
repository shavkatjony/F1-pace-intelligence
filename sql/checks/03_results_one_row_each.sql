-- core_results: one row per session + driver.
SELECT session_key, driver_code, count(*) AS n
FROM core_results
GROUP BY ALL
HAVING n > 1
