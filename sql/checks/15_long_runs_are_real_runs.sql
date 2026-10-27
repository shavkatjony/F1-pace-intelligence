-- mart_long_runs: practice only, enough laps, and a believable pace (within 10% of the best).
SELECT session_key, driver_code, stint, session_type, run_laps, gap_to_best_same_tyre_pct
FROM mart_long_runs
WHERE session_type NOT IN ('FP1', 'FP2', 'FP3')
    OR run_laps < {{ long_run_min_laps }}
    OR gap_to_best_same_tyre_pct > 10
