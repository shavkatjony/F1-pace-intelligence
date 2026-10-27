# Data dictionary

Every table in `data/warehouse.duckdb`, one row per column. Built by `dpec build`.
`dpec check` fails if a column in the warehouse is missing here, so this page can't go out of date.

Times are in seconds (`_s`), speeds in km/h (`_kph`). A **key** is the set of columns that is unique per row.

## core_sessions

One row per session (FP1, FP2, FP3, SQ, S, Q, R) of every saved weekend. **Key:** `session_key`.

| column | type | meaning |
|---|---|---|
| `session_key` | text | season, round and session type, e.g. `2024_01_R`. The id used everywhere |
| `season` | int | year |
| `round` | int | round number within the season |
| `event_name` | text | e.g. Bahrain Grand Prix |
| `circuit` | text | short circuit name, e.g. Sakhir |
| `session_name` | text | FastF1's name, e.g. Practice 1, Sprint Shootout |
| `session_type` | text | FP1, FP2, FP3, SQ (sprint qualifying), S (sprint), Q, R |
| `session_date_utc` | timestamp | session start time in UTC |
| `is_sprint_weekend` | bool | the weekend has a sprint |
| `event_folder` | text | folder name in data/raw, used to join raw files |
| `session_folder` | text | folder name in data/raw, used to join raw files |

## core_laps

One row per driver per lap per session. **Key:** `session_key` + `driver_code` + `lap_number`.
Rules for `lap_reason`: decision 0003.

| column | type | meaning |
|---|---|---|
| `session_key` | text | see core_sessions |
| `season` | int | year |
| `round` | int | round number |
| `session_type` | text | FP1 … R |
| `driver_code` | text | three letters, e.g. VER. One driver within a season |
| `car_number` | text | race number on the car that day |
| `team` | text | team name as FastF1 writes it; empty names filled from the same weekend or the same car number |
| `lap_number` | int | 1 = first lap of the session for this driver |
| `stint` | int | 1 = first set of tyres; goes up after each pit stop |
| `compound` | text | SOFT, MEDIUM, HARD, INTERMEDIATE, WET (or UNKNOWN) |
| `tyre_age_laps` | int | laps on this set of tyres, including laps from earlier sessions |
| `fresh_tyre` | bool | the set was new when fitted |
| `lap_time_s` | float | lap time; NULL when not timed |
| `sector1_s` | float | sector 1 time |
| `sector2_s` | float | sector 2 time |
| `sector3_s` | float | sector 3 time |
| `speed_trap_kph` | float | speed at the speed trap |
| `position` | int | running position at the end of the lap (races only) |
| `lap_start_session_s` | float | seconds from session start when the lap began |
| `lap_end_session_s` | float | seconds from session start when the lap ended |
| `lap_start_utc` | timestamp | clock time the lap began |
| `track_status` | text | every track status code seen during the lap, e.g. `14` |
| `deleted_reason` | text | why race control deleted the lap (track limits …) |
| `is_in_lap` | bool | the car entered the pit lane on this lap |
| `is_out_lap` | bool | the car left the pit lane on this lap |
| `is_deleted` | bool | lap time deleted by race control |
| `is_generated` | bool | row made up by FastF1 to fill a gap |
| `is_accurate` | bool | FastF1 trusts the lap time |
| `is_lap_one` | bool | first lap of a race or sprint |
| `under_red_flag` | bool | status code 5 during the lap |
| `under_safety_car` | bool | status code 4 during the lap |
| `under_vsc` | bool | status code 6 or 7 during the lap |
| `under_yellow` | bool | status code 2 during the lap |
| `on_wet_tyre` | bool | intermediate or wet tyre |
| `session_clean_median_s` | float | median clean lap of the session, used by the `slow` rule |
| `lap_reason` | text | `clean` or the first rule the lap breaks |
| `is_clean` | bool | lap_reason = 'clean'. Only clean laps count as pace |

## core_results

One row per driver per race, sprint, qualifying and sprint qualifying. **Key:** `session_key` + `driver_code`.
The official classification (Jolpica, via FastF1): penalties decided after the flag are in.

| column | type | meaning |
|---|---|---|
| `session_key` | text | see core_sessions |
| `season` | int | year |
| `round` | int | round number |
| `session_type` | text | R, S, Q or SQ |
| `driver_code` | text | three letters |
| `driver_id` | text | Jolpica's id, e.g. `max_verstappen`; filled from the same season when the source has none |
| `car_number` | text | race number |
| `driver_name` | text | full name |
| `team` | text | team name |
| `team_id` | text | from seeds/teams.csv |
| `grid_position` | int | starting position; 0 = pit lane |
| `finish_position` | int | official finishing order, after penalties |
| `classified` | text | a number, or R retired, D disqualified, W withdrew |
| `status` | text | Finished, +1 Lap, Disqualified, Retired … |
| `points` | float | points scored (races and sprints) |
| `laps_completed` | int | laps completed |
| `q1_s` | float | best Q1 time (qualifying) |
| `q2_s` | float | best Q2 time |
| `q3_s` | float | best Q3 time |

## core_files

One row per saved table per session, from the manifests. **Key:** `session_key` + `table_name`.

| column | type | meaning |
|---|---|---|
| `session_key` | text | see core_sessions |
| `table_name` | text | laps, car_data, pos_data, weather, results, race_control, track_status |
| `n_rows` | int | rows in the file |
| `is_empty` | bool | n_rows = 0. Allowed only if listed in seeds/known_gaps.csv |
| `sha256` | text | fingerprint of the file; changes if the data changes |
| `saved_at_utc` | timestamp | when `dpec ingest` saved it |

## dim_drivers

The driver ID map. One row per driver per season. **Key:** `season` + `driver_code`.

| column | type | meaning |
|---|---|---|
| `season` | int | year |
| `driver_code` | text | three letters |
| `driver_id` | text | Jolpica's id; NULL for FP1 stand-ins who never raced or qualified |
| `driver_name` | text | full name (NULL for FP1 stand-ins) |
| `car_numbers` | list | numbers used this season (a stand-in can use two) |
| `teams` | list | teams this season; two = changed team mid-season |
| `started_a_race` | bool | has a race result this season |

## dim_teams

The team ID map. One row per team name FastF1 uses. **Key:** `team_name`.

| column | type | meaning |
|---|---|---|
| `team_name` | text | as FastF1 writes it, e.g. Racing Bulls |
| `team_id` | text | short id from seeds/teams.csv |
| `lineage` | text | one id for a team across name changes (AlphaTauri → RB → Racing Bulls) |
| `first_season` | int | first season with this name |
| `last_season` | int | last season with this name |

## mart_weekends

The overview: one row per race weekend. **Key:** `season` + `round`.

| column | type | meaning |
|---|---|---|
| `season` | int | year |
| `round` | int | round number |
| `event_name` | text | e.g. Bahrain Grand Prix |
| `circuit` | text | short circuit name |
| `race_date` | date | race day (UTC) |
| `is_sprint_weekend` | bool | the weekend has a sprint |
| `pole` | text | driver code of P1 in qualifying (before grid penalties) |
| `winner` | text | driver code of the official race winner |
| `winner_team` | text | the winner's team |
| `race_laps` | int | laps the leader completed |
| `not_classified` | int | drivers retired, disqualified or withdrawn |
| `safety_car_laps` | int | laps with the safety car out at any point |
| `vsc_laps` | int | laps with a virtual safety car at any point |
| `had_red_flag` | bool | the race was stopped at least once |
| `wet_tyre_share` | float | share of laps on intermediates or wets |
| `is_wet_race` | bool | wet_tyre_share above 0.1 |
| `clean_share` | float | share of laps that are clean |

## mart_session_weather

Weather of each session, from one sample a minute. **Key:** `session_key`.

| column | type | meaning |
|---|---|---|
| `session_key` | text | see core_sessions |
| `season` | int | year |
| `round` | int | round number |
| `session_type` | text | FP1 … R |
| `n_samples` | int | weather samples (about one a minute) |
| `air_temp_c` | float | median air temperature |
| `track_temp_min_c` | float | lowest track temperature |
| `track_temp_c` | float | median track temperature |
| `track_temp_max_c` | float | highest track temperature |
| `humidity_pct` | float | median humidity |
| `wind_speed_ms` | float | median wind speed, metres per second |
| `rain_share` | float | share of minutes with rain |
| `had_rain` | bool | rain at any point |

## mart_standings

The drivers' championship after every round. **Key:** `season` + `round` + `driver_code`.

| column | type | meaning |
|---|---|---|
| `season` | int | year |
| `round` | int | round number |
| `driver_code` | text | three letters |
| `team` | text | team in that round's race |
| `round_points` | float | race + sprint points this weekend |
| `round_wins` | int | 1 if he won the race this weekend |
| `total_points` | float | points so far this season |
| `total_wins` | int | race wins so far this season |
| `championship_position` | int | place after this round: points, then wins |

## mart_driver_session_pace

How fast each driver was in each session, on clean laps only. **Key:** `session_key` + `driver_code`.

| column | type | meaning |
|---|---|---|
| `session_key` | text | see core_sessions |
| `season` | int | year |
| `round` | int | round number |
| `session_type` | text | FP1 … R |
| `driver_code` | text | three letters |
| `team` | text | team name |
| `clean_laps` | int | number of clean laps |
| `best_lap_s` | float | fastest clean lap |
| `median_lap_s` | float | median clean lap |
| `gap_to_best_pct` | float | best lap vs the session's fastest, in percent (0 = fastest) |
| `pace_rank` | int | 1 = fastest best lap in the session |

## mart_stints

One row per set of tyres a driver used in a session. **Key:** `session_key` + `driver_code` + `stint`.

| column | type | meaning |
|---|---|---|
| `session_key` | text | see core_sessions |
| `season` | int | year |
| `round` | int | round number |
| `session_type` | text | FP1 … R |
| `driver_code` | text | three letters |
| `stint` | int | 1 = first set of tyres in the session |
| `team` | text | team name |
| `compound` | text | SOFT, MEDIUM, HARD, INTERMEDIATE, WET or UNKNOWN (test tyres, missing names) |
| `first_lap` | int | first lap number of the stint |
| `last_lap` | int | last lap number of the stint |
| `n_laps` | int | laps in the stint, clean or not |
| `tyre_age_start` | int | tyre age on the first lap; above 1 = a used set |
| `fresh_at_start` | bool | the set was new when fitted |
| `n_clean` | int | clean laps in the stint |
| `median_clean_s` | float | median clean lap |
| `deg_raw_s_per_lap` | float | slope of clean lap time vs tyre age; NULL with fewer than 4 clean laps |
| `deg_s_per_lap` | float | deg_raw plus the fuel effect from the config: the tyre's real wear per lap |

## mart_long_runs

Practice stints that look like race running. **Key:** `session_key` + `driver_code` + `stint`.
Rule: at least `long_run_min_laps` clean laps within `long_run_band_pct` % of the stint's median (config).

| column | type | meaning |
|---|---|---|
| `session_key` | text | see core_sessions |
| `season` | int | year |
| `round` | int | round number |
| `session_type` | text | FP1, FP2 or FP3 |
| `driver_code` | text | three letters |
| `stint` | int | stint number in the session |
| `team` | text | team name |
| `compound` | text | SOFT, MEDIUM or HARD |
| `tyre_age_start` | int | tyre age at the start of the stint |
| `run_laps` | int | laps in the run (inside the band) |
| `run_median_s` | float | median lap of the run |
| `run_median_fuel_adj_s` | float | the same with the fuel burnt during the run added back |
| `deg_s_per_lap` | float | tyre wear per lap during the run, fuel effect included |
| `gap_to_best_same_tyre_pct` | float | gap to the quickest long run of the session on the same compound |

## mart_track_evolution

How much faster the track gets during a session. One row per practice and qualifying session. **Key:** `session_key`.
Method: decision 0009.

| column | type | meaning |
|---|---|---|
| `session_key` | text | see core_sessions |
| `season` | int | year |
| `round` | int | round number |
| `session_type` | text | FP1, FP2, FP3, Q or SQ |
| `n_drivers` | int | drivers with at least two push laps on one compound |
| `n_laps` | int | push laps used |
| `evo_s_per_10min` | float | change in lap time every 10 minutes, same driver and tyre; negative = track getting faster |
| `q1_to_q2_s` | float | median change of the same drivers' best time from Q1 to Q2 (qualifying only) |
| `q2_to_q3_s` | float | the same from Q2 to Q3 |
| `track_temp_min_c` | float | lowest track temperature in the session |
| `track_temp_max_c` | float | highest track temperature in the session |
| `had_rain` | bool | rain at any point in the session |
| `wet_lap_share` | float | share of laps on intermediates or wets |
| `is_reliable` | bool | dry, no rain, at least 10 drivers: use the number. Otherwise a drying track or noise |

## mart_weekend_signals

What practice and qualifying said, next to what happened on Sunday. One row per driver per race weekend
with at least 10 clean race laps. **Key:** `season` + `round` + `driver_code`.
Pace numbers are % behind the best of that session (0 = best).

| column | type | meaning |
|---|---|---|
| `season` | int | year |
| `round` | int | round number |
| `driver_code` | text | three letters |
| `team` | text | team in the race |
| `is_sprint_weekend` | bool | the weekend has a sprint (only one practice) |
| `is_wet_race` | bool | from mart_weekends |
| `n_long_runs` | int | long runs in practice this weekend |
| `long_run_gap_pct` | float | median of his long runs' gaps to the best run on the same tyre |
| `long_run_deg_s_per_lap` | float | median tyre wear in his long runs |
| `quali_gap_pct` | float | best clean qualifying lap vs the fastest |
| `race_clean_laps` | int | clean laps in the race |
| `race_pace_gap_pct` | float | median clean race lap vs the driver with the best median |
| `grid_position` | int | official starting position |
| `finish_position` | int | official finishing position |
| `points` | float | race points |
