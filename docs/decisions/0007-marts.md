# 0007 · Marts: answer tables, and no dbt (yet)

Date: 2026-10-17
Status: accepted

## Decision
- sql/marts holds answer tables, built after sql/core. Names start with mart_.
- Every mart states its grain and key at the top of its file and in the dictionary.
- Pace is compared in percent of the session's best, not seconds, so tracks are comparable.
- 2026-10-__: a track temperature of exactly 0.0 °C is a sensor dropout (47 of 54,295 samples): read as missing. Check 18 guards it.

## dbt: not yet
- My own runner already does what I would use dbt for: placeholders, files in order,
  one table per file, data checks (`dpec check`) and a dictionary check. dbt would add
  a new tool and config files without giving me a new result.
- With only 12 tables, ordering by file number is still easy to read. dbt's automatic
  ordering from ref() only pays off when the number of tables and links between them grows.

## When to revisit
When there are more than ~25 tables, or file-number ordering starts causing build mistakes.
