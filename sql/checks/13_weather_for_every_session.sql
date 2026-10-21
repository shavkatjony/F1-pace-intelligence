-- Every session has weather (FastF1 saves one sample a minute).
SELECT s.session_key
FROM core_sessions AS s
LEFT JOIN mart_session_weather AS w USING (session_key)
WHERE w.session_key IS NULL OR w.n_samples < 10
