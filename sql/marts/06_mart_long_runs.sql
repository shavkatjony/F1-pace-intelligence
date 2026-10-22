-- mart_long_runs: practice stints that look like race running.
-- Key: session_key + driver_code + stint.
-- A long run = at least {{ long_run_min_laps }} clean laps within {{ long_run_band_pct }}% of the
-- stint's median clean lap (push laps and traffic laps fall outside the band).
CREATE OR REPLACE TABLE mart_long_runs AS
WITH practice_laps AS (
    SELECT
        l.*,
        s.median_clean_s,
        s.compound,
        s.tyre_age_start
    FROM core_laps AS l
    INNER JOIN mart_stints AS s USING (session_key, driver_code, stint)
    WHERE l.session_type IN ('FP1', 'FP2', 'FP3')
        AND l.is_clean
        AND s.compound IN ('SOFT', 'MEDIUM', 'HARD')
),

in_band AS (
    SELECT
        *,
        lap_number - min(lap_number) OVER (PARTITION BY session_key, driver_code, stint)
            AS laps_into_run
    FROM practice_laps
    WHERE abs(lap_time_s / median_clean_s - 1) * 100 <= {{ long_run_band_pct }}
),

runs AS (
    SELECT
        session_key,
        season,
        round,
        session_type,
        driver_code,
        stint,
        max(team) AS team,
        max(compound) AS compound,
        max(tyre_age_start) AS tyre_age_start,
        count(*) AS run_laps,
        median(lap_time_s) AS run_median_s,
        -- the same, with the fuel burnt during the run taken out: every lap is moved back
        -- to the car's weight on the first lap of the run
        median(lap_time_s + {{ fuel_effect_s_per_lap }} * laps_into_run) AS run_median_fuel_adj_s,
        regr_slope(lap_time_s, tyre_age_laps) + {{ fuel_effect_s_per_lap }} AS deg_s_per_lap
    FROM in_band
    GROUP BY ALL
    HAVING count(*) >= {{ long_run_min_laps }}
)

SELECT
    *,
    -- gap to the quickest long run of the session on the same compound, in percent
    round(100 * (run_median_s / min(run_median_s) OVER (PARTITION BY session_key, compound) - 1), 3)
        AS gap_to_best_same_tyre_pct
FROM runs
ORDER BY session_key, compound, run_median_s;
