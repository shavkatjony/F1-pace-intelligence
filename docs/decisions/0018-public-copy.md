# 0018 · The public copy: what's online, how it gets there, where it runs

Date: 2026-11-20
Status: accepted

## Decision
- A read-only copy of the pit wall is online: https://<your-hf-name>-dpec-pit-wall.hf.space
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
- The host: a free Hugging Face Space (Docker, CPU basic) that runs the :latest image.
  New data = a new release, then "Factory rebuild" on the Space.

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
- Release v1.0: the release run built, checked and pushed an image of <image sizes i put there soon
>;
  the Space runs it.

## Known limits
- The online copy is as fresh as the last release, not live: the ledger on GitHub is
  always the up-to-date record.
- A visitor after 48 quiet hours waits about a minute.
- No telemetry traces online: the README pictures and the video show them.
- If Hugging Face changes its free tier, the same image runs on any Docker host.
