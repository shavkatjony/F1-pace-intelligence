-- dim_drivers: one row per driver per season. The driver ID map.
-- Key: season + driver_code (a code like VER means one driver within a season).
-- driver_id is NULL for FP1 stand-ins who never started a race or qualifying.
CREATE OR REPLACE TABLE dim_drivers AS
WITH seen AS (
    SELECT DISTINCT season, driver_code, car_number, team, session_type
    FROM core_laps
    UNION
    SELECT DISTINCT season, driver_code, car_number, team, session_type
    FROM core_results
),

ids AS (
    SELECT season, driver_code, max(driver_id) AS driver_id, max(driver_name) AS driver_name
    FROM core_results
    GROUP BY ALL
)

SELECT
    s.season,
    s.driver_code,
    i.driver_id,
    i.driver_name,
    list(DISTINCT s.car_number ORDER BY s.car_number) AS car_numbers,
    list(DISTINCT s.team ORDER BY s.team) AS teams,  -- more than one = changed team mid-season
    bool_or(s.session_type = 'R') AS started_a_race
FROM seen AS s
LEFT JOIN ids AS i
    ON i.season = s.season
    AND i.driver_code = s.driver_code
GROUP BY ALL
ORDER BY s.season, s.driver_code;
