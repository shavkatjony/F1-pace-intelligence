# 0018 · The public copy: what's online, how it gets there, where it runs

Date: 2026-11-04
Status: accepted
Updated: 2026-11-05 (Render instead of Hugging Face), 2026-11-08 (the friendly public copy)
Builds on: [0002](0002-storage.md) storage, [0015](0015-public-record.md) public record, [0017](0017-race-engineer.md) race engineer

## Decision
- A read-only copy of the pit wall is online: [F1 Pace Intelligence, online demo](https://f1-pace-intelligence.onrender.com).
  It has the forecasts, the public record, the tyre decisions, the weekends, weather and
  standings, the race part of the debrief, and the race engineer's recorded exam answers. Settings: config/public.yaml, the same as
  config/dpec.yaml except `mode: public` (a test fails if they drift apart).
- Local only: the telemetry traces and the lap split (they read 4 GB of raw files; the API
  answers 404 with the reason), and live questions to the race engineer (each costs money;
  the API answers 403). Online, those windows explain this in one sentence and show a
  picture or the recorded answers instead.
- The data: `dpec snapshot` packs the warehouse, the saved forecasts, the ledger and the
  2026 dry runs (12.5 MB for v1.2) with a SHA-256 per file and a manifest, and the file is
  attached to a GitHub Release. Data never goes into git.
- The image: on each published release, a GitHub workflow builds a Docker image from the
  tagged code, stops if a checksum doesn't match, starts it, checks it's the public copy
  (public mode, the snapshot's date, the page, the weekends, the recorded answers, chat
  refused), then pushes it to ghcr.io as
  :<tag> and :latest. The image runs as a normal user, not root.
- The host: a free Render web service that runs the :latest image (a Hugging Face Space
  until 5 November: see the update). New data = a new release, then Manual Deploy on Render.

## Why
- Hugging Face Spaces: free without a card, runs any Docker image, enough memory for
  DuckDB and pandas, a public link, and data science people know it. It sleeps after
  48 hours without visitors and wakes on the next visit in about a minute.
- Render (free web service): also runs Docker, but sleeps after 15 minutes without
  visitors and has a small memory limit for the free tier.
- Fly.io: needs a credit card; no free tier for new accounts.
- A static site on GitHub Pages: free and never sleeps, but static: every view would have
  to be exported as files, or the queries rewritten to run in the browser. A rewrite.
- Building the image on GitHub, not on my Mac: the online copy is provably the tagged
  code, built on a clean machine and tested before it's published, with a public log.

## Evidence
- Tests, including: the public settings differ from the local ones only in `mode`; the
  snapshot holds exactly the warehouse, the forecasts, the ledger and the dry runs, and its
  checksums catch a one-character change; the public API refuses telemetry (404) and chat
  (403) and keeps the rest; the recorded answers join the newest exam run with its questions.
- Release v1.2 (5 November): the release run built the image from the tagged code, checked
  every file of the 12.5 MB data snapshot, started it, passed the smoke test and pushed it
  to ghcr.io as :v1.2 and :latest. Render runs it.
- The workflow stopped the two releases before it: v1.0 had no data file attached, and
  v1.1's file was damaged (it had been opened and saved as text, so it no longer started
  with the gzip bytes 1f 8b). Releases can't be changed once published, so each fix was a
  new release.

## Known limits
- The online copy is a fixed snapshot, not a live feed: it is as fresh as the last release.
  Its footer shows the date the snapshot was packed and the last race in it.
- A visitor after 15 quiet minutes waits about a minute.
- No telemetry traces online: their windows show a picture made from the same data.
- If Render changes its free tier, the same image runs on any Docker host.

## Update (5 November 2026): Render instead of Hugging Face
- What changed: Hugging Face now needs a PRO plan (US$9 a month) to create a Docker Space,
  even on its free hardware.
- Where it runs instead: a free Render web service that pulls the same :latest image from
  ghcr.io (Singapore region, port 7860, health check /api/health):
  https://f1-pace-intelligence.onrender.com
- The trade-off: the free service has 0.1 CPU and 512 MB of memory, sleeps after 15 minutes
  without visitors, and the next visit waits about a minute. Render doesn't redeploy when
  :latest changes, so after each release: Manual Deploy > Deploy latest reference.
- Next: a static copy on GitHub Pages (every answer saved as a file), which never sleeps.
- deploy/huggingface/ stays: it still works for anyone with PRO.

## Update (8 November 2026): a copy for visitors, not developers
- Messages: an empty or local-only window says in one plain sentence why, and what to look
  at instead. The status code and address stay under "Details".
- The race engineer's window shows the questions and answers of its newest exam run, with
  pass or fail, the tools it used, the time and the tokens.
- The public record says there are 0 live weekends and why, and shows the 2026 dry runs
  labelled "replayed afterwards".
- The footer shows the snapshot's date and the last race in it, never "live" or "real-time".
- Online, table names on window titles are hidden by default (Settings > Data sources shows
  them); the local app shows them.
