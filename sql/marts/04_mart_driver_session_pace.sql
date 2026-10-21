-- mart_driver_session_pace: how fast each driver was in each session, on clean laps only.
-- One row per driver per session with at least one clean lap. Key: session_key + driver_code.
CREATE OR REPLACE TABLE mart_driver_session_pace AS
WITH per_driver AS (
    SELECT
        session_key,
        season,
        round,
        session_type,
        driver_code,
        max(team) AS team,
        count(*) AS clean_laps,
        min(lap_time_s) AS best_lap_s,
        median(lap_time_s) AS median_lap_s
    FROM core_laps
    WHERE is_clean
    GROUP BY ALL
)

SELECT
    *,
    -- how far from the fastest lap of the session, in percent (0 = the fastest driver)
    round(100 * (best_lap_s / min(best_lap_s) OVER (PARTITION BY session_key) - 1), 3)
        AS gap_to_best_pct,
    rank() OVER (PARTITION BY session_key ORDER BY best_lap_s) AS pace_rank
FROM per_driver
ORDER BY session_key, pace_rank;