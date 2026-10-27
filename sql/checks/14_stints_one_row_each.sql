-- mart_stints: one row per session + driver + stint, and the laps add up to core_laps.
WITH per_driver AS (
    SELECT session_key, driver_code, sum(n_laps) AS stint_laps, count(*) AS n, count(DISTINCT stint) AS stints
    FROM mart_stints
    GROUP BY ALL
),

laps AS (
    SELECT session_key, driver_code, count(*) AS laps
    FROM core_laps
    WHERE stint IS NOT NULL
    GROUP BY ALL
)

SELECT *
FROM per_driver AS p
FULL JOIN laps AS l USING (session_key, driver_code)
WHERE p.n IS DISTINCT FROM p.stints OR p.stint_laps IS DISTINCT FROM l.laps
