-- mart_race_strategy: one row per race weekend. What practice said about tyre wear, next to
-- what the race showed: tyre wear, the time a pit stop costs, and how often the top 10 stopped.
-- The table the decision layer (step C4) learns from. Key: season + round.
CREATE OR REPLACE TABLE mart_race_strategy AS
WITH race_laps AS (
    SELECT * FROM core_laps WHERE session_type = 'R'
),

normal_lap AS (
    -- each driver's normal race lap: the median of his clean laps
    SELECT season, round, driver_code, median(lap_time_s) AS normal_lap_s
    FROM race_laps
    WHERE is_clean
    GROUP BY ALL
),

pit_stops AS (
    -- one row per stop: the in-lap, next to the lap after it (the out-lap)
    SELECT
        i.season,
        i.round,
        i.driver_code,
        i.lap_time_s + o.lap_time_s - 2 * n.normal_lap_s AS loss_s,
        -- under a safety car everyone is slow, so a stop costs less: not a normal stop
        (i.under_safety_car OR i.under_vsc OR i.under_red_flag
            OR o.under_safety_car OR o.under_vsc OR o.under_red_flag) AS neutralised
    FROM race_laps AS i
    INNER JOIN race_laps AS o
        ON o.session_key = i.session_key
        AND o.driver_code = i.driver_code
        AND o.lap_number = i.lap_number + 1
    INNER JOIN normal_lap AS n
        ON n.season = i.season AND n.round = i.round AND n.driver_code = i.driver_code
    WHERE i.is_in_lap AND o.is_out_lap
),

pit_loss AS (
    SELECT
        season,
        round,
        count(*) FILTER (WHERE NOT neutralised AND loss_s IS NOT NULL) AS green_stops,
        median(loss_s) FILTER (WHERE NOT neutralised) AS pit_loss_s
    FROM pit_stops
    GROUP BY ALL
),

practice_wear AS (
    -- known before the race: tyre wear in this weekend's practice long runs (all teams)
    SELECT
        season,
        round,
        count(*) AS practice_long_runs,
        median(deg_s_per_lap) AS practice_deg_s_per_lap
    FROM mart_long_runs
    WHERE compound IN ('SOFT', 'MEDIUM', 'HARD')
    GROUP BY ALL
),

race_wear AS (
    -- the answer: tyre wear in the race, from stints with enough clean laps to measure it
    SELECT
        season,
        round,
        count(*) AS race_stints,
        median(deg_s_per_lap) AS race_deg_s_per_lap
    FROM mart_stints
    WHERE session_type = 'R'
        AND compound IN ('SOFT', 'MEDIUM', 'HARD')
        AND n_clean >= 8
    GROUP BY ALL
),

top10_stops AS (
    -- the answer: the most common number of stops among the top 10 finishers
    SELECT season, round, mode(stops) AS top10_stops
    FROM (
        SELECT s.season, s.round, s.driver_code, count(*) - 1 AS stops
        FROM mart_stints AS s
        INNER JOIN core_results AS r
            ON r.season = s.season AND r.round = s.round AND r.driver_code = s.driver_code
            AND r.session_type = 'R'
        WHERE s.session_type = 'R' AND r.finish_position <= 10
        GROUP BY ALL
    )
    GROUP BY ALL
)

SELECT
    w.season,
    w.round,
    w.circuit,
    w.race_date,
    w.race_laps,
    w.is_wet_race,
    w.safety_car_laps,
    w.vsc_laps,
    pw.practice_long_runs,
    round(pw.practice_deg_s_per_lap, 4) AS practice_deg_s_per_lap,
    rw.race_stints,
    round(rw.race_deg_s_per_lap, 4) AS race_deg_s_per_lap,
    pl.green_stops,
    round(pl.pit_loss_s, 2) AS pit_loss_s,
    t.top10_stops
FROM mart_weekends AS w
LEFT JOIN practice_wear AS pw USING (season, round)
LEFT JOIN race_wear AS rw USING (season, round)
LEFT JOIN pit_loss AS pl USING (season, round)
LEFT JOIN top10_stops AS t USING (season, round)
ORDER BY w.season, w.round;
