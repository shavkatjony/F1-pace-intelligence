-- Every driver in a results table has a driver_id.
SELECT session_key, driver_code
FROM core_results
WHERE driver_id IS NULL
