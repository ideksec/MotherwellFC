"""Form and season summaries over the match log.

All functions accept the match log as a DataFrame (see clean.matchlog) and
are pure. `competition` filters to one competition code (e.g. "sco.1");
None means every competition.
"""

import math

import pandas as pd

from steelmen.metrics.xg import xpoints

POINTS = {"W": 3, "D": 1, "L": 0}


def _filtered(log: pd.DataFrame, competition: str | None) -> pd.DataFrame:
    if log.empty:
        return log
    frame = log.copy()
    if competition:
        frame = frame[frame["competition_code"] == competition]
    return frame.sort_values(["kickoff_utc", "espn_id"]).reset_index(drop=True)


def through_match(log: pd.DataFrame, *, espn_id: str) -> pd.DataFrame:
    """The log up to and including one match, in kickoff order."""
    frame = _filtered(log, None)
    positions = (
        frame.index[frame["espn_id"].astype(str) == str(espn_id)] if not frame.empty else []
    )
    if len(positions) == 0:
        raise KeyError(f"espn_id {espn_id} not in match log")
    return frame.iloc[: positions[0] + 1].reset_index(drop=True)


def streak(results: list[str]) -> str:
    """ "W3", "D1", "L2" or "" — most recent result first."""
    if not results:
        return ""
    last = results[-1]
    count = 0
    for r in reversed(results):
        if r != last:
            break
        count += 1
    return f"{last}{count}"


def run_lengths(results: list[str]) -> dict:
    unbeaten = winless = 0
    for r in reversed(results):
        if r != "L":
            unbeaten += 1
        else:
            break
    for r in reversed(results):
        if r != "W":
            winless += 1
        else:
            break
    return {"unbeaten": unbeaten, "winless": winless}


def _num(value) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) else number


def last_n_summary(log: pd.DataFrame, n: int = 5, *, competition: str | None = None) -> dict:
    """Record, goals, xG and streak context over the last n matches in the log."""
    frame = _filtered(log, competition)
    window = frame.tail(n)
    results = [str(r) for r in window["result"].tolist()]
    gf = int(pd.to_numeric(window["motherwell_goals"], errors="coerce").fillna(0).sum())
    ga = int(pd.to_numeric(window["opponent_goals"], errors="coerce").fillna(0).sum())
    xg_rows = window.dropna(subset=["motherwell_xg", "opponent_xg"])
    xg_for = float(pd.to_numeric(xg_rows["motherwell_xg"], errors="coerce").sum())
    xg_against = float(pd.to_numeric(xg_rows["opponent_xg"], errors="coerce").sum())
    xpts = sum(
        xpoints(_num(r.motherwell_xg) or 0.0, _num(r.opponent_xg) or 0.0)
        for r in xg_rows.itertuples()
    )
    points = sum(POINTS[r] for r in results)
    games = len(results)
    return {
        "games": games,
        "wins": results.count("W"),
        "draws": results.count("D"),
        "losses": results.count("L"),
        "points": points,
        "ppg": round(points / games, 2) if games else None,
        "goals_for": gf,
        "goals_against": ga,
        "goal_diff": gf - ga,
        "clean_sheets": int((pd.to_numeric(window["opponent_goals"], errors="coerce") == 0).sum()),
        "failed_to_score": int(
            (pd.to_numeric(window["motherwell_goals"], errors="coerce") == 0).sum()
        ),
        "xg_games": int(len(xg_rows)),
        "xg_for": round(xg_for, 2),
        "xg_against": round(xg_against, 2),
        "xg_diff": round(xg_for - xg_against, 2),
        "xpoints": round(float(xpts), 2),
        "form": "".join(results),
        "streak": streak(results),
        **run_lengths(results),
    }


def season_summary(log: pd.DataFrame, *, competition: str | None = None) -> dict:
    frame = _filtered(log, competition)
    summary = last_n_summary(frame, n=len(frame) if len(frame) else 1, competition=None)
    summary["form_last5"] = "".join(str(r) for r in frame["result"].tail(5).tolist())
    home = frame[frame["home_away"] == "home"]
    away = frame[frame["home_away"] == "away"]
    summary["home_record"] = (
        f"{(home['result'] == 'W').sum()}-{(home['result'] == 'D').sum()}-"
        f"{(home['result'] == 'L').sum()}"
    )
    summary["away_record"] = (
        f"{(away['result'] == 'W').sum()}-{(away['result'] == 'D').sum()}-"
        f"{(away['result'] == 'L').sum()}"
    )
    return summary
