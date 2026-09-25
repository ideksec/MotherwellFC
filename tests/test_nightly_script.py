"""Orchestration tests for scripts/nightly_motherwell.py with every fetcher
monkeypatched to return fixtures, so the flow runs offline end to end."""

import importlib.util
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from steelmen.utils.time import UK

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "nightly_motherwell.py"


@pytest.fixture
def nightly():
    spec = importlib.util.spec_from_file_location("nightly_motherwell", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def wired(nightly, monkeypatch, scoreboard_gameday, scoreboard_empty, summary_aberdeen,
          footballdata_frame, schedule_266, standings_payload, tmp_path):  # fmt: skip
    """Patch the network layer; return the module and a data root."""
    calls = {"scoreboard": [], "summary": []}

    def fake_scoreboard(league, date, *, cache_dir, force=False):
        calls["scoreboard"].append((league, date))
        if league == "sco.1" and date == "2026-09-15":
            return json.loads(json.dumps(scoreboard_gameday))
        return json.loads(json.dumps(scoreboard_empty))

    def fake_summary(league, event_id, *, cache_dir, force=False):
        calls["summary"].append((league, str(event_id)))
        path = cache_dir / "espn" / "summary" / f"{league}_{event_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary_aberdeen))
        return json.loads(json.dumps(summary_aberdeen))

    monkeypatch.setattr(nightly, "get_scoreboard", fake_scoreboard)
    monkeypatch.setattr(nightly, "get_summary", fake_summary)
    monkeypatch.setattr(nightly, "get_season_csv", lambda *a, **k: footballdata_frame.copy())
    upcoming = json.loads(json.dumps(schedule_266))
    for event in upcoming["events"]:
        event["competitions"][0]["status"]["type"] = {
            "name": "STATUS_SCHEDULED",
            "completed": False,
        }
    monkeypatch.setattr(
        nightly,
        "get_team_schedule",
        lambda *a, fixtures=False, **k: upcoming if fixtures else schedule_266,
    )
    monkeypatch.setattr(nightly, "get_standings", lambda *a, **k: standings_payload)
    monkeypatch.setattr(nightly, "next_events", lambda *a, **k: [
        {"idEvent": "1", "dateEvent": "2026-10-11", "strTimestamp": "2026-10-11T11:00:00",
         "strHomeTeam": "Motherwell", "strAwayTeam": "Celtic",
         "strLeague": "Scottish Premier League", "strVenue": "Fir Park"}
    ])  # fmt: skip
    monkeypatch.setattr(nightly, "FIGURES_DIR", tmp_path / "figures")

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 17, 3, 0, tzinfo=UK)

    monkeypatch.setattr(nightly, "datetime", FrozenDateTime)
    return nightly, tmp_path / "data", calls


def test_no_match_days_are_noops(wired, capsys):
    nightly, root, calls = wired
    nightly.main(["--date", "2026-09-16", "--data-root", str(root), "--skip-fixtures"])
    out = capsys.readouterr().out
    assert "RESULT: no-match 2026-09-16" in out
    assert not (root / "processed").exists() or not list(root.glob("processed/**/*.json"))


def test_match_day_writes_pack_log_and_figure(wired, capsys):
    nightly, root, calls = wired
    nightly.main(["--date", "2026-09-15", "--data-root", str(root)])
    out = capsys.readouterr().out
    assert "RESULT: wrote 2026-09-15 sco.1 event 401878401 L 0-4 home vs Aberdeen (with xG)" in out
    pack = json.loads(
        (root / "processed/motherwell/statpacks/2026-09-15_401878401.json").read_text()
    )
    assert pack["xg"]["available"] is True
    log = pd.read_csv(root / "processed/motherwell/matchlog_2026-27.csv", dtype={"espn_id": str})
    assert log["espn_id"].tolist() == ["401878401"]
    assert float(log["motherwell_xg"].iloc[0]) == 0.77
    assert (nightly.FIGURES_DIR / "2026-09-15_vs-aberdeen.png").exists()
    assert "RESULT: fixtures 8 upcoming (next 2026-08-02)" in out  # 7 ESPN + 1 TheSportsDB
    fixtures = pd.read_csv(root / "processed/motherwell/fixtures.csv")
    assert set(fixtures["source"]) == {"espn", "thesportsdb"}
    assert "RESULT: table updated (Motherwell 8th, 8 pts)" in out
    table = pd.read_csv(root / "processed/motherwell/table.csv")
    assert len(table) == 12 and "goals_for" in table.columns
    # second run is idempotent
    nightly.main(["--date", "2026-09-15", "--data-root", str(root), "--skip-fixtures"])
    assert "RESULT: exists 2026-09-15 sco.1 event 401878401" in capsys.readouterr().out
    assert len(calls["summary"]) == 1


def test_lookback_scans_every_league(wired, capsys):
    nightly, root, calls = wired
    nightly.main(["--days-back", "2", "--data-root", str(root), "--skip-fixtures"])
    dates = {d for _, d in calls["scoreboard"]}
    assert dates == {"2026-09-17", "2026-09-16", "2026-09-15"}
    leagues = {lg for lg, _ in calls["scoreboard"]}
    assert "sco.tennents" in leagues and "club.friendly" in leagues


def test_xg_retry_rebuilds_fresh_pack(wired, monkeypatch, capsys):
    nightly, root, calls = wired
    monkeypatch.setattr(nightly, "get_season_csv", lambda *a, **k: pd.DataFrame(
        columns=["Date", "HomeTeam", "AwayTeam"]))  # fmt: skip
    nightly.main(["--date", "2026-09-15", "--data-root", str(root), "--skip-fixtures"])
    assert "(NO xG)" in capsys.readouterr().out
    pack_path = root / "processed/motherwell/statpacks/2026-09-15_401878401.json"
    assert nightly.needs_xg_retry(pack_path, "2026-09-15") is True
    # once xG appears the pack is rebuilt and retries stop
    monkeypatch.setattr(nightly, "get_season_csv", lambda *a, **k: wired_frame())
    nightly.main(["--date", "2026-09-15", "--data-root", str(root), "--skip-fixtures"])
    assert "(with xG)" in capsys.readouterr().out
    assert nightly.needs_xg_retry(pack_path, "2026-09-15") is False


def wired_frame():
    return pd.read_csv(Path(__file__).parent / "fixtures" / "footballdata_SC0_sample.csv")


def test_dry_run_writes_nothing(wired, capsys):
    nightly, root, calls = wired
    nightly.main(["--date", "2026-09-15", "--data-root", str(root), "--dry-run"])
    out = capsys.readouterr().out
    assert "RESULT: dry-run 2026-09-15 sco.1 event 401878401" in out
    assert not (root / "processed").exists()


def test_refresh_table_handles_missing_team_and_ordinals(wired, monkeypatch, standings_payload):
    nightly, root, calls = wired
    entries = standings_payload["children"][0]["standings"]["entries"]
    for entry in entries:
        for stat in entry["stats"]:
            if stat["name"] == "rank" and entry["team"]["id"] == "266":
                stat["value"] = 1.0
    out = nightly.refresh_table(root=root, dry_run=True, force=False, stamp="x")
    assert out.startswith("RESULT: table updated (Motherwell 1st,")
    standings_payload["children"][0]["standings"]["entries"] = [
        e for e in entries if e["team"]["id"] != "266"
    ]
    out = nightly.refresh_table(root=root, dry_run=True, force=False, stamp="x")
    assert "Motherwell not listed" in out


def test_recent_dates_include_today(nightly):
    dates = nightly.recent_uk_dates(2, today=datetime(2026, 9, 17, 3, 0, tzinfo=UK))
    assert dates == ["2026-09-17", "2026-09-16", "2026-09-15"]
