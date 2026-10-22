-- mart_stints: one row per set of tyres a driver used in a session.
-- Key: session_key + driver_code + stint.
-- deg = how much slower each lap gets as the tyre ages, on clean laps only.
CREATE OR REPLACE TABLE mart_stints AS
WITH laps AS (
    SELECT
        *,
        -- FastF1 also writes TEST_UNKNOWN (test tyres in practice), 'nan', '' and NULL
        CASE
            WHEN compound IN ('SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET') THEN compound
            ELSE 'UNKNOWN'
        END AS tyre
    FROM core_laps
    WHERE stint IS NOT NULL
),

stints AS (
    SELECT
        session_key,
        season,
        round,
        session_type,
        driver_code,
        stint,
        max(team) AS team,
        mode(tyre) AS compound,                     -- the most common name in the stint
        min(lap_number) AS first_lap,
        max(lap_number) AS last_lap,
        count(*) AS n_laps,
        min(tyre_age_laps) AS tyre_age_start,       -- > 1 = a used set
        bool_or(fresh_tyre) AS fresh_at_start,
        count(*) FILTER (WHERE is_clean) AS n_clean,
        median(lap_time_s) FILTER (WHERE is_clean) AS median_clean_s,
        -- seconds per lap of tyre age; needs a few clean laps to mean anything
        CASE WHEN count(*) FILTER (WHERE is_clean) >= 4
            THEN regr_slope(lap_time_s, tyre_age_laps) FILTER (WHERE is_clean)
        END AS deg_raw_s_per_lap
    FROM laps
    GROUP BY ALL
)

SELECT
    *,
    -- the car gets lighter every lap and that hides tyre wear, so add the fuel effect back
    deg_raw_s_per_lap + {{ fuel_effect_s_per_lap }} AS deg_s_per_lap
FROM stints
ORDER BY session_key, driver_code, stint;
