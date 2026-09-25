"""Corners and cards over the match log — the set-piece / discipline themes."""

import pandas as pd


def discipline_summary(log: pd.DataFrame) -> dict:
    if log.empty:
        return {"games": 0}
    num = {
        c: pd.to_numeric(log[c], errors="coerce")
        for c in (
            "motherwell_corners",
            "opponent_corners",
            "motherwell_yellows",
            "motherwell_reds",
            "opponent_yellows",
            "opponent_reds",
        )
    }
    games = int(num["motherwell_corners"].notna().sum())
    return {
        "games": games,
        "corners_for": int(num["motherwell_corners"].fillna(0).sum()),
        "corners_against": int(num["opponent_corners"].fillna(0).sum()),
        "corners_for_pg": round(num["motherwell_corners"].mean(), 2) if games else None,
        "corners_against_pg": round(num["opponent_corners"].mean(), 2) if games else None,
        "yellows": int(num["motherwell_yellows"].fillna(0).sum()),
        "reds": int(num["motherwell_reds"].fillna(0).sum()),
        "opponent_yellows": int(num["opponent_yellows"].fillna(0).sum()),
        "opponent_reds": int(num["opponent_reds"].fillna(0).sum()),
    }
