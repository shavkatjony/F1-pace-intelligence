-- Weather summaries must look like weather: no 0 °C track next to 30 °C air (a sensor dropout
-- that once made it into the minimum). Returns the sessions that break the rule.
SELECT session_key, air_temp_c, track_temp_min_c, track_temp_c, track_temp_max_c
FROM mart_session_weather
WHERE track_temp_min_c NOT BETWEEN 5 AND 70
    OR track_temp_max_c NOT BETWEEN 5 AND 70
    OR air_temp_c NOT BETWEEN 0 AND 50
    