import json
from datetime import datetime, timezone

import pandas as pd
import pytest

from steelmen.clean.footballdata import find_match, normalise
from steelmen.clean.match import parse_match_summary
from steelmen.clean.matchlog import MATCHLOG_COLUMNS, matchlog_row, upsert_matchlog
from steelmen.statpack import (
    STAT_PACK_VERSION,
    StatPackError,
    build_stat_pack,
    figure_filename,
    report_filename,
    stat_pack_path,
    validate_stat_pack,
    write_stat_pack,
)


def _pack(summary, footballdata_frame, tmp_path, league="sco.1"):
    frame = normalise(footballdata_frame)
    match = parse_match_summary(summary, league)
    home = match["home_away"] == "home"
    opp = match["opponent"]["name"]
    row = find_match(
        frame, match["date"], "Motherwell" if home else opp, opp if home else "Motherwell"
    )
    provisional = {
        "match": match,
        "team_stats": {},
        "xg": {"available": False},
        "market": {"available": False},
        "footballdata_stats": {"available": False},
    }
    log = upsert_matchlog(tmp_path / "log.csv", [matchlog_row(provisional)], write=False)
    return build_stat_pack(
        summary=summary,
        league=league,
        matchlog=log,
        footballdata_row=row,
        generated_at=datetime(2026, 9, 20, 3, 0, tzinfo=timezone.utc),
    )


def test_build_home_loss_with_xg(summary_aberdeen, footballdata_frame, tmp_path):
    pack = _pack(summary_aberdeen, footballdata_frame, tmp_path)
    validate_stat_pack(pack)
    assert pack["schema_version"] == STAT_PACK_VERSION
    assert pack["generated_at"] == "2026-09-20T03:00:00Z"
    assert pack["season"] == "2026-27"
    assert pack["sources"]["footballdata_xg"] is True
    assert pack["xg"]["motherwell"] == 0.77 and pack["xg"]["opponent"] == 0.92
    assert 0 < pack["xg"]["xpoints"] < 3
    assert pack["market"]["actual_points"] == 0
    assert pack["table"]["motherwell"]["rank"] == 8
    assert pack["rolling"]["last5_all"]["games"] == 1
    assert pack["rolling"]["season_league"]["form"] == "L"
    assert pack["figure"] == "reports/motherwell/figures/2026-09-15_vs-aberdeen.png"
    assert pack["notes"] == []
    assert len(json.dumps(pack)) < 30_000


def test_build_away_without_footballdata(summary_dundee, tmp_path):
    empty = pd.DataFrame(columns=["Date", "HomeTeam", "AwayTeam", "HxG", "AxG"])
    pack = _pack(summary_dundee, empty, tmp_path)
    validate_stat_pack(pack)
    assert pack["xg"] == {"available": False, "source": None}
    assert pack["market"] == {"available": False}
    assert "xG unavailable" in pack["notes"][0]


def test_non_league_has_no_table(summary_dundee, footballdata_frame, tmp_path):
    pack = _pack(summary_dundee, footballdata_frame, tmp_path, league="sco.cis")
    assert pack["table"] is None
    assert pack["xg"]["available"] is False
    assert report_filename(pack) == "2026-09-19_at-dundee_scottish-cup.md"


def test_filenames(summary_aberdeen, summary_dundee, footballdata_frame, tmp_path):
    home = _pack(summary_aberdeen, footballdata_frame, tmp_path)
    away = _pack(summary_dundee, footballdata_frame, tmp_path)
    assert report_filename(home) == "2026-09-15_vs-aberdeen.md"
    assert report_filename(away) == "2026-09-19_at-dundee.md"
    assert figure_filename(away) == "2026-09-19_at-dundee.png"
    assert stat_pack_path(tmp_path, "2026-09-15", "401878401") == (
        tmp_path / "processed" / "motherwell" / "statpacks" / "2026-09-15_401878401.json"
    )


def test_write_round_trip(summary_aberdeen, footballdata_frame, tmp_path):
    pack = _pack(summary_aberdeen, footballdata_frame, tmp_path)
    pack["_path"] = "should-not-be-written"
    path = write_stat_pack(pack, tmp_path)
    on_disk = json.loads(path.read_text())
    assert "_path" not in on_disk
    validate_stat_pack(on_disk)


def test_rolling_trims_to_this_match(
    summary_aberdeen, summary_dundee, footballdata_frame, tmp_path
):
    """Rebuilding an older pack must not see newer matches in its rolling block."""
    frame = normalise(footballdata_frame)
    rows = []
    for summary in (summary_aberdeen, summary_dundee):
        match = parse_match_summary(summary, "sco.1")
        rows.append(
            matchlog_row(
                {
                    "match": match,
                    "team_stats": {},
                    "xg": {"available": False},
                    "market": {"available": False},
                    "footballdata_stats": {"available": False},
                }
            )
        )
    log = pd.DataFrame(rows, columns=MATCHLOG_COLUMNS)
    pack = build_stat_pack(
        summary=summary_aberdeen,
        league="sco.1",
        matchlog=log,
        footballdata_row=find_match(frame, "2026-09-15", "Motherwell", "Aberdeen"),
    )
    assert pack["rolling"]["season_all"]["games"] == 1


def test_validate_rejects_bad_packs(summary_aberdeen, footballdata_frame, tmp_path):
    pack = _pack(summary_aberdeen, footballdata_frame, tmp_path)
    bad = dict(pack)
    bad["schema_version"] = 99
    with pytest.raises(StatPackError):
        validate_stat_pack(bad)
    bad = dict(pack)
    del bad["xg"]
    with pytest.raises(StatPackError):
        validate_stat_pack(bad)
    bad = json.loads(json.dumps(pack))
    bad["match"]["result"] = "X"
    with pytest.raises(StatPackError):
        validate_stat_pack(bad)
