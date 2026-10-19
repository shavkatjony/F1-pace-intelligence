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
)

SELECT
    s.session_key,
    s.season,
    s.round,
    s.session_type,
    r.Abbreviation AS driver_code,
    r.DriverId AS driver_id,           -- Jolpica's id, e.g. 'max_verstappen'
    r.DriverNumber AS car_number,
    r.FullName AS driver_name,
    r.TeamName AS team,
    r.TeamId AS team_id,
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
ORDER BY s.session_key, finish_position;

-- Same pattern as core_laps: read every results.parquet, join to core_sessions by folder, give clear names.
-- classified stays text, because it isn't always a number: R retired, D disqualified, W withdrew (didn't start).
-- driver_id is Jolpica's id. It becomes the base of the driver ID map in step A6.
-- Practice sessions are left out: they have no official order.
