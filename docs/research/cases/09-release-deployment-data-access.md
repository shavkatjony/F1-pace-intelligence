# Case 09 · Release, deployment and losing data access

Decisions: [0015 · Public record](../../decisions/0015-public-record.md) (updated 2026-11-05), [0018 · Public copy](../../decisions/0018-public-copy.md) (2026-11-04, updated 2026-11-05 and 2026-11-08) · Register: E30–E32

## 1. Research question
How can a data product built on a laptop be published so that the online version provably matches tagged code and checked data, at no cost, and what happens to the project when its data source changes its terms?

## 2. Initial hypothesis
A Docker image on a free Hugging Face Space, refreshed from a data snapshot, would be enough. Live weekends would continue for the rest of the 2026 season through FastF1.

## 3. Dataset and scope
Releases v1.0 to v1.2 of the public copy (November 2026); the `release.yml` workflow; the FastF1 data path for 2026 rounds after Singapore.

## 4. Method
- **Release design:** `dpec snapshot` packs the warehouse, saved forecasts, ledger and dry runs with a SHA-256 per file and a manifest. The file is attached to a GitHub Release. The workflow builds the image from the tagged code, verifies every checksum during the build, starts the container and runs a smoke test that it is the public copy, then pushes to GHCR. Data never enters git.
- **Hosting comparison:** Hugging Face Spaces, Render, Fly.io, and a static GitHub Pages site, on cost, memory, sleep behaviour and effort.
- **Data access:** tested a new-round ingest after the October 2026 change.

## 5. Results
- **v1.0 failed:** the workflow stopped with no data file to download, because the snapshot was not attached.
- **v1.1 failed:** the attached file had been opened and re-saved as text, so it no longer began with the gzip bytes `1f 8b`.
- **v1.2 passed:** built from the tag, every file of the 12.5 MB snapshot verified, smoke test passed, pushed as `:v1.2` and `:latest`.
- Published releases cannot be edited, so each fix had to be a new release.
- **Hosting:** Hugging Face began requiring a paid plan (US$9/month) for Docker Spaces. A free Render web service runs the same image instead (0.1 CPU, 512 MB, sleeps after 15 minutes idle, about a minute to wake, no automatic redeploy on a new `:latest`). Fly.io needed a card; GitHub Pages would require exporting every view or rewriting queries to run in the browser.
- **Data access:** since October 2026, F1's timing service requires a login. FastF1 3.9+ needs a paid F1TV Access subscription and 3.8 receives no data. No session after the 2026 Singapore Grand Prix (11 October) could be downloaded.

## 6. Interpretation
The workflow did its job: two bad releases were stopped before anything reached users, and the version that went live is traceable to a tag and a checksum list. Choosing a portable Docker image rather than a host-specific format meant the hosting change cost a configuration change, not a rewrite. For the forecasting record, the honest response to losing data access was to stop at the saved races rather than present after-the-fact dry runs as live forecasts.

## 7. Decision influenced
- The online copy is a versioned snapshot; its footer shows the snapshot date and last race, never "live" ([decision 0018](../../decisions/0018-public-copy.md)).
- Render replaced Hugging Face; [`deploy/huggingface/`](../../../deploy/huggingface/) is kept for anyone with a paid plan.
- The public record is paused with **0 live weekends**; `freeze`, `score` and the CI ledger checks remain ready for a new source (OpenF1) or an F1TV subscription ([decision 0015, update](../../decisions/0015-public-record.md#update-5-november-2026-no-live-weekends), [live-weekends.md](../../live-weekends.md)).
- Operations documents the release steps and these failure modes ([operations.md § 9 and § 11](../../engineering/operations.md#9-release-and-deployment)).

## 8. Known limitations
- The online copy is only as fresh as the last release, and sleeps when idle.
- A static GitHub Pages copy, which never sleeps, is planned but not built (Future).
- Restarting live forecasts depends on a paid subscription or a new adapter.

## 9. Evidence and implementation
- Workflow: [`.github/workflows/release.yml`](../../../.github/workflows/release.yml) · Image: [`Dockerfile`](../../../Dockerfile), [`.dockerignore`](../../../.dockerignore)
- Snapshot: [`src/dpec/publish/snapshot.py`](../../../src/dpec/publish/snapshot.py) · Tests: [`tests/dpec/test_publish.py`](../../../tests/dpec/test_publish.py), [`test_api.py`](../../../tests/dpec/test_api.py)
- Public settings: [`config/public.yaml`](../../../config/public.yaml)
- Live status: [live-weekends.md](../../live-weekends.md) · Narrative: [methods.md § 12](../../methods.md#12-the-public-copy)
- How it works now: [workstream 05 · Backend engineering](../../workstreams/05-backend-engineering.md) · [workstream 04 · ML engineering](../../workstreams/04-ml-engineering.md)

Previous: [Case 08](08-strategy-modelling.md) · Back to the [research archive](../README.md)
