"""football-data.co.uk rows -> xG, match stats and market blocks."""

import pandas as pd

from steelmen.metrics.market import implied_probabilities

NUMERIC = [
    "FTHG", "FTAG", "HTHG", "HTAG", "HxG", "AxG",
    "HS", "AS", "HST", "AST", "HF", "AF", "HC", "AC", "HY", "AY", "HR", "AR",
    "B365H", "B365D", "B365A", "AvgH", "AvgD", "AvgA", "Avg>2.5", "Avg<2.5",
]  # fmt: skip


def normalise(frame: pd.DataFrame) -> pd.DataFrame:
    """ISO dates, numeric stats, stripped team names. Safe to call twice."""
    out = frame.copy()
    if "date" not in out.columns:
        out["date"] = pd.to_datetime(out["Date"], dayfirst=True, errors="coerce").dt.strftime(
            "%Y-%m-%d"
        )
    for col in NUMERIC:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    out["HomeTeam"] = out["HomeTeam"].astype(str).str.strip()
    out["AwayTeam"] = out["AwayTeam"].astype(str).str.strip()
    return out


def find_match(frame: pd.DataFrame, date: str, home: str, away: str) -> pd.Series | None:
    rows = frame[
        (frame["date"] == date) & (frame["HomeTeam"] == home) & (frame["AwayTeam"] == away)
    ]
    if rows.empty:
        return None
    return rows.iloc[0]


def _pick(row: pd.Series, home_key: str, away_key: str, motherwell_home: bool):
    ours = row.get(home_key if motherwell_home else away_key)
    theirs = row.get(away_key if motherwell_home else home_key)
    return (
        None if pd.isna(ours) else float(ours),
        None if pd.isna(theirs) else float(theirs),
    )


def xg_block(row: pd.Series | None, motherwell_home: bool, *, source: str) -> dict:
    if row is None:
        return {"available": False, "source": None}
    ours, theirs = _pick(row, "HxG", "AxG", motherwell_home)
    if ours is None or theirs is None:
        return {"available": False, "source": source, "note": "row present, xG blank"}
    return {
        "available": True,
        "source": source,
        "motherwell": round(ours, 2),
        "opponent": round(theirs, 2),
        "diff": round(ours - theirs, 2),
    }


def stats_block(row: pd.Series | None, motherwell_home: bool) -> dict:
    """Shots/corners/cards from football-data — a cross-check for ESPN's box score."""
    if row is None:
        return {"available": False}
    keys = {
        "shots": ("HS", "AS"),
        "shots_on_target": ("HST", "AST"),
        "fouls": ("HF", "AF"),
        "corners": ("HC", "AC"),
        "yellow_cards": ("HY", "AY"),
        "red_cards": ("HR", "AR"),
        "ht_goals": ("HTHG", "HTAG"),
    }
    out: dict = {"available": True, "motherwell": {}, "opponent": {}}
    for name, (h, a) in keys.items():
        ours, theirs = _pick(row, h, a, motherwell_home)
        out["motherwell"][name] = None if ours is None else int(ours)
        out["opponent"][name] = None if theirs is None else int(theirs)
    return out


def market_block(row: pd.Series | None, motherwell_home: bool, result: str) -> dict:
    """Pre-match Bet365 odds (B365H/D/A, the earlier price, not the closing
    B365C* columns) -> implied probabilities and a points-vs-market verdict."""
    if row is None:
        return {"available": False}
    h, d, a = row.get("B365H"), row.get("B365D"), row.get("B365A")
    if any(pd.isna(x) for x in (h, d, a)):
        return {"available": False, "note": "row present, odds blank"}
    probs = implied_probabilities(float(h), float(d), float(a))
    p_win = probs["home"] if motherwell_home else probs["away"]
    p_loss = probs["away"] if motherwell_home else probs["home"]
    expected_points = 3 * p_win + probs["draw"]
    actual_points = {"W": 3, "D": 1, "L": 0}[result]
    return {
        "available": True,
        "source": "football-data.co.uk (Bet365 pre-match)",
        "odds": {"home": float(h), "draw": float(d), "away": float(a)},
        "motherwell_win_prob": round(p_win, 3),
        "draw_prob": round(probs["draw"], 3),
        "motherwell_loss_prob": round(p_loss, 3),
        "expected_points": round(expected_points, 2),
        "actual_points": actual_points,
        "points_vs_market": round(actual_points - expected_points, 2),
        "favourite": "motherwell" if p_win > p_loss else "opponent",
        "over_2_5_price": None if pd.isna(row.get("Avg>2.5")) else float(row.get("Avg>2.5")),
    }
