-- core_laps: one row per driver per lap per session.
-- Every lap gets yes/no flags and ONE reason code: 'clean' or the first rule it breaks.
CREATE OR REPLACE TABLE core_laps AS
WITH raw_laps AS (
    SELECT *
    FROM read_parquet(
        '{{ raw }}/fastf1/*/*/*/laps.parquet',
        hive_partitioning = true,
        union_by_name = true
    )
),

renamed AS (
    SELECT
        s.session_key,
        s.season,
        s.round,
        s.session_type,
        l.Driver AS driver_code,
        l.DriverNumber AS car_number,
        nullif(l.Team, '') AS team_raw,  -- empty in 2026 rounds 5 and 7 FP1, filled below
        CAST(l.LapNumber AS INTEGER) AS lap_number,
        CAST(l.Stint AS INTEGER) AS stint,
        l.Compound AS compound,
        CAST(l.TyreLife AS INTEGER) AS tyre_age_laps,
        l.FreshTyre AS fresh_tyre,
        l.LapTime AS lap_time_s,
        l.Sector1Time AS sector1_s,
        l.Sector2Time AS sector2_s,
        l.Sector3Time AS sector3_s,
        l.SpeedST AS speed_trap_kph,
        CAST(l.Position AS INTEGER) AS position,
        l.LapStartTime AS lap_start_session_s,
        l.Time AS lap_end_session_s,
        l.LapStartDate AS lap_start_utc,
        coalesce(l.TrackStatus, '') AS track_status,
        l.DeletedReason AS deleted_reason,
        -- yes/no flags, one per rule
        l.PitInTime IS NOT NULL AS is_in_lap,
        l.PitOutTime IS NOT NULL AS is_out_lap,
        coalesce(l.Deleted, false) AS is_deleted,
        coalesce(l.FastF1Generated, false) AS is_generated,
        coalesce(l.IsAccurate, false) AS is_accurate
    FROM raw_laps AS l
    INNER JOIN core_sessions AS s
        ON s.season = l.season
        AND s.event_folder = l.event
        AND s.session_folder = l.session
),

teams_filled AS (
    SELECT
        * EXCLUDE (team_raw),
        coalesce(
            team_raw,
            -- 1. the same driver's team in another session of the same weekend
            max(team_raw) OVER (PARTITION BY season, round, driver_code),
            -- 2. FP1 stand-ins: the same driver with the same car number this season
            max(team_raw) OVER (PARTITION BY season, driver_code, car_number)
        ) AS team
    FROM renamed
),

flagged AS (
    SELECT
        *,
        lap_number = 1 AND session_type IN ('R', 'S') AS is_lap_one,
        contains(track_status, '5') AS under_red_flag,
        contains(track_status, '4') AS under_safety_car,
        regexp_matches(track_status, '[67]') AS under_vsc,
        contains(track_status, '2') AS under_yellow,
        compound IN ('INTERMEDIATE', 'WET') AS on_wet_tyre
    FROM teams_filled
),

first_pass AS (
    SELECT
        *,
        -- order matters: a lap gets the FIRST reason that is true
        CASE
            WHEN lap_time_s IS NULL THEN 'no_time'
            WHEN is_generated THEN 'generated'
            WHEN is_in_lap THEN 'in_lap'
            WHEN is_out_lap THEN 'out_lap'
            WHEN is_lap_one THEN 'lap_one'
            WHEN under_red_flag THEN 'red_flag'
            WHEN under_safety_car THEN 'safety_car'
            WHEN under_vsc THEN 'vsc'
            WHEN under_yellow THEN 'yellow'
            WHEN is_deleted THEN 'deleted'
            WHEN NOT is_accurate THEN 'inaccurate'
            WHEN on_wet_tyre THEN 'wet_tyre'
            ELSE 'clean'
        END AS reason_before_slow
    FROM flagged
),

with_median AS (
    SELECT
        *,
        median(lap_time_s) FILTER (WHERE reason_before_slow = 'clean')
            OVER (PARTITION BY session_key) AS session_clean_median_s
    FROM first_pass
)

SELECT
    * EXCLUDE (reason_before_slow),
    CASE
        WHEN reason_before_slow <> 'clean' THEN reason_before_slow
        WHEN lap_time_s > session_clean_median_s * {{ slow_lap_pct }} / 100 THEN 'slow'
        ELSE 'clean'
    END AS lap_reason,
    lap_reason = 'clean' AS is_clean
FROM with_median
ORDER BY session_key, driver_code, lap_number;
