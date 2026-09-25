from steelmen.io import espn


def test_scoreboard_filters_to_motherwell_final(scoreboard_gameday):
    events = espn.final_events(scoreboard_gameday)
    assert [e["id"] for e in events] == ["401878401"]
    assert espn.event_status(events[0]) == "STATUS_FULL_TIME"


def test_empty_scoreboard(scoreboard_empty):
    assert espn.final_events(scoreboard_empty) == []


def test_not_final_is_excluded(scoreboard_gameday):
    event = next(e for e in scoreboard_gameday["events"] if "Motherwell" in e["name"])
    event["competitions"][0]["status"]["type"] = {"name": "STATUS_SCHEDULED", "completed": False}
    assert espn.final_events(scoreboard_gameday) == []


def test_scoreboard_cache_path_and_params(tmp_path, monkeypatch):
    seen = {}

    def fake(url, *, params, cache_path, force):
        seen.update(url=url, params=params, cache_path=cache_path)
        return {"events": []}

    monkeypatch.setattr(espn, "cached_get_json", fake)
    espn.get_scoreboard("sco.1", "2026-09-15", cache_dir=tmp_path)
    assert seen["params"] == {"dates": "20260915"}
    assert seen["cache_path"] == tmp_path / "espn" / "scoreboard" / "sco.1_20260915.json"
    assert seen["url"].endswith("/sco.1/scoreboard")


def test_schedule_events_are_league_only(schedule_266):
    assert all(espn.involves_team(e) for e in schedule_266["events"])
    assert all(espn.is_final(e) for e in schedule_266["events"])


def test_schedule_fixtures_switch(tmp_path, monkeypatch):
    seen = []

    def fake(url, *, params=None, cache_path, force):
        seen.append((params, cache_path.name))
        return {"events": []}

    monkeypatch.setattr(espn, "cached_get_json", fake)
    espn.get_team_schedule("sco.1", "266", cache_dir=tmp_path)
    espn.get_team_schedule("sco.1", "266", fixtures=True, cache_dir=tmp_path)
    assert seen == [
        (None, "sco.1_t266.json"),
        ({"fixture": "true"}, "sco.1_t266_fixtures.json"),
    ]


def test_standings_url_and_stamp(tmp_path, monkeypatch):
    seen = {}

    def fake(url, *, params=None, cache_path, force):
        seen.update(url=url, cache_path=cache_path)
        return {}

    monkeypatch.setattr(espn, "cached_get_json", fake)
    espn.get_standings("sco.1", cache_dir=tmp_path, stamp="2026-09-25")
    assert seen["url"].endswith("/v2/sports/soccer/sco.1/standings")
    assert seen["cache_path"].name == "sco.1_2026-09-25.json"
