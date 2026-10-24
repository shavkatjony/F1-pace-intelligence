-- mart_weekend_signals: one row per driver per race weekend. What practice and qualifying said,
-- next to what happened on Sunday. The table for the research question in step B3.
-- Key: season + round + driver_code. All pace numbers are % behind the best of that session (0 = best).
CREATE OR REPLACE TABLE mart_weekend_signals AS
WITH long_runs AS (
    -- each driver's long runs of the weekend, as % behind the best run on the same tyre
    SELECT
        season,
        round,
        driver_code,
        count(*) AS n_long_runs,
        median(gap_to_best_same_tyre_pct) AS long_run_gap_pct,
        median(deg_s_per_lap) AS long_run_deg_s_per_lap
    FROM mart_long_runs
    GROUP BY ALL
),

quali AS (
    SELECT season, round, driver_code, gap_to_best_pct AS quali_gap_pct
    FROM mart_driver_session_pace
    WHERE session_type = 'Q'
),

race AS (
    -- race pace: median clean lap, as % behind the driver with the best median
    SELECT
        season,
        round,
        driver_code,
        team,
        clean_laps AS race_clean_laps,
        round(100 * (median_lap_s / min(median_lap_s) OVER (PARTITION BY season, round) - 1), 3)
            AS race_pace_gap_pct
    FROM mart_driver_session_pace
    WHERE session_type = 'R'
        AND clean_laps >= 10  -- fewer clean laps than that is not a race pace
),

finish AS (
    SELECT season, round, driver_code, finish_position, grid_position, points
    FROM core_results
    WHERE session_type = 'R'
)

SELECT
    r.season,
    r.round,
    r.driver_code,
    r.team,
    w.is_sprint_weekend,
    w.is_wet_race,
    lr.n_long_runs,
    lr.long_run_gap_pct,
    lr.long_run_deg_s_per_lap,
    q.quali_gap_pct,
    r.race_clean_laps,
    r.race_pace_gap_pct,
    f.grid_position,
    f.finish_position,
    f.points
FROM race AS r
INNER JOIN mart_weekends AS w USING (season, round)
LEFT JOIN long_runs AS lr USING (season, round, driver_code)
LEFT JOIN quali AS q USING (season, round, driver_code)
LEFT JOIN finish AS f USING (season, round, driver_code)
ORDER BY r.season, r.round, r.race_pace_gap_pct;
