import json
from pathlib import Path

import pandas as pd
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def summary_aberdeen() -> dict:
    """Motherwell 0-4 Aberdeen, Fir Park, 2026-09-15 (home loss, no Motherwell goals)."""
    return _load_json("espn_summary_401878401.json")


@pytest.fixture
def summary_dundee() -> dict:
    """Dundee 2-1 Motherwell, Dens Park, 2026-09-19 (away loss, penalty against)."""
    return _load_json("espn_summary_401878380.json")


@pytest.fixture
def scoreboard_gameday() -> dict:
    return _load_json("espn_scoreboard_gameday.json")


@pytest.fixture
def scoreboard_empty() -> dict:
    return _load_json("espn_scoreboard_empty.json")


@pytest.fixture
def schedule_266() -> dict:
    return _load_json("espn_schedule_266.json")


@pytest.fixture
def standings_payload() -> dict:
    """ESPN standings endpoint (trimmed), 12 teams after matchday 7."""
    return _load_json("espn_standings.json")


@pytest.fixture
def footballdata_frame() -> pd.DataFrame:
    return pd.read_csv(FIXTURES / "footballdata_SC0_sample.csv")


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES
