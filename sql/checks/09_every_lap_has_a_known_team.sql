-- Every lap belongs to a team that is in seeds/teams.csv.
SELECT l.session_key, l.driver_code, l.team, count(*) AS laps
FROM core_laps AS l
LEFT JOIN dim_teams AS t
    ON t.team_name = l.team
WHERE t.team_id IS NULL
GROUP BY ALL
