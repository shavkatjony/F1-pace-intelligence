-- mart_standings: the drivers' championship after every round.
-- One row per driver per round they scored or started in. Key: season + round + driver_code.
CREATE OR REPLACE TABLE mart_standings AS
WITH points_per_round AS (
    -- race and sprint points of the weekend added together
    SELECT
        season,
        round,
        driver_code,
        max(team) FILTER (WHERE session_type = 'R') AS team,
        sum(points) AS round_points,
        count(*) FILTER (WHERE session_type = 'R' AND finish_position = 1) AS round_wins
    FROM core_results
    WHERE session_type IN ('R', 'S')
    GROUP BY season, round, driver_code
),

running AS (
    SELECT
        *,
        sum(round_points) OVER (
            PARTITION BY season, driver_code ORDER BY round
        ) AS total_points,
        sum(round_wins) OVER (
            PARTITION BY season, driver_code ORDER BY round
        ) AS total_wins
    FROM points_per_round
)

SELECT
    *,
    -- the championship order after this round: most points, then most wins
    rank() OVER (
        PARTITION BY season, round ORDER BY total_points DESC, total_wins DESC
    ) AS championship_position
FROM running
ORDER BY season, round, championship_position;
