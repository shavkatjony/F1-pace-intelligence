-- Every race, sprint and qualifying session has an official result.
SELECT s.session_key
FROM core_sessions AS s
LEFT JOIN core_results AS r
    ON r.session_key = s.session_key
WHERE s.session_type IN ('R', 'S', 'Q', 'SQ')
GROUP BY s.session_key
HAVING count(r.driver_code) = 0
