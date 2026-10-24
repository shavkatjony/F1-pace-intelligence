from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Paths(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: Path
    cache: Path
    raw: Path
    warehouse: Path
    sql: Path
    seeds: Path
    log: Path
    dictionary: Path


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown keys (typos) are errors

    team_name: str
    adopted_team: str = Field(min_length=1)
    seasons: list[int]
    grid_step_m: float = Field(gt=0, le=50)
    slow_lap_pct: float = Field(
        gt=100, le=150
    )  # (gt=100: a limit of 100% or less would call almost every lap slow. le=150: above that the rule does nothing.)
    fuel_effect_s_per_lap: float = Field(ge=0, le=0.2)  # lap time gained per lap of fuel burnt
    long_run_min_laps: int = Field(ge=3, le=20)  # clean laps in a row that make a long run
    long_run_band_pct: float = Field(gt=0, le=10)  # long-run laps stay this close to the median
    push_lap_band_pct: float = Field(gt=0, le=5)  # push laps are this close to the best lap
    mode: Literal["local", "public"]
    paths: Paths

    @field_validator("seasons")
    @classmethod
    def check_seasons(cls, seasons: list[int]) -> list[int]:
        if not seasons:
            raise ValueError("seasons must not be empty")
        too_early = [s for s in seasons if s < 2018]
        if too_early:
            raise ValueError(f"FastF1 telemetry starts in 2018, got {too_early}")
        return sorted(seasons)


def load_settings(path: str | Path = "config/dpec.yaml") -> Settings:
    """Read the YAML file and return checked settings."""
    with open(path) as f:
        raw = yaml.safe_load(f)
    return Settings.model_validate(raw)
