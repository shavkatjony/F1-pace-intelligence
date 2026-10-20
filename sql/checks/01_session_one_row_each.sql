-- core_sessions: one row per session_key. Returns the keys that appear twice.
SELECT session_key, count(*) AS n
FROM core_sessions
GROUP BY session_key
HAVING n > 1
