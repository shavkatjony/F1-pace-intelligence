-- dim_teams: one row per team name FastF1 uses. The team ID map.
-- lineage links the names of one team over the years (AlphaTauri -> RB -> Racing Bulls).
-- The names, ids and lineages come from seeds/teams.csv, which you write by hand.
CREATE OR REPLACE TABLE dim_teams AS
WITH seen AS (
    SELECT team, season FROM core_laps
    UNION ALL
    SELECT team, season FROM core_results
)

SELECT
    s.team AS team_name,
    t.team_id,   -- NULL = this name is missing from seeds/teams.csv (a check catches it)
    t.lineage,
    min(s.season) AS first_season,
    max(s.season) AS last_season
FROM seen AS s
LEFT JOIN read_csv('{{ seeds }}/teams.csv') AS t
    ON t.team_name = s.team
GROUP BY ALL
ORDER BY t.lineage, first_season;

