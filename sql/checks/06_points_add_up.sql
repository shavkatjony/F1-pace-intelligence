-- Points per race: 25+18+15+12+10+8+6+4+2+1 = 101, plus 1 for the fastest lap until 2024.
-- Points per sprint: 8+7+6+5+4+3+2+1 = 36.
SELECT session_key, session_type, sum(points) AS total
FROM core_results
WHERE session_type IN ('R', 'S')
GROUP BY ALL
HAVING NOT (
    (session_type = 'R' AND total IN (101, 102))
    OR (session_type = 'S' AND total = 36)
)
