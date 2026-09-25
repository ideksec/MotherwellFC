from steelmen.clean.matchlog import MATCHLOG_COLUMNS, load_matchlog, upsert_matchlog


def _row(espn_id, kickoff, result="W"):
    return {
        "espn_id": espn_id, "date": kickoff[:10], "kickoff_utc": kickoff, "season": "2026-27",
        "competition_code": "sco.1", "competition": "Scottish Premiership",
        "home_away": "home", "opponent": "X", "opponent_slug": "x", "result": result,
        "points": {"W": 3, "D": 1, "L": 0}[result], "motherwell_goals": 1, "opponent_goals": 0,
    }  # fmt: skip


def test_upsert_creates_sorts_and_dedupes(tmp_path):
    path = tmp_path / "matchlog_2026-27.csv"
    upsert_matchlog(path, [_row("2", "2026-08-09T14:00Z"), _row("1", "2026-08-02T15:30Z")])
    log = load_matchlog(path)
    assert log["espn_id"].tolist() == ["1", "2"]
    assert list(log.columns) == MATCHLOG_COLUMNS
    upsert_matchlog(path, [_row("2", "2026-08-09T14:00Z", result="L")])
    log = load_matchlog(path)
    assert len(log) == 2
    assert log.loc[log["espn_id"] == "2", "result"].iloc[0] == "L"


def test_write_false_does_not_touch_disk(tmp_path):
    path = tmp_path / "matchlog.csv"
    merged = upsert_matchlog(path, [_row("1", "2026-08-02T15:30Z")], write=False)
    assert len(merged) == 1 and not path.exists()


def test_load_missing_is_empty(tmp_path):
    assert load_matchlog(tmp_path / "nope.csv").empty
