import typer

from telemetry_core.config import load_settings

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
def ingest() -> None:
    """Download data from the providers (built in step A3)."""
    typer.echo("not yet: built in step A3")