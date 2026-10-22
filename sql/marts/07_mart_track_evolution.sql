-- mart_track_evolution: how much faster the track gets during a session, as rubber goes down.
-- One row per practice, qualifying and sprint qualifying session. Key: session_key.
-- Races are left out: there the car gets lighter and the tyres wear at the same time.
--
-- Method: take each driver's push laps (clean laps within {{ push_lap_band_pct }}% of his best on
-- that compound). Compare every lap with the same driver's other laps on the same compound, so
-- car, driver and tyre drop out ("fixed effects"). What is left changes with the clock.
CREATE OR REPLACE TABLE mart_track_evolution AS
WITH push_laps AS (
    SELECT session_key, season, round, session_type, driver_code, compound, lap_time_s,
        lap_start_session_s / 60 AS minute
    FROM core_laps
    WHERE is_clean
        AND session_type IN ('FP1', 'FP2', 'FP3', 'Q', 'SQ')
    QUALIFY lap_time_s <= (1 + {{ push_lap_band_pct }} / 100)
        * min(lap_time_s) OVER (PARTITION BY session_key, driver_code, compound)
),

within_driver AS (
    -- lap time and clock time, each minus the driver + compound average
    SELECT
        *,
        lap_time_s - avg(lap_time_s) OVER g AS lap_vs_own_avg_s,
        minute - avg(minute) OVER g AS minute_vs_own_avg,
        count(*) OVER g AS laps_in_group
    FROM push_laps
    WINDOW g AS (PARTITION BY session_key, driver_code, compound)
),

evolution AS (
    SELECT
        session_key,
        season,
        round,
        session_type,
        count(DISTINCT driver_code) AS n_drivers,
        count(*) AS n_laps,
        round(10 * regr_slope(lap_vs_own_avg_s, minute_vs_own_avg), 3) AS evo_s_per_10min
    FROM within_driver
    WHERE laps_in_group >= 2  -- one lap alone says nothing about change
    GROUP BY ALL
),

wet_laps AS (
    SELECT session_key, avg(CAST(on_wet_tyre AS INTEGER)) AS wet_lap_share
    FROM core_laps
    GROUP BY session_key
),

quali_steps AS (
    -- the same drivers' best times from one part of qualifying to the next
    SELECT
        session_key,
        median(q2_s - q1_s) AS q1_to_q2_s,
        median(q3_s - q2_s) AS q2_to_q3_s
    FROM core_results
    WHERE session_type IN ('Q', 'SQ')
    GROUP BY session_key
)

SELECT
    e.*,
    q.q1_to_q2_s,
    q.q2_to_q3_s,
    w.track_temp_min_c,
    w.track_temp_max_c,
    w.had_rain,
    round(wl.wet_lap_share, 3) AS wet_lap_share,
    -- a drying track gets seconds faster, which is not rubber going down; few drivers = noise
    NOT coalesce(w.had_rain, false) AND wl.wet_lap_share < 0.1 AND e.n_drivers >= 10
        AS is_reliable
FROM evolution AS e
LEFT JOIN quali_steps AS q USING (session_key)
LEFT JOIN mart_session_weather AS w USING (session_key)
LEFT JOIN wet_laps AS wl USING (session_key)
ORDER BY e.session_key;

