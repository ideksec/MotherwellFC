import json
from pathlib import Path

import pandas as pd

from steelmen.clean.match import parse_match_summary
from steelmen.clean.matchlog import matchlog_row, upsert_matchlog
from steelmen.metrics.usage import player_match_rows, squad_usage
from steelmen.statpack import build_stat_pack
from steelmen.viz import usage_figure

REPO = Path(__file__).resolve().parent.parent


def _packs():
    folder = REPO / "data/processed/motherwell/statpacks"
    return [json.loads(p.read_text()) for p in sorted(folder.glob("*.json"))]


def test_usage_from_fixture_pack(summary_dundee, tmp_path):
    match = parse_match_summary(summary_dundee, "sco.1")
    provisional = {
        "match": match,
        "team_stats": {},
        "xg": {"available": False},
        "market": {"available": False},
        "footballdata_stats": {"available": False},
    }
    log = upsert_matchlog(tmp_path / "log.csv", [matchlog_row(provisional)], write=False)
    pack = build_stat_pack(summary=summary_dundee, league="sco.1", matchlog=log)
    usage = squad_usage([pack])
    assert len(usage) == 16  # 11 starters + 5 subs used
    lowry = usage[usage["name"] == "Alexander Lowry"].iloc[0]
    assert lowry["goals"] == 1 and lowry["minutes_est"] == 86 and lowry["starts"] == 1
    williams = usage[usage["name"] == "Dylan Williams"].iloc[0]
    assert williams["sub_apps"] == 1 and williams["minutes_est"] == 25
    assert list(usage.columns)[0] == "name"
    assert usage.iloc[0]["minutes_est"] == 90
    assert isinstance(usage, pd.DataFrame)


def test_usage_empty():
    assert squad_usage([]).empty


def test_usage_over_committed_packs(tmp_path):
    packs = _packs()
    if not packs:
        return
    usage = squad_usage(packs)
    rows = player_match_rows(packs)
    assert usage["minutes_est"].sum() == rows["minutes_est"].sum()
    assert usage["goals"].sum() == rows["goals"].sum()  # vendor player stats, not the score
    league = squad_usage(packs, competition="sco.1")
    assert league["minutes_est"].sum() <= usage["minutes_est"].sum()
    out = usage_figure(usage, tmp_path / "u.png", title="t", max_minutes=90 * len(packs))
    assert out.exists()
