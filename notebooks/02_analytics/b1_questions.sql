-- 1. Wet races and red flags per season
SELECT
    season,
    count(*) FILTER (WHERE is_wet_race) AS wet_races,
    count(*) FILTER (WHERE had_red_flag) AS red_flag_races
FROM mart_weekends
GROUP BY season
ORDER BY season;

-- 2. How often does pole win?
SELECT
    season,
    round(avg(CAST(pole = winner AS INTEGER)), 2) AS pole_win_share
FROM mart_weekends
WHERE winner IS NOT NULL
GROUP BY season
ORDER BY season;

-- 3. How close was each title? (P1 minus P2 after the last round)
WITH last_round AS (
    SELECT *
    FROM mart_standings
    QUALIFY round = max(round) OVER (PARTITION BY season)
)
SELECT
    season,
    max(total_points) FILTER (WHERE championship_position = 1)
      - max(total_points) FILTER (WHERE championship_position = 2) AS title_margin
FROM last_round
GROUP BY season
ORDER BY season;

-- 4. How many sessions had rain at some point?
SELECT
    count(*) FILTER (WHERE had_rain) AS sessions_with_rain,
    count(*) AS all_sessions
FROM mart_session_weather;
