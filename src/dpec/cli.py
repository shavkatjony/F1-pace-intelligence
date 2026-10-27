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