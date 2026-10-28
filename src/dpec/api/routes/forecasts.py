"""Addresses for Phase C: the forecasts `dpec backtest` saved in data/forecasts/.

Read-only, like the rest of the API. A weekend's forecast is shown exactly as the walk-forward
test made it before that race: the guess, its 80% range and chances, next to what happened.
"""

from fastapi import APIRouter, HTTPException, Request

from dpec.api.routes.analytics import rows

router = APIRouter()


@router.get("/weekends/{season}/{round_no}/forecast")
def forecast(request: Request, season: int, round_no: int) -> list[dict]:
    """The shared model's race pace forecast for one weekend, at both checkpoints."""
    saved = request.app.state.settings.paths.data / "forecasts" / "backtest.parquet"
    if not saved.exists():
        raise HTTPException(404, "no forecasts yet: run `uv run dpec backtest`")
    found = rows(
        request,
        """
        SELECT f.checkpoint, f.driver_code, f.lineage, f.predicted, f.low, f.high, f.actual,
            f.p_best, f.p_top3, f.mean_rank, f.p_beats_teammate,
            r.grid_position, r.finish_position
        FROM read_parquet(?) AS f
        LEFT JOIN core_results AS r
            ON r.season = f.season AND r.round = f.round AND r.driver_code = f.driver_code
            AND r.session_type = 'R'
        WHERE f.forecaster = 'shared_model' AND f.season = ? AND f.round = ?
        ORDER BY f.checkpoint, f.predicted
        """,
        [str(saved), season, round_no],
    )
    if not found:
        raise HTTPException(
            404,
            f"no forecast for {season} round {round_no}: forecasts start in 2023 "
            "(2022 only teaches the model), and wet races are not forecast (decision 0011)",
        )
    return found

# read it that , you dont need ice americano
# read_parquet(?): DuckDB reads the saved guesses straight from the Parquet file and joins them with core_results, in one query.
# Two different 404s: no backtest yet, or no forecast for that weekend (2022, or a wet race).