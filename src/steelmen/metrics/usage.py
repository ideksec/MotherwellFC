"""Squad usage across stat packs: appearances, starts, estimated minutes,
goals, assists, shots. Minutes come from lineups.*.minutes_est, so they are
estimates (no stoppage time) and are labelled as such downstream."""

import json
from pathlib import Path

import pandas as pd

USAGE_COLUMNS = [
    "name", "apps", "starts", "sub_apps", "minutes_est", "goals", "assists",
    "shots", "shots_on_target", "yellow_cards", "red_cards", "shots_per90",
]  # fmt: skip


def load_packs(statpack_dir: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(statpack_dir.glob("*.json"))]


def player_match_rows(packs: list[dict], side: str = "motherwell") -> pd.DataFrame:
    """One row per player per match they played (started or came on)."""
    rows = []
    for pack in packs:
        match = pack["match"]
        lineup = pack["lineups"][side]
        for entry in lineup["starters"] + lineup["bench"]:
            if not (entry["starter"] or entry["subbed_in"]):
                continue
            rows.append(
                {
                    "espn_id": match["espn_id"],
                    "date": match["date"],
                    "competition_code": match["competition"]["code"],
                    "opponent": match["opponent"]["name"],
                    "name": entry["name"],
                    "position": entry["position"],
                    "starter": bool(entry["starter"]),
                    "minutes_est": entry["minutes_est"] or 0,
                    "goals": entry.get("goals", 0) or 0,
                    "assists": entry.get("assists", 0) or 0,
                    "shots": entry.get("shots", 0) or 0,
                    "shots_on_target": entry.get("shots_on_target", 0) or 0,
                    "yellow_cards": entry.get("yellow_cards", 0) or 0,
                    "red_cards": entry.get("red_cards", 0) or 0,
                }
            )
    return pd.DataFrame(rows)


def squad_usage(
    packs: list[dict], *, side: str = "motherwell", competition: str | None = None
) -> pd.DataFrame:
    """Per-player totals, sorted by estimated minutes. Empty frame when no packs."""
    rows = player_match_rows(packs, side)
    if rows.empty:
        return pd.DataFrame(columns=USAGE_COLUMNS)
    if competition:
        rows = rows[rows["competition_code"] == competition]
    grouped = rows.groupby("name").agg(
        apps=("espn_id", "nunique"),
        starts=("starter", "sum"),
        minutes_est=("minutes_est", "sum"),
        goals=("goals", "sum"),
        assists=("assists", "sum"),
        shots=("shots", "sum"),
        shots_on_target=("shots_on_target", "sum"),
        yellow_cards=("yellow_cards", "sum"),
        red_cards=("red_cards", "sum"),
    )
    grouped["sub_apps"] = grouped["apps"] - grouped["starts"]
    minutes = grouped["minutes_est"].astype(float).replace(0.0, float("nan"))
    grouped["shots_per90"] = (grouped["shots"] / minutes * 90).round(2)

    out = grouped.reset_index().sort_values(["minutes_est", "name"], ascending=[False, True])
    return out[USAGE_COLUMNS].reset_index(drop=True)
