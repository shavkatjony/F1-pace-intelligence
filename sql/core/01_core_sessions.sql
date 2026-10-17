--  core_session: one row per session (FP1, FP2, FP3, SQ, S, Q, R) of every saved weekend.
-- Built from the manifest.json files that `dpec ingest` wrote.

CREATE OR REPLACE TABLE core_sessions AS 
WITH manifests AS (
    SELECT
        CAST(season AS INTEGER) AS season,
        CAST(info ->> 'round' AS INTEGER) AS round,
        info ->> 'event' AS event_name,
        info -> 'session_info' -> 'Meeting' -> 'Circuit' ->> 'ShortName' AS circuit,
        info ->> 'session' AS session_name,
        CAST(info ->> 'session_date_utc' AS TIMESTAMP) AS session_date_utc,
        event AS event_folder,
        session AS session_folder
    FROM read_json(
        '{{ raw }}/fastf1/*/*/*/manifest.json',
        columns = {'info': 'JSON'},
        hive_partitioning = true
    )
),

typed AS (
    SELECT
        *,
        CASE session_name
            WHEN 'Practice 1' THEN 'FP1'
            WHEN 'Practice 2' THEN 'FP2'
            WHEN 'Practice 3' THEN 'FP3'
            WHEN 'Sprint Shootout' THEN 'SQ'    -- 2023 name
            WHEN 'Sprint Qualifying' THEN 'SQ'  -- 2024+ name
            WHEN 'Sprint' THEN 'S'
            WHEN 'Qualifying' THEN 'Q'
            WHEN 'Race' THEN 'R'
            ELSE error('unknown session name: ' || session_name)
        END AS session_type
    FROM manifests
)

SELECT
    printf('%d_%02d_%s', season, round, session_type) AS session_key,
    season,
    round,
    event_name,
    circuit,
    session_name,
    session_type,
    session_date_utc,
    bool_or(session_type = 'S') OVER (PARTITION BY season, round) AS is_sprint_weekend,
    event_folder,
    session_folder
FROM typed
ORDER BY season, round, session_date_utc;