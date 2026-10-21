-- The last row of each driver's season in mart_standings = all his race and sprint points.
WITH final AS (
    SELECT season, driver_code, total_points
    FROM mart_standings
    QUALIFY round = max(round) OVER (PARTITION BY season, driver_code)
),

official AS (
    SELECT season, driver_code, sum(points) AS points
    FROM core_results
    WHERE session_type IN ('R', 'S')
    GROUP BY ALL
)

SELECT o.season, o.driver_code, o.points, f.total_points
FROM official AS o
LEFT JOIN final AS f USING (season, driver_code)
WHERE f.total_points IS DISTINCT FROM o.points
