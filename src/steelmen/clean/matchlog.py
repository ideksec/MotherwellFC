"""The season match log — one row per Motherwell match, all competitions.

Committed as data/processed/motherwell/matchlog_{season}.csv. Upserts are
keyed on espn_id and the file is rewritten sorted by kickoff, so re-runs
are idempotent and rows only ever get richer.
"""

from pathlib import Path

import pandas as pd

MATCHLOG_COLUMNS = [
    "espn_id", "date", "kickoff_utc", "season", "competition_code", "competition",
    "home_away", "opponent", "opponent_slug", "result", "points",
    "motherwell_goals", "opponent_goals", "ht_motherwell", "ht_opponent",
    "venue", "attendance", "referee",
    "motherwell_xg", "opponent_xg",
    "motherwell_shots", "opponent_shots", "motherwell_sot", "opponent_sot",
    "motherwell_possession", "motherwell_corners", "opponent_corners",
    "motherwell_yellows", "motherwell_reds", "opponent_yellows", "opponent_reds",
    "odds_motherwell", "odds_draw", "odds_opponent",
    "statpack",
]  # fmt: skip

POINTS = {"W": 3, "D": 1, "L": 0}


def matchlog_row(pack: dict) -> dict:
    """Flatten a stat pack into a match-log row."""
    match = pack["match"]
    stats = pack.get("team_stats", {})
    ours, theirs = stats.get("motherwell", {}), stats.get("opponent", {})
    xg = pack.get("xg", {})
    market = pack.get("market", {})
    fd = pack.get("footballdata_stats", {})
    odds = market.get("odds") if market.get("available") else None
    fd_ours = (fd.get("motherwell") or {}) if fd.get("available") else {}
    fd_theirs = (fd.get("opponent") or {}) if fd.get("available") else {}
    home = match["home_away"] == "home"
    return {
        "espn_id": match["espn_id"],
        "date": match["date"],
        "kickoff_utc": match["kickoff_utc"],
        "season": pack.get("season"),
        "competition_code": match["competition"]["code"],
        "competition": match["competition"]["name"],
        "home_away": match["home_away"],
        "opponent": match["opponent"]["name"],
        "opponent_slug": match["opponent"]["slug"],
        "result": match["result"],
        "points": POINTS[match["result"]],
        "motherwell_goals": match["score"]["motherwell"],
        "opponent_goals": match["score"]["opponent"],
        "ht_motherwell": fd_ours.get("ht_goals"),
        "ht_opponent": fd_theirs.get("ht_goals"),
        "venue": match.get("venue"),
        "attendance": match.get("attendance"),
        "referee": match.get("referee"),
        "motherwell_xg": xg.get("motherwell") if xg.get("available") else None,
        "opponent_xg": xg.get("opponent") if xg.get("available") else None,
        "motherwell_shots": ours.get("shots"),
        "opponent_shots": theirs.get("shots"),
        "motherwell_sot": ours.get("shots_on_target"),
        "opponent_sot": theirs.get("shots_on_target"),
        "motherwell_possession": ours.get("possession_pct"),
        "motherwell_corners": ours.get("corners"),
        "opponent_corners": theirs.get("corners"),
        "motherwell_yellows": ours.get("yellow_cards"),
        "motherwell_reds": ours.get("red_cards"),
        "opponent_yellows": theirs.get("yellow_cards"),
        "opponent_reds": theirs.get("red_cards"),
        "odds_motherwell": (odds["home"] if home else odds["away"]) if odds else None,
        "odds_draw": odds["draw"] if odds else None,
        "odds_opponent": (odds["away"] if home else odds["home"]) if odds else None,
        "statpack": pack.get("_path", ""),
    }


def load_matchlog(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=MATCHLOG_COLUMNS)
    frame = pd.read_csv(path, dtype={"espn_id": str})
    for col in MATCHLOG_COLUMNS:
        if col not in frame.columns:
            frame[col] = None
    return frame[MATCHLOG_COLUMNS]


def upsert_matchlog(path: Path, rows: list[dict], *, write: bool = True) -> pd.DataFrame:
    """Merge rows into the log by espn_id (new rows win), sort, optionally write."""
    existing = load_matchlog(path)
    incoming = pd.DataFrame(rows, columns=MATCHLOG_COLUMNS)
    incoming["espn_id"] = incoming["espn_id"].astype(str)
    keep = existing[~existing["espn_id"].astype(str).isin(set(incoming["espn_id"]))]
    merged = pd.concat([keep, incoming], ignore_index=True)
    merged = merged.sort_values(["kickoff_utc", "espn_id"]).reset_index(drop=True)
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(path, index=False)
    return merged
