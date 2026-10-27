-- mart_session_weather: one row per session. Weather summed up from the raw weather files
-- (one sample a minute). Key: session_key.
CREATE OR REPLACE TABLE mart_session_weather AS
WITH raw_weather AS (
    -- a track temperature of exactly 0.0 is a sensor dropout (47 of 54,295 samples), not weather
    SELECT * REPLACE (nullif(TrackTemp, 0) AS TrackTemp)
    FROM read_parquet(
        '{{ raw }}/fastf1/*/*/*/weather.parquet',
        hive_partitioning = true,
        union_by_name = true
    )
)

SELECT
    s.session_key,
    s.season,
    s.round,
    s.session_type,
    count(*) AS n_samples,
    round(median(w.AirTemp), 1) AS air_temp_c,
    round(min(w.TrackTemp), 1) AS track_temp_min_c,
    round(median(w.TrackTemp), 1) AS track_temp_c,
    round(max(w.TrackTemp), 1) AS track_temp_max_c,
    round(median(w.Humidity), 0) AS humidity_pct,
    round(median(w.WindSpeed), 1) AS wind_speed_ms,
    round(avg(CAST(w.Rainfall AS INTEGER)), 3) AS rain_share,  -- share of minutes with rain
    bool_or(w.Rainfall) AS had_rain
FROM raw_weather AS w
INNER JOIN core_sessions AS s
    ON s.season = CAST(w.season AS INTEGER)
    AND s.event_folder = w.event
    AND s.session_folder = w.session
GROUP BY ALL
ORDER BY s.session_key;
