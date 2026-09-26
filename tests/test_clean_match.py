import pytest

from steelmen.clean import match as m


def test_match_summary_home_loss(summary_aberdeen):
    out = m.parse_match_summary(summary_aberdeen, "sco.1")
    assert out["espn_id"] == "401878401"
    assert out["date"] == "2026-09-15"  # 18:45Z kickoff is the same UK day
    assert out["kickoff_utc"] == "2026-09-15T18:45Z"
    assert out["home_away"] == "home"
    assert out["result"] == "L"
    assert out["score"] == {"motherwell": 0, "opponent": 4}
    assert out["opponent"]["slug"] == "aberdeen"
    assert out["venue"] == "Fir Park"
    assert out["attendance"] == 6965
    assert out["referee"] == "Steven Mclean"
    assert out["competition"] == {"code": "sco.1", "name": "Scottish Premiership"}


def test_match_summary_away(summary_dundee):
    out = m.parse_match_summary(summary_dundee, "sco.1")
    assert out["home_away"] == "away"
    assert out["opponent"]["name"] == "Dundee"
    assert out["opponent"]["slug"] == "dundee"
    assert out["score"] == {"motherwell": 1, "opponent": 2}


def test_events_are_labelled_and_ordered(summary_dundee):
    events = m.parse_events(summary_dundee)
    kinds = [(e["minute"], e["kind"], e["team"]) for e in events if e["kind"] != "substitution"]
    assert kinds[0] == (23, "penalty_goal", "opponent")
    assert (44, "goal", "motherwell") in kinds
    goals = [e for e in events if e["scoring"]]
    assert [g["player"] for g in goals] == ["Joe Westley", "Bradley Fink", "Alexander Lowry"]
    stoppage = [e for e in events if e["minute_display"] == "90'+3'"]
    assert stoppage and stoppage[0]["minute"] == 93
    subs = [e for e in events if e["kind"] == "substitution"]
    assert subs[0]["player_on"] and subs[0]["player_off"]
    minutes = [e["minute"] for e in events]
    assert minutes == sorted(minutes)


def test_extra_time_cup_tie(summary_leaguecup_aet):
    out = m.parse_match_summary(summary_leaguecup_aet, "sco.cis")
    assert out["result"] == "L" and out["decided_by"] == "aet"
    assert out["round"] == "Round 2" and out["leg"] is None
    assert out["competition"]["name"] == "Scottish League Cup"
    assert out["opponent"]["slug"] == "stenhousemuir"
    events = m.parse_events(summary_leaguecup_aet)
    goal = next(e for e in events if e["kind"] == "goal")
    assert goal["minute"] == 114 and goal["period"] == 4 and goal["team"] == "opponent"


def test_european_leg_drops_admin_events(summary_uecl):
    out = m.parse_match_summary(summary_uecl, "uefa.europa.conf_qual")
    assert out["leg"] == "1st Leg" and out["round"] == "Playoff Round"
    assert out["attendance"] is None  # ESPN wrote 0
    events = m.parse_events(summary_uecl)
    kinds = {e["kind"] for e in events}
    assert not kinds & {"kickoff", "halftime", "end-regular-time", "start-2nd-half", "other"}
    goals = [e for e in events if e["scoring"]]
    assert [g["kind"] for g in goals] == ["goal", "goal", "penalty_goal", "goal"]
    assert any(e["kind"] == "red_card" for e in events)
    assert goals[-1]["minute"] == 96


def test_penalty_shootout_uses_winner_flag(summary_leaguecup_aet):
    comp = summary_leaguecup_aet["header"]["competitions"][0]
    comp["status"]["type"]["name"] = "STATUS_FINAL_PEN"
    for c in comp["competitors"]:
        c["score"] = "1"
        c["shootoutScore"] = 4 if c["team"]["id"] == "266" else 3
        c["winner"] = c["team"]["id"] == "266"
    out = m.parse_match_summary(summary_leaguecup_aet, "sco.cis")
    assert out["result"] == "W" and out["decided_by"] == "pens"
    assert out["shootout"] == {"motherwell": 4, "opponent": 3}


def test_empty_box_score_is_unavailable(summary_aberdeen):
    for team in summary_aberdeen["boxscore"]["teams"]:
        for stat in team["statistics"]:
            stat["displayValue"] = "3" if stat["name"] == "yellowCards" else "0"
    stats = m.parse_team_stats(summary_aberdeen)
    assert stats == {"available": False, "motherwell": {}, "opponent": {}}


def test_team_stats(summary_aberdeen):
    stats = m.parse_team_stats(summary_aberdeen)
    assert stats["available"] is True
    assert stats["motherwell"]["shots"] == 12
    assert stats["motherwell"]["shots_on_target"] == 5
    assert stats["motherwell"]["possession_pct"] == 68.9
    assert stats["opponent"]["corners"] == 2
    assert stats["opponent"]["saves"] == 5


def test_lineups_and_minutes(summary_dundee):
    lineups = m.parse_lineups(summary_dundee)
    ours = lineups["motherwell"]
    assert ours["formation"] == "4-2-3-1"
    assert len(ours["starters"]) == 11
    assert ours["used_subs"] == 5
    longelo = next(p for p in ours["starters"] if p["name"] == "Emmanuel Longelo")
    assert longelo["subbed_out"] and longelo["off_minute"] == 65 and longelo["minutes_est"] == 65
    keeper = next(p for p in ours["starters"] if p["position"] == "G")
    assert keeper["minutes_est"] == 90
    williams = next(p for p in ours["bench"] if p["name"] == "Dylan Williams")
    assert williams["on_minute"] == 65 and williams["minutes_est"] == 25
    unused = [p for p in ours["bench"] if not p["subbed_in"]]
    assert all(p["minutes_est"] is None for p in unused)


def test_player_lines(summary_dundee):
    lines = m.parse_player_lines(m.parse_lineups(summary_dundee))
    assert lines["scorers"] == [{"name": "Alexander Lowry", "goals": 1}]
    assert lines["assists"] == [{"name": "Tom Sparrow", "assists": 1}]
    assert lines["booked"] == ["Dylan Williams"]
    assert lines["players_used"] == 16


def test_standings(summary_aberdeen):
    table = m.parse_standings(summary_aberdeen)
    assert table["motherwell"]["rank"] == 8
    assert table["motherwell"]["points"] == 8
    assert table["motherwell"]["teams"] == 12
    assert table["table"][0]["team"] == "Celtic"


def test_standings_absent():
    assert m.parse_standings({"standings": {}}) is None
    assert m.parse_standings({"children": []}) is None


def test_standings_endpoint_shape(standings_payload):
    table = m.parse_standings(standings_payload)
    assert table["motherwell"]["rank"] == 8
    assert table["table"][0]["team"] == "Celtic"
    assert table["table"][0]["goals_for"] == 14 and table["table"][0]["goals_against"] == 4


def test_standings_without_motherwell(standings_payload):
    entries = standings_payload["children"][0]["standings"]["entries"]
    standings_payload["children"][0]["standings"]["entries"] = [
        e for e in entries if e["team"]["id"] != "266"
    ]
    table = m.parse_standings(standings_payload)
    assert table["motherwell"] is None and len(table["table"]) == 11


def test_drift_raises(summary_aberdeen):
    del summary_aberdeen["header"]["competitions"][0]["competitors"]
    with pytest.raises(m.ParseError):
        m.parse_match_summary(summary_aberdeen, "sco.1")


def test_not_a_motherwell_match(summary_aberdeen):
    for c in summary_aberdeen["header"]["competitions"][0]["competitors"]:
        c["team"]["id"] = "999"
    with pytest.raises(m.ParseError):
        m.parse_match_summary(summary_aberdeen, "sco.1")
