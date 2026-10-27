"""The pit wall's web API: read-only, JSON, one small question per address.

The windows in web/app/ ask these addresses for data. Nothing here writes: every request
opens its own read-only connection to the warehouse, so `dpec build` can still run while
the app is open.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from dpec.api.routes import analytics
from telemetry_core.config import load_settings

WEB_APP = Path("web/app")


def create_app(config: str = "config/dpec.yaml") -> FastAPI:
    """Build the app. Tests call this with a config that points at a small fake warehouse."""
    app = FastAPI(
        title="Team DPEC pit wall",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.state.settings = load_settings(config)
    app.include_router(analytics.router, prefix="/api")
    if WEB_APP.exists():  # the app's own files; /api/... above is matched first
        app.mount("/", StaticFiles(directory=WEB_APP, html=True), name="app")
    return app
