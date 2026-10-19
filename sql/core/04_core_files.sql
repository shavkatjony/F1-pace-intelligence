-- core_files: one row per saved table per session, from the manifests.
-- Shows at a glance what we have, and what came back empty from FastF1.
CREATE OR REPLACE TABLE core_files AS
WITH manifests AS (
    SELECT
        CAST(season AS INTEGER) AS season,
        event AS event_folder,
        session AS session_folder,
        CAST(saved_at_utc AS TIMESTAMP) AS saved_at_utc,
        files
    FROM read_json(
        '{{ raw }}/fastf1/*/*/*/manifest.json',
        columns = {'saved_at_utc': 'VARCHAR', 'files': 'JSON'},
        hive_partitioning = true
    )
),

one_row_per_table AS (
    SELECT *, unnest(json_keys(files)) AS table_name
    FROM manifests
)

SELECT
    s.session_key,
    t.table_name,
    CAST(t.files -> t.table_name ->> 'rows' AS BIGINT) AS n_rows,
    n_rows = 0 AS is_empty,
    t.files -> t.table_name ->> 'sha256' AS sha256,
    t.saved_at_utc
FROM one_row_per_table AS t
INNER JOIN core_sessions AS s
    ON s.season = t.season
    AND s.event_folder = t.event_folder
    AND s.session_folder = t.session_folder
ORDER BY s.session_key, t.table_name;


-- json_keys(files) lists the table names in one manifest (laps, car_data, …). unnest turns that list into one row per table.
-- files -> table_name ->> 'rows' reads that table's row count from the JSON.
-- sha256 is the fingerprint of the file. If it ever changes for a saved session, the data changed.