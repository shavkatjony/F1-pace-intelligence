-- mart_weekends: one row per season + round, and one per race in core_sessions.
SELECT s.session_key, count(w.round) AS n
FROM core_sessions AS s
LEFT JOIN mart_weekends AS w
    ON w.season = s.season
    AND w.round = s.round
WHERE s.session_type = 'R'
GROUP BY s.session_key
HAVING n <> 1