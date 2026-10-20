-- Every lap has exactly one reason from the list in decision 0003.
SELECT lap_reason, count(*) AS n
FROM core_laps
WHERE lap_reason IS NULL
    OR lap_reason NOT IN (
        'clean', 'no_time', 'generated', 'in_lap', 'out_lap', 'lap_one', 'red_flag',
        'safety_car', 'vsc', 'yellow', 'deleted', 'inaccurate', 'wet_tyre', 'slow'
    )
GROUP BY lap_reason
