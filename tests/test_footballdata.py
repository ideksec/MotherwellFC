import pandas as pd

from steelmen.clean import footballdata as fd
from steelmen.io.providers import FootballDataXG


def test_normalise_dates_and_numbers(footballdata_frame):
    frame = fd.normalise(footballdata_frame)
    assert frame["date"].iloc[0] == "2026-07-31"
    assert frame["HxG"].dtype.kind == "f"


def test_find_match_and_blocks(footballdata_frame):
    frame = fd.normalise(footballdata_frame)
    row = fd.find_match(frame, "2026-09-15", "Motherwell", "Aberdeen")
    assert row is not None
    xg = fd.xg_block(row, True, source="test")
    assert xg["available"] and xg["motherwell"] == 0.77 and xg["opponent"] == 0.92
    market = fd.market_block(row, True, "L")
    assert market["available"]
    assert market["actual_points"] == 0
    assert 0 < market["motherwell_win_prob"] < 1
    assert (
        abs(
            market["motherwell_win_prob"]
            + market["draw_prob"]
            + market["motherwell_loss_prob"]
            - 1
        )
        < 1e-9
    )
    stats = fd.stats_block(row, True)
    assert stats["motherwell"]["ht_goals"] == 0 and stats["opponent"]["ht_goals"] == 1


def test_away_perspective(footballdata_frame):
    frame = fd.normalise(footballdata_frame)
    row = fd.find_match(frame, "2026-09-19", "Dundee", "Motherwell")
    xg = fd.xg_block(row, False, source="test")
    assert xg["motherwell"] == 1.1 and xg["opponent"] == 1.36
    market = fd.market_block(row, False, "L")
    assert market["odds"]["away"] == float(row["B365A"])


def test_missing_row_blocks():
    assert fd.xg_block(None, True, source="x") == {"available": False, "source": None}
    assert fd.market_block(None, True, "W") == {"available": False}
    assert fd.stats_block(None, True) == {"available": False}


def test_blank_xg_is_unavailable(footballdata_frame):
    frame = fd.normalise(footballdata_frame)
    row = fd.find_match(frame, "2026-09-15", "Motherwell", "Aberdeen").copy()
    row["HxG"] = float("nan")
    assert fd.xg_block(row, True, source="x")["available"] is False


def test_provider_interface(footballdata_frame):
    provider = FootballDataXG(footballdata_frame)
    assert provider.match_xg("2026-09-15", "Motherwell", "Aberdeen") == {
        "home": 0.77,
        "away": 0.92,
        "shots": None,
    }
    assert provider.match_xg("2026-09-15", "Motherwell", "Celtic") is None
    assert isinstance(provider.frame, pd.DataFrame)
