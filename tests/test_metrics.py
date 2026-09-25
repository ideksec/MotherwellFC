import math

import pandas as pd
import pytest

from steelmen.clean.matchlog import MATCHLOG_COLUMNS
from steelmen.metrics import form, market, xg
from steelmen.metrics.discipline import discipline_summary


def _log(rows):
    frame = pd.DataFrame(rows)
    for col in MATCHLOG_COLUMNS:
        if col not in frame.columns:
            frame[col] = None
    return frame[MATCHLOG_COLUMNS]


SAMPLE = _log(
    [
        {"espn_id": "1", "kickoff_utc": "2026-08-02T15:30Z", "competition_code": "sco.1",
         "home_away": "away", "result": "W", "motherwell_goals": 2, "opponent_goals": 1,
         "motherwell_xg": 2.0, "opponent_xg": 1.92, "motherwell_corners": 3, "opponent_corners": 5,
         "motherwell_yellows": 1, "motherwell_reds": 0, "opponent_yellows": 2, "opponent_reds": 0},
        {"espn_id": "2", "kickoff_utc": "2026-08-09T14:00Z", "competition_code": "sco.1",
         "home_away": "home", "result": "D", "motherwell_goals": 0, "opponent_goals": 0,
         "motherwell_xg": 0.89, "opponent_xg": 0.44, "motherwell_corners": 6,
         "opponent_corners": 2,
         "motherwell_yellows": 0, "motherwell_reds": 0, "opponent_yellows": 1, "opponent_reds": 0},
        {"espn_id": "3", "kickoff_utc": "2026-08-16T14:00Z", "competition_code": "sco.tennents",
         "home_away": "home", "result": "L", "motherwell_goals": 1, "opponent_goals": 3,
         "motherwell_xg": None, "opponent_xg": None},
    ]
)  # fmt: skip


def test_implied_probabilities_remove_overround():
    probs = market.implied_probabilities(2.0, 3.5, 3.6)
    assert abs(probs["home"] + probs["draw"] + probs["away"] - 1) < 1e-9
    assert probs["overround"] > 0
    assert probs["home"] > probs["away"]


def test_implied_probabilities_reject_bad_odds():
    with pytest.raises(ValueError):
        market.implied_probabilities(0, 3, 3)


def test_moneyline_to_decimal():
    assert abs(market.moneyline_to_decimal(-120) - 1.8333) < 1e-3
    assert market.moneyline_to_decimal(300) == 4.0


def test_xpoints_bounds_and_symmetry():
    assert 0 < xg.xpoints(1.0, 1.0) < 3
    assert xg.xpoints(3.0, 0.2) > xg.xpoints(0.2, 3.0)
    assert math.isclose(xg.xpoints(0.0, 0.0), 1.0)  # certain 0-0 is one point


def test_last_n_summary_all_comps():
    out = form.last_n_summary(SAMPLE, 5)
    assert (out["wins"], out["draws"], out["losses"]) == (1, 1, 1)
    assert out["points"] == 4 and out["ppg"] == 1.33
    assert out["form"] == "WDL" and out["streak"] == "L1"
    assert out["xg_games"] == 2 and out["xg_diff"] == 0.53
    assert out["unbeaten"] == 0 and out["winless"] == 2


def test_last_n_summary_league_only():
    out = form.last_n_summary(SAMPLE, 5, competition="sco.1")
    assert out["games"] == 2 and out["form"] == "WD" and out["unbeaten"] == 2


def test_through_match_trims():
    trimmed = form.through_match(SAMPLE, espn_id="2")
    assert trimmed["espn_id"].tolist() == ["1", "2"]
    with pytest.raises(KeyError):
        form.through_match(SAMPLE, espn_id="99")


def test_season_summary_records():
    out = form.season_summary(SAMPLE, competition="sco.1")
    assert out["home_record"] == "0-1-0" and out["away_record"] == "1-0-0"
    assert out["form_last5"] == "WD"


def test_empty_log():
    out = form.last_n_summary(_log([]), 5)
    assert out["games"] == 0 and out["ppg"] is None and out["form"] == ""
    with pytest.raises(KeyError):
        form.through_match(_log([]), espn_id="1")


def test_discipline_summary():
    out = discipline_summary(SAMPLE)
    assert out["corners_for"] == 9 and out["corners_against"] == 7
    assert out["yellows"] == 1 and out["opponent_yellows"] == 3
