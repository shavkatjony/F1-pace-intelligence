from pathlib import Path

from telemetry_core.paths import session_folder, slug


def test_slug():
    assert slug("Bahrain Grand Prix") == "bahrain_grand_prix"
    assert slug("São Paulo Grand Prix") == "s_o_paulo_grand_prix"
    assert slug("Practice 1") == "practice_1"


def test_session_folder():
    folder = session_folder(Path("data/raw"), "fastf1", 2024, 1, "Bahrain Grand Prix", "Race")
    assert folder == Path("data/raw/fastf1/season=2024/event=01_bahrain_grand_prix/session=race")
