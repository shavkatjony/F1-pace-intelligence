-- core_results: one row per driver per race, sprint, qualifying and sprint qualifying.
-- FastF1 fills these from Jolpica (the official classification), so penalties and
-- disqualifications decided after the session are already in.
CREATE OR REPLACE TABLE core_results AS
WITH raw_results AS (
    SELECT *
    FROM read_parquet(
        '{{ raw }}/fastf1/*/*/*/results.parquet',
        hive_partitioning = true,
        union_by_name = true
    )
),

teams AS (
    SELECT * FROM read_csv('{{ seeds }}/teams.csv')
),

renamed AS (
    SELECT
        s.session_key,
        s.season,
        s.round,
        s.session_type,
        r.Abbreviation AS driver_code,
        -- Jolpica's id, e.g. 'max_verstappen'. Empty in sprint qualifying, 'nan' for
        -- a few qualifying no-shows; both become NULL and are filled below.
        nullif(nullif(r.DriverId, ''), 'nan') AS driver_id_raw,
        r.DriverNumber AS car_number,
        r.FullName AS driver_name,
        r.TeamName AS team,
        CAST(r.GridPosition AS INTEGER) AS grid_position,  -- 0 = started from the pit lane
        CAST(r.Position AS INTEGER) AS finish_position,
        r.ClassifiedPosition AS classified,  -- a number, or R retired, D disqualified, W withdrew
        r.Status AS status,
        r.Points AS points,
        CAST(r.Laps AS INTEGER) AS laps_completed,
        r.Q1 AS q1_s,
        r.Q2 AS q2_s,
        r.Q3 AS q3_s
    FROM raw_results AS r
    INNER JOIN core_sessions AS s
        ON s.season = r.season
        AND s.event_folder = r.event
        AND s.session_folder = r.session
    WHERE s.session_type IN ('R', 'S', 'Q', 'SQ')
)

SELECT
    r.* EXCLUDE (driver_id_raw, team),
    -- a driver code means one driver within a season, so borrow the id from his other sessions
    coalesce(
        r.driver_id_raw,
        max(r.driver_id_raw) OVER (PARTITION BY r.season, r.driver_code)
    ) AS driver_id,
    r.team,
    t.team_id,  -- from seeds/teams.csv, so it is never empty
FROM renamed AS r
LEFT JOIN teams AS t
    ON t.team_name = r.team
ORDER BY r.session_key, r.finish_position;

-- Same pattern as core_laps: read every results.parquet, join to core_sessions by folder, give clear names.
-- classified stays text, because it isn't always a number: R retired, D disqualified, W withdrew (didn't start).
-- Practice sessions are left out: they have no official order.

