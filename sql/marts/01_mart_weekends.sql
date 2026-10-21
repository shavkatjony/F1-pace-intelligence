-- mart_weekends: one row per race weekend. The overview table.
-- Key: season + round.
CREATE OR REPLACE TABLE mart_weekends AS
WITH races AS (
    SELECT * FROM core_sessions WHERE session_type = 'R'
),

race_results AS (
    SELECT
        session_key,
        max(driver_code) FILTER (WHERE finish_position = 1) AS winner,
        max(team) FILTER (WHERE finish_position = 1) AS winner_team,
        max(laps_completed) AS race_laps,
        count(*) FILTER (WHERE classified IN ('R', 'D', 'W')) AS not_classified
    FROM core_results
    WHERE session_type = 'R'
    GROUP BY session_key
),

poles AS (
    SELECT season, round, driver_code AS pole
    FROM core_results
    WHERE session_type = 'Q' AND finish_position = 1
),

race_laps AS (
    SELECT
        session_key,
        count(DISTINCT lap_number) FILTER (WHERE under_safety_car) AS safety_car_laps,
        count(DISTINCT lap_number) FILTER (WHERE under_vsc) AS vsc_laps,
        bool_or(under_red_flag) AS had_red_flag,
        avg(CAST(on_wet_tyre AS INTEGER)) AS wet_tyre_share,
        avg(CAST(is_clean AS INTEGER)) AS clean_share
    FROM core_laps
    WHERE session_type = 'R'
    GROUP BY session_key
)

SELECT
    r.season,
    r.round,
    r.event_name,
    r.circuit,
    CAST(r.session_date_utc AS DATE) AS race_date,
    r.is_sprint_weekend,
    p.pole,
    rr.winner,
    rr.winner_team,
    rr.race_laps,
    rr.not_classified,
    rl.safety_car_laps,
    rl.vsc_laps,
    rl.had_red_flag,
    round(rl.wet_tyre_share, 3) AS wet_tyre_share,
    rl.wet_tyre_share > 0.1 AS is_wet_race,  -- more than 1 lap in 10 on intermediates or wets
    round(rl.clean_share, 3) AS clean_share
FROM races AS r
LEFT JOIN race_results AS rr USING (session_key)
LEFT JOIN poles AS p USING (season, round)
LEFT JOIN race_laps AS rl USING (session_key)
ORDER BY r.season, r.round;
