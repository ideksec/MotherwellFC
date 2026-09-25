"""Pluggable xG providers.

The free stack gets team xG from football-data.co.uk (league matches only).
A paid feed (Sportmonks, API-Football, ...) can be added as another class
implementing XGProvider without touching stat packs or the Routine prompts:
the pack's `xg` block only ever carries what `match_xg` returns plus a
`source` label.
"""

from typing import Protocol

import pandas as pd

from steelmen.clean.footballdata import find_match, normalise


class XGProvider(Protocol):
    name: str

    def match_xg(self, date: str, home: str, away: str) -> dict | None:
        """Team xG for a match (ISO date, home/away names in the provider's
        vocabulary). None when the provider has nothing for this match."""


class FootballDataXG:
    """xG from a football-data.co.uk season frame."""

    name = "football-data.co.uk"

    def __init__(self, season_frame: pd.DataFrame):
        self.frame = normalise(season_frame)

    def match_xg(self, date: str, home: str, away: str) -> dict | None:
        row = find_match(self.frame, date, home, away)
        if row is None or pd.isna(row.get("HxG")) or pd.isna(row.get("AxG")):
            return None
        return {"home": float(row["HxG"]), "away": float(row["AxG"]), "shots": None}
