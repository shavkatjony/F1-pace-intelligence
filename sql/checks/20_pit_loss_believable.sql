-- A green-flag pit stop costs roughly 15 to 35 seconds everywhere on the calendar. A value
-- outside that (from 3+ stops) means the in-lap/out-lap pairing broke. Returns those races.
SELECT season, round, circuit, green_stops, pit_loss_s
FROM mart_race_strategy
WHERE green_stops >= 3
    AND NOT is_wet_race
    AND pit_loss_s NOT BETWEEN 15 AND 35
