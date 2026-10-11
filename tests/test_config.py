import pytest
import yaml
from pydantic import ValidationError

from telemetry_core.config import load_settings


def write_config(tmp_path, data):
    path = tmp_path / "dpec.yaml"
    path.write_text(yaml.safe_dump(data))
    return path


def good_config():
    return yaml.safe_load(open("config/dpec.yaml"))


def test_real_config_loads():
    s = load_settings("config/dpec.yaml")
    assert s.team_name == "DPEC"
    assert s.seasons == sorted(s.seasons)


def test_season_before_2018_fails(tmp_path):
    data = good_config()
    data["seasons"] = [2010, 2024]
    with pytest.raises(ValidationError):
        load_settings(write_config(tmp_path, data))


def test_typo_key_fails(tmp_path):
    data = good_config()
    data["adopted_teem"] = data.pop("adopted_team")
    with pytest.raises(ValidationError):
        load_settings(write_config(tmp_path, data))


def test_wrong_mode_fails(tmp_path):
    data = good_config()
    data["mode"] = "online"
    with pytest.raises(ValidationError):
        load_settings(write_config(tmp_path, data))

def test_grid_step_too_big_fails(tmp_path):
    data = good_config()
    data["grid_step_m"] = 100
    with pytest.raises(ValidationError):
        load_settings(write_config(tmp_path, data))
        