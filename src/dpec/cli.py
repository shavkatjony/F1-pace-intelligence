"""The `dpec` commands."""

# dear viewer , please ,before change anything ,
# spend a lots of time as much as possible about f1 rules and regulations and also
# how the engineers work in the backend ,
# because if you f**k up , this possible  a lots of days to fix

import typer

# we import here the created warehouse that runs the sql and sql (assume that there are temporary files)
from telemetry_core import warehouse
from telemetry_core.config import load_settings
from telemetry_core.ingestion import fastf1_source
from telemetry_core.ingestion.writer import is_saved, write_session
from telemetry_core.paths import session_folder

app = typer.Typer(help="Team DPEC weekend forecaster.", no_args_is_help=True)


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
                try:
                    tables, meta = fastf1_source.fetch_session(year, rnd, name)
                except fastf1_source.RateLimitError:
                    typer.echo("FastF1 rate limit reached. Run the same command again later;")
                    typer.echo("everything saved so far is kept and will be skipped.")
                    raise typer.Exit(code=1) from None
                except Exception as error:  # noqa: BLE001 - one bad session must not stop the rest
                    failed.append(f"{year} round {rnd} {name}: {error}")
                    typer.echo(f"  {name:<20} FAILED: {error}")
                    continue
                manifest = write_session(tables, meta, folder)
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
    params = {"raw": s.paths.raw.as_posix(), "slow_lap_pct": s.slow_lap_pct}
    counts = warehouse.build(s.paths.sql, s.paths.warehouse, params)
    for table, rows in counts.items():
        typer.echo(f"{table:<20} {rows:>10,} rows")
    typer.echo(f"Saved to {s.paths.warehouse}")


@app.command()
def sql(query: str, config: str = "config/dpec.yaml") -> None:
    """Run one SQL query on the warehouse and print the result."""
    s = load_settings(config)
    result = warehouse.query(s.paths.warehouse, query)
    typer.echo(result.to_string(index=False, max_rows=60))
