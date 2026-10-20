-- Every saved table has rows, except the gaps written down in seeds/known_gaps.csv.
SELECT f.session_key, f.table_name
FROM core_files AS f
LEFT JOIN read_csv('{{ seeds }}/known_gaps.csv') AS g
    ON g.session_key = f.session_key
    AND g.table_name = f.table_name
WHERE f.is_empty
    AND g.session_key IS NULL
    