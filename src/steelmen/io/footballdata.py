"""football-data.co.uk season CSVs (Scottish Premiership = SC0).

Free for personal use, one CSV per season, refreshed after each round of
fixtures. From 2026-27 the file carries team xG (HxG/AxG) alongside shots,
corners, cards and closing odds. League matches only — nothing for cups.
"""

from io import StringIO
from pathlib import Path

import pandas as pd

from steelmen.io.cache import DATA_RAW, cached_get_text

BASE = "https://www.football-data.co.uk/mmz4281"
DIVISION = "SC0"

# The subset we keep: results, xG, match stats and the Bet365 / market-average odds.
KEEP_COLUMNS = [
    "Div", "Date", "Time", "HomeTeam", "AwayTeam",
    "FTHG", "FTAG", "FTR", "HTHG", "HTAG", "HTR", "Referee",
    "HxG", "AxG",
    "HS", "AS", "HST", "AST", "HF", "AF", "HC", "AC", "HY", "AY", "HR", "AR",
    "B365H", "B365D", "B365A", "AvgH", "AvgD", "AvgA", "Avg>2.5", "Avg<2.5",
]  # fmt: skip


def season_url(season_code: str, division: str = DIVISION) -> str:
    return f"{BASE}/{season_code}/{division}.csv"


def get_season_csv(
    season_code: str,
    *,
    cache_dir: Path = DATA_RAW,
    force: bool = False,
    stamp: str | None = None,
    division: str = DIVISION,
) -> pd.DataFrame:
    """The raw season file as a frame, restricted to KEEP_COLUMNS where present.

    stamp: cache-buster for the in-progress season (e.g. today's date), so
    the nightly run sees this week's rows while past seasons stay cached.
    """
    suffix = f"_{stamp}" if stamp else ""
    text = cached_get_text(
        season_url(season_code, division),
        cache_path=cache_dir / "footballdata" / f"{division}_{season_code}{suffix}.csv",
        force=force,
    )
    frame = pd.read_csv(StringIO(text.lstrip("﻿")))
    columns = [c for c in KEEP_COLUMNS if c in frame.columns]
    return frame[columns].dropna(subset=["Date", "HomeTeam"])
