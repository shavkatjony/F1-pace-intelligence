# 0018 · The public copy: what's online, how it gets there, where it runs

Date: 2026-11-04
Status: accepted

## Decision
- A read-only copy of the pit wall is online: [F1 Pace Intelligence — Live Demo](https://f1-pace-intelligence.onrender.com).
  It has the forecasts, the public record, the tyre decisions, the weekends, weather and
  standings, and the race part of the debrief. Settings: config/public.yaml, the same as
  config/dpec.yaml except `mode: public` (a test fails if they drift apart).
- Local only: the telemetry traces and the lap split (they read 4 GB of raw files; the API
  answers 404 with the reason), and the race engineer (it costs money per question; 403).
- The data: `dpec snapshot` packs the warehouse, the saved forecasts and the ledger
  (about 11 MB) with a SHA-256 per file and a manifest, and the file is attached to a
  GitHub Release. Data never goes into git.
- The image: on each published release, a GitHub workflow builds a Docker image from the
  tagged code, stops if a checksum doesn't match, starts it, checks it's the public copy
  (public mode, the page, the weekends, chat refused), then pushes it to ghcr.io as
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
- 127 tests, including: the public settings differ from the local ones only in `mode`;
  the snapshot holds exactly the warehouse, the forecasts and the ledger, and its
  checksums catch a one-character change; the public API refuses telemetry (404) and chat
  (403) and keeps the rest.
- Release v1.2 (5 November): the release run built the image from the tagged code, checked
  every file of the 12.5 MB data snapshot, started it, passed the smoke test and pushed it
  to ghcr.io as :v1.2 and :latest. Render runs it.
- The workflow stopped the two releases before it: v1.0 had no data file attached, and
  v1.1's file was damaged (it had been opened and saved as text, so it no longer started
  with the gzip bytes 1f 8b). Releases can't be changed once published, so each fix was a
  new release.

## Known limits
- The online copy is as fresh as the last release, not live: the ledger on GitHub is
  always the up-to-date record.
- A visitor after 15 quiet minutes waits about a minute.
- No telemetry traces online: the README pictures and the video show them.
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