
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


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown keys (typos) are errors

    team_name: str
    adopted_team: str = Field(min_length=1)
    seasons: list[int]
    grid_step_m: float = Field(gt=0, le=50)
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