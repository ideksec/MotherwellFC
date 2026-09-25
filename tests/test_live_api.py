"""Live checks against the real endpoints. Excluded by default; run with
`pytest -m live`. A known finished match: Motherwell 0-4 Aberdeen, 2026-09-15."""

import pytest

from steelmen.clean.footballdata import find_match, normalise
from steelmen.clean.match import parse_match_summary
from steelmen.io.espn import final_events, get_scoreboard, get_summary
from steelmen.io.footballdata import get_season_csv

pytestmark = pytest.mark.live


def test_espn_scoreboard_and_summary(tmp_path):
    scoreboard = get_scoreboard("sco.1", "2026-09-15", cache_dir=tmp_path)
    events = final_events(scoreboard)
    assert [e["id"] for e in events] == ["401878401"]
    summary = get_summary("sco.1", "401878401", cache_dir=tmp_path)
    match = parse_match_summary(summary, "sco.1")
    assert match["score"] == {"motherwell": 0, "opponent": 4}


def test_footballdata_current_season(tmp_path):
    frame = normalise(get_season_csv("2627", cache_dir=tmp_path))
    row = find_match(frame, "2026-09-15", "Motherwell", "Aberdeen")
    assert row is not None and float(row["HxG"]) > 0
