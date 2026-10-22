-- mart_track_evolution: one row per session, and on a dry track with enough drivers
-- no session changes by more than 1 s in 10 minutes.
SELECT session_key, count(*) AS n, max(abs(evo_s_per_10min)) FILTER (WHERE is_reliable) AS biggest
FROM mart_track_evolution
GROUP BY session_key
HAVING n <> 1 OR biggest > 1