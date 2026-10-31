"""The `dpec` commands."""

# dear viewer , please ,before change anything ,
# spend a lots of time as much as possible about f1 rules and regulations and also
# how the engineers work in the backend ,
# because if you f**k up , this possible  a lots of days to fix
import time
from pathlib import Path

import typer

# we import here the created warehouse that runs the sql and sql (assume that there are temporary files)
from telemetry_core import warehouse
from telemetry_core.alignment import distance_grid
from telemetry_core.alignment.lap_telemetry import load_lap
from telemetry_core.config import load_settings
from telemetry_core.ingestion import fastf1_source
from telemetry_core.ingestion.log import log_attempt
from telemetry_core.ingestion.writer import is_saved, write_session
from telemetry_core.paths import session_folder

app = typer.Typer(help="Team DPEC weekend forecaster.", no_args_is_help=True)
LAYERS = ["core", "marts"]  # folders in sql/, built in this order,|||||.   Marts are built after core, so they can read every core table. dpec build names each table after its file, like before.

def sql_params(s) -> dict:
    """Values for the {{ }} placeholders in the SQL files."""
    return {
        "raw": s.paths.raw.as_posix(),
        "seeds": s.paths.seeds.as_posix(),
        "slow_lap_pct": s.slow_lap_pct,
        "fuel_effect_s_per_lap": s.fuel_effect_s_per_lap,
        "long_run_min_laps": s.long_run_min_laps,
        "long_run_band_pct": s.long_run_band_pct,
        "push_lap_band_pct": s.push_lap_band_pct,
    }


@app.command()
def info(config: str = "config/dpec.yaml") -> None:
    """Show the current settings."""
    s = load_settings(config)
    typer.echo(f"Team:     {s.team_name} (our cars: {s.adopted_team})")
    typer.echo(f"Seasons:  {s.seasons[0]}-{s.seasons[-1]}")
    typer.echo(f"Mode:     {s.mode}")
    typer.echo(f"Raw data: {s.paths.raw}")


@app.command()
def ingest(
    season: int | None = typer.Option(None, help="One season. Default: every season in config"),
    round_no: int | None = typer.Option(None, "--round", help="One round. Default: all rounds"),
    session: str | None = typer.Option(None, help="One session, e.g. 'Race'. Default: all"),
    force: bool = typer.Option(False, help="Download again even if already saved"),
    config: str = "config/dpec.yaml",
) -> None:
    """Save F1 sessions from FastF1 to data/raw as Parquet. Already saved sessions are skipped."""
    s = load_settings(config)
    fastf1_source.enable_cache(s.paths.cache)
    seasons = [season] if season else s.seasons
    counts = {"saved": 0, "skipped": 0}
    failed = []

    for year in seasons:
        rounds = [round_no] if round_no else fastf1_source.season_rounds(year)
        for rnd in rounds:
            event_name, names = fastf1_source.session_names(year, rnd)
            if session:
                names = [n for n in names if n.lower() == session.lower()]
            typer.echo(f"{year} round {rnd}: {event_name}")
            for name in names:
                folder = session_folder(s.paths.raw, "fastf1", year, rnd, event_name, name)
                if is_saved(folder) and not force:
                    counts["skipped"] += 1
                    typer.echo(f"  {name:<20} skipped (already saved)")
                    continue
                where = {"source": "fastf1", "season": year, "round": rnd, "session": name}
                started = time.perf_counter()
                try:
                    tables, meta = fastf1_source.fetch_session(year, rnd, name)
                except fastf1_source.RateLimitError:
                    log_attempt(s.paths.log, **where, status="rate_limited")
                    typer.echo("FastF1 rate limit reached. Run the same command again later;")
                    typer.echo("everything saved so far is kept and will be skipped.")
                    raise typer.Exit(code=1) from None
                except Exception as error:  # noqa: BLE001 - one bad session must not stop the rest
                    log_attempt(s.paths.log, **where, status="failed", error=str(error))
                    failed.append(f"{year} round {rnd} {name}: {error}")
                    typer.echo(f"  {name:<20} FAILED: {error}")
                    continue
                manifest = write_session(tables, meta, folder)
                total_rows = sum(v["rows"] for v in manifest["files"].values())
                seconds = round(time.perf_counter() - started, 1)
                log_attempt(s.paths.log, **where, status="ok", rows=total_rows, seconds=seconds)
                counts["saved"] += 1
                rows = ", ".join(f"{k} {v['rows']}" for k, v in manifest["files"].items())
                typer.echo(f"  {name:<20} saved: {rows}")

    typer.echo(
        f"\nDone: {counts['saved']} saved, {counts['skipped']} skipped, {len(failed)} failed"
    )
    for line in failed:
        typer.echo(f"  failed: {line}")
    if failed:
        raise typer.Exit(code=1)


@app.command()
def build(config: str = "config/dpec.yaml") -> None:
    """Build the clean tables in data/warehouse.duckdb from data/raw."""
    s = load_settings(config)
    for layer in LAYERS:
        counts = warehouse.build(s.paths.sql / layer, s.paths.warehouse, sql_params(s))
        for table, rows in counts.items():
            typer.echo(f"{table:<24} {rows:>10,} rows")
    typer.echo(f"Saved to {s.paths.warehouse}")

@app.command()
def check(config: str = "config/dpec.yaml") -> None:
    """Run the data checks in sql/checks and the data dictionary check. Fails if any fails."""
    s = load_settings(config)
    results = warehouse.run_checks(s.paths.sql / "checks", s.paths.warehouse, sql_params(s))
    missing = warehouse.undocumented_columns(s.paths.warehouse, s.paths.dictionary)
    results.append(
        {
            "name": "data_dictionary_covers_every_column",
            "n_bad": len(missing),
            "sample": "\n".join(missing[:5]),
        }
    )
    for r in results:
        mark = "PASS" if r["n_bad"] == 0 else f"FAIL ({r['n_bad']} rows)"
        typer.echo(f"{mark:<16} {r['name']}")
        if r["n_bad"]:
            typer.echo(f"{r['sample']}\n")
    failed = sum(r["n_bad"] > 0 for r in results)
    typer.echo(f"\n{len(results) - failed} passed, {failed} failed")
    if failed:
        raise typer.Exit(code=1)

@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000, config: str = "config/dpec.yaml") -> None:
    """Open the pit wall app on this computer (read-only). Stop it with Ctrl+C."""
    import uvicorn

    from dpec.api.main import create_app

    typer.echo(f"Pit wall: http://{host}:{port}   API docs: http://{host}:{port}/api/docs")
    uvicorn.run(create_app(config), host=host, port=port, log_level="warning")
    
#import uvicorn sits inside the function on purpose:

@app.command()
def sql(query: str, config: str = "config/dpec.yaml") -> None:
    """Run one SQL query on the warehouse and print the result."""
    s = load_settings(config)
    result = warehouse.query(s.paths.warehouse, query)
    typer.echo(result.to_string(index=False, max_rows=60))


@app.command()
def compare(
    session_key: str,
    driver: str,
    lap: int,
    other_driver: str,
    other_lap: int,
    other_session: str | None = typer.Option(None, help="Default: the same session"),
    config: str = "config/dpec.yaml",
) -> None:
    """Put two laps on the distance grid, check the corners line up, and save a chart."""
    import matplotlib

    matplotlib.use("Agg")  # save to a file, no window
    import matplotlib.pyplot as plt

    s = load_settings(config)
    other_session = other_session or session_key
    try:
        tel_a, info_a = load_lap(s.paths.warehouse, s.paths.raw, session_key, driver, lap)
        tel_b, info_b = load_lap(s.paths.warehouse, s.paths.raw, other_session, other_driver, other_lap)
    except ValueError as error:
        typer.echo(f"Can't compare: {error}")
        raise typer.Exit(code=1) from None

    ref = distance_grid.to_grid(
        tel_a, s.grid_step_m, info_a["lap_start_session_s"], info_a["lap_end_session_s"]
    )
    lap_length = ref["distance_m"].iloc[-1]
    other = distance_grid.to_grid(
        tel_b,
        s.grid_step_m,
        info_b["lap_start_session_s"],
        info_b["lap_end_session_s"],
        lap_length_m=lap_length,
    )
    both = distance_grid.delta(ref, other)

    name_a, name_b = f"{driver.upper()} lap {lap}", f"{other_driver.upper()} lap {other_lap}"
    for name, info, grid in [(name_a, info_a, ref), (name_b, info_b, other)]:
        typer.echo(
            f"{name:<12} official {info['lap_time_s']:.3f} s | on grid {grid['time_s'].iloc[-1]:.3f} s"
            f" | {info['lap_reason']}"
        )
    typer.echo(f"Lap length (reference): {lap_length:.0f} m, {len(both)} grid points")

    corners_a = distance_grid.apexes(ref)
    corners_b = distance_grid.apexes(other)
    typer.echo("\nCorner  apex A (m)  apex B (m)  gap (m)  min speed A  min speed B")
    for i, row in corners_a.iterrows():
        nearest = corners_b.iloc[(corners_b["distance_m"] - row["distance_m"]).abs().argmin()]
        gap = nearest["distance_m"] - row["distance_m"]
        typer.echo(
            f"{i + 1:>6}  {row['distance_m']:>10.0f}  {nearest['distance_m']:>10.0f}  {gap:>7.0f}"
            f"  {row['speed_kph']:>11.0f}  {nearest['speed_kph']:>11.0f}"
        )
    typer.echo(f"\nGap at the line: {both['delta_s'].iloc[-1]:+.3f} s ({name_b} vs {name_a})")

    fig, (top, bottom) = plt.subplots(2, 1, figsize=(12, 6), sharex=True, height_ratios=[2, 1])
    top.plot(both["distance_m"], both["speed_kph_ref"], label=name_a)
    top.plot(both["distance_m"], both["speed_kph_other"], label=name_b)
    for d in corners_a["distance_m"]:
        top.axvline(d, color="grey", lw=0.5, ls=":")
    top.set_ylabel("speed (km/h)")
    top.legend()
    bottom.plot(both["distance_m"], both["delta_s"], color="black")
    bottom.axhline(0, color="grey", lw=0.5)
    bottom.set_ylabel(f"gap (s), + = {other_driver.upper()} behind")
    bottom.set_xlabel("distance from the start line (m)")
    fig.suptitle(f"{session_key} {name_a} vs {other_session} {name_b}")
    out = Path("reports/figures") / f"{session_key}_{driver}{lap}_vs_{other_driver}{other_lap}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=120, bbox_inches="tight")
    typer.echo(f"Chart saved: {out}")

@app.command()
def backtest(
    first_season: int = typer.Option(
        2023, help="First season to forecast; earlier ones only teach"
    ),
    test_from: int = typer.Option(2025, help="Seasons from here on are the test years"),
    config: str = "config/dpec.yaml",
) -> None:
    """Forecast every past dry race with only what was known before it, then score each forecaster.
    Choose settings on the tune years; report the test years. Adds 80% ranges to every guess,
    and the chances of the shared model."""
    import numpy as np
    import pandas as pd

    from dpec.forecasting.backtest import score, walk_forward
    from dpec.forecasting.baselines import BASELINES
    from dpec.forecasting.model import shared_model
    from dpec.forecasting.ranges import add_ranges, coverage_table
    from dpec.forecasting.simulate import walk_forward_chances
    from dpec.forecasting.targets import forecast_table

    s = load_settings(config)
    forecasters = {**BASELINES, "shared_model": shared_model}
    table = forecast_table(s.paths.warehouse)
    predictions = add_ranges(walk_forward(table, forecasters, first_season))
    predictions["years"] = np.where(predictions["season"] < test_from, "tune", "test")
    model = predictions["forecaster"] == "shared_model"
    predictions = predictions.join(walk_forward_chances(predictions[model]))
    scores = pd.concat(
        [
            score(predictions).assign(years="all"),
            score(predictions, by=("years", "checkpoint", "forecaster")),
        ]
    )
    saved = s.paths.data / "forecasts" / "backtest.parquet"  # every guess: rebuildable, not in git
    saved.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_parquet(saved, index=False)
    report = Path("reports/backtest/scores.csv")  # small: kept in git as evidence
    report.parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(report, index=False, float_format="%.3f")
    titles = {
        "all": f"All years, {first_season} on",
        "tune": f"Tune years, {first_season}-{test_from - 1} (choose settings here)",
        "test": f"Test years, {test_from} on (report these)",
    }
    for years, title in titles.items():
        rows = scores[scores["years"] == years].drop(columns="years")
        typer.echo(f"\n{title}\n" + rows.to_string(index=False, float_format="%.3f"))

    cover = coverage_table(predictions[model], by=("years", "checkpoint"))
    cover.to_csv(report.parent / "ranges.csv", index=False, float_format="%.3f")
    typer.echo("\n80% ranges of the shared model: share of real race paces inside (aim: 0.75-0.85)")
    typer.echo(cover.to_string(index=False, float_format="%.3f"))
    typer.echo(f"\nSaved {len(predictions):,} guesses to {saved}")


@app.command()
def replay(
    first_season: int = typer.Option(2023, help="First season to replay; earlier ones only teach"),
    config: str = "config/dpec.yaml",
) -> None:
    """Replay every past dry race: the tyre and stop decision the packet would have made before
    it, next to what happened. Scored on tyre wear, stops and first-stop windows."""
    from dpec.decisions.replay import replay_all, score

    s = load_settings(config)
    replayed, _ = replay_all(s.paths.warehouse, first_season)
    saved = s.paths.data / "forecasts" / "decisions.parquet"  # rebuildable, not in git
    saved.parent.mkdir(parents=True, exist_ok=True)
    replayed.to_parquet(saved, index=False)
    scores = score(replayed)
    report = Path("reports/backtest/decisions.csv")  # small: kept in git as evidence
    report.parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(report, index=False, float_format="%.3f")
    typer.echo(scores.to_string(index=False, float_format="%.3f"))
    typer.echo(f"\nSaved {len(replayed)} replayed races to {saved}")

@app.command()
def packet(
    season: int = typer.Option(..., help="Season of the race"),
    round_no: int = typer.Option(..., "--round", help="Round of the race"),
    checkpoint: str = typer.Option("after_quali", help="after_practice or after_quali"),
    config: str = "config/dpec.yaml",
) -> None:
    """Write one past race's decision packet to reports/packets: race pace, tyres, the stop
    plan, what could make it wrong, and what happened."""
    from dpec.decisions.packet import file_name, make_packet, to_markdown

    s = load_settings(config)
    forecasts = s.paths.data / "forecasts" / "backtest.parquet"
    try:
        p = make_packet(s.paths.warehouse, forecasts, season, round_no, s.adopted_team, checkpoint)
    except ValueError as problem:
        typer.echo(str(problem), err=True)
        raise typer.Exit(1) from None
    page = to_markdown(p)
    out = Path("reports/packets") / file_name(p)  # small: kept in git as evidence
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    typer.echo(page)
    typer.echo(f"Saved: {out}")

@app.command()
def freeze(
    season: int = typer.Option(..., help="Season of the race"),
    round_no: int = typer.Option(..., "--round", help="Round of the race"),
    checkpoint: str = typer.Option(
        "after_quali", help="after_quali (before the race) or after_practice (before quali)"
    ),
    race_laps: int | None = typer.Option(None, help="Race length in laps, only at a new circuit"),
    dry_run: bool = typer.Option(
        False, help="Any weekend, past ones too: saved in reports/dry-runs, never in ledger/"
    ),
    config: str = "config/dpec.yaml",
) -> None:
    """Freeze this weekend's forecast and tyre decision into ledger/ before the session starts.
    Then commit and push it at once: GitHub's time on the push is the proof."""
    from dpec.record.freeze import TooLate, check_deadline, describe, make_forecast
    from dpec.record.ledger import LEDGER, event_folder, write_once

    s = load_settings(config)
    fastf1_source.enable_cache(s.paths.cache)
    try:
        record = make_forecast(
            s.paths.warehouse,
            season,
            round_no,
            checkpoint,
            s.adopted_team,
            race_laps,
            check_time=not dry_run,
        )
        root = Path("reports/dry-runs") if dry_run else LEDGER
        path = event_folder(root, season, round_no, record.circuit) / f"{checkpoint}.json"
        write_once(record, path, overwrite=dry_run)
    except (ValueError, KeyError, TooLate, FileExistsError) as problem:
        typer.echo(str(problem), err=True)
        raise typer.Exit(1) from None
    typer.echo(describe(record))
    typer.echo(f"\nSaved: {path}")
    if dry_run:
        try:
            check_deadline(record.frozen_at_utc, record.target_start_utc)
        except TooLate as late:
            typer.echo(f"Dry run. A real freeze now would be refused: {late}")
    else:
        typer.echo("Now commit and push it, before the deadline:")
        typer.echo(f'  git add {path} && git commit -m "Freeze {path.parent.name}" && git push')


@app.command()
def score(
    season: int = typer.Option(..., help="Season of the race"),
    round_no: int = typer.Option(..., "--round", help="Round of the race"),
    dry_run: bool = typer.Option(False, help="Score a dry run in reports/dry-runs instead"),
    config: str = "config/dpec.yaml",
) -> None:
    """Score a frozen weekend after the race: writes score.json next to the frozen files,
    which it never changes."""
    from dpec.record.ledger import LEDGER, write_once
    from dpec.record.score import score_weekend, summary

    s = load_settings(config)
    root = Path("reports/dry-runs") if dry_run else LEDGER
    folders = sorted((root / str(season)).glob(f"{round_no:02d}-*"))
    if not folders:
        typer.echo(f"nothing frozen for {season} round {round_no} in {root}/", err=True)
        raise typer.Exit(1)
    try:
        result = score_weekend(s.paths.warehouse, folders[0])
        write_once(result, folders[0] / "score.json", overwrite=dry_run)
    except (ValueError, FileExistsError) as problem:
        typer.echo(str(problem), err=True)
        raise typer.Exit(1) from None
    typer.echo(summary(result).to_string(index=False, float_format="%.3f"))
    for checkpoint in result.checkpoints:
        for car in checkpoint.our_cars:
            where = {True: "inside", False: "outside", None: "no"}[car.inside_range]
            typer.echo(
                f"{checkpoint.checkpoint}: {car.driver_code} ★ forecast "
                f"{car.predicted_gap_pct:+.2f}%, race {car.actual_gap_pct:+.2f}% ({where} range)"
            )
    d = result.decision
    if d:
        right = {True: "right", False: "wrong", None: "not known"}[d.stops_right]
        typer.echo(
            f"Decision '{d.call}': top 10 made {d.actual_top10_stops} stop(s), {right}; "
            f"tyre wear {d.actual_tyre_wear} (inside range: {d.tyre_wear_inside_range}); "
            f"first stops inside the window: {d.inside_window} of {d.green_first_stops}"
        )
    typer.echo(f"Verdict: {result.verdict}")
    typer.echo(f"Saved: {folders[0] / 'score.json'}")


@app.command()
def ledger(
    since: str | None = typer.Option(
        None, help="A commit: fail if a ledger file changed or was deleted since then"
    ),
    late_check: bool = typer.Option(
        False, help="CI only: forecasts added since --since must arrive before their deadline"
    ),
) -> None:
    """Check the public record: every file valid, and unchanged since it was frozen."""
    import subprocess
    from datetime import UTC, datetime

    from dpec.record.ledger import LEDGER, git_changes, late, problems

    found = problems()
    if since and set(since) != {"0"}:  # all zeros: a new branch, nothing to compare with
        try:
            changes = git_changes(since)
        except subprocess.CalledProcessError:
            typer.echo(f"commit {since} isn't in the history (was it rewritten?)", err=True)
            raise typer.Exit(1) from None
        found += [
            f"{path}: changed or deleted after it was pushed" for st, path in changes if st != "A"
        ]
        if late_check:
            added = [Path(path) for st, path in changes if st == "A"]
            found += late(added, datetime.now(UTC))
    files = len(list(LEDGER.rglob("*.json")))
    for problem in found:
        typer.echo(problem)
    if found:
        typer.echo(f"\n{len(found)} problem(s) in the ledger ({files} files)")
        raise typer.Exit(1)
    typer.echo(f"Ledger OK: {files} files, every one as it was frozen")


@app.command()
def pretend(
    season: int = typer.Option(..., help="A past season: every dry race in it is frozen and scored"),
    checkpoint: str = typer.Option("after_quali", help="after_quali or after_practice"),
    config: str = "config/dpec.yaml",
) -> None:
    """A pretend ledger: freeze and score every dry race of a past season the live way (as dry
    runs, in reports/dry-runs). It must match the backtest and the replay: same numbers."""
    import pandas as pd

    from dpec.forecasting.targets import forecast_table
    from dpec.record.freeze import make_forecast
    from dpec.record.ledger import event_folder, write_once
    from dpec.record.score import score_weekend

    s = load_settings(config)
    table = forecast_table(s.paths.warehouse)
    races = table.loc[table["season"] == season, ["round", "circuit"]].drop_duplicates()
    rows, frozen = [], []
    for race in races.itertuples():
        f = make_forecast(
            s.paths.warehouse, season, race.round, checkpoint, s.adopted_team, check_time=False
        )
        folder = event_folder(Path("reports/dry-runs"), season, race.round, f.circuit)
        write_once(f, folder / f"{checkpoint}.json", overwrite=True)
        result = score_weekend(s.paths.warehouse, folder)
        write_once(result, folder / "score.json", overwrite=True)
        c, d = result.checkpoints[-1], result.decision
        rows.append(
            {
                "round": race.round,
                "circuit": race.circuit,
                "drivers": c.drivers_scored,
                "error_pct": c.mae_pct,
                "skill": c.skill_vs_team_form,
                "inside_range": c.inside_range,
                "call": d.call if d else "-",
                "stops_right": d.stops_right if d else None,
                "verdict": result.verdict,
            }
        )
        frozen += [
            {"round": race.round, "driver_code": x.driver_code, "frozen": x.predicted_gap_pct}
            for x in f.drivers
        ]
        typer.echo(f"  round {race.round:>2} {race.circuit:<16} {result.verdict}")
    out = pd.DataFrame(rows)
    report = Path("reports/pretend-ledger") / f"{season}-{checkpoint}.csv"  # small: kept in git
    report.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(report, index=False, float_format="%.4f")
    typer.echo("\n" + out.to_string(index=False, float_format="%.3f"))
    typer.echo(f"\nVerdicts: {out['verdict'].value_counts().to_dict()}")

    saved = s.paths.data / "forecasts" / "backtest.parquet"
    if saved.exists():  # same code path as the backtest, so the same numbers
        bt = pd.read_parquet(saved)
        bt = bt[
            (bt["forecaster"] == "shared_model")
            & (bt["season"] == season)
            & (bt["checkpoint"] == checkpoint)
        ]
        both = pd.DataFrame(frozen).merge(bt, on=["round", "driver_code"])
        gap = (both["frozen"] - both["predicted"]).abs().max()
        error = (both["frozen"] - both["actual"]).abs().mean()
        typer.echo(
            f"Against the backtest: {len(both)} drivers in both, largest difference "
            f"{gap:.4f}% (rounding), error {error:.3f}% here vs "
            f"{(both['predicted'] - both['actual']).abs().mean():.3f}% in the backtest"
        )
    typer.echo(f"Saved: {report}")


@app.command()
def schema() -> None:
    """Write the ledger's file formats to schemas/ as JSON Schema: anyone can check a frozen
    file against them without running this project."""
    import json

    from dpec.record.ledger import Forecast, Score

    folder = Path("schemas")
    folder.mkdir(exist_ok=True)
    for name, model in {"forecast": Forecast, "score": Score}.items():
        path = folder / f"{name}.schema.json"
        path.write_text(json.dumps(model.model_json_schema(), indent=2) + "\n", encoding="utf-8")
        typer.echo(f"Saved: {path}")

@app.command()
def debrief(
    season: int = typer.Option(..., help="Season of the race"),
    round_no: int = typer.Option(..., "--round", help="Round of the race"),
    config: str = "config/dpec.yaml",
) -> None:
    """After a race: where our cars' time went. Best qualifying lap split by part of the track,
    race gap split into pace, tyres and traffic, next to the forecast. Saved in reports/debriefs."""
    from dpec.debrief.report import file_name, make_debrief, to_markdown

    s = load_settings(config)
    try:
        d = make_debrief(
            s.paths.warehouse, s.paths.raw, s.paths.data, season, round_no, s.adopted_team
        )
    except ValueError as problem:
        typer.echo(str(problem), err=True)
        raise typer.Exit(1) from None
    page = to_markdown(d)
    out = Path("reports/debriefs") / file_name(d)  # small: kept in git as evidence
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    typer.echo(page)
    typer.echo(f"Saved: {out}")