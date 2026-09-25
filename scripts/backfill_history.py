#!/usr/bin/env python3
"""Seed the playground with football-data.co.uk history.

Downloads one Scottish Premiership season CSV per season code, keeps the
compact column set, and writes:

  data/processed/spfl/league_{season}.csv      every match in the league
  data/processed/motherwell/history_matches.csv Motherwell's matches, Motherwell-relative

Idempotent: past seasons are cached under data/raw/ and never re-fetched;
pass --force to refresh the current season.

Usage:
    python scripts/backfill_history.py --seasons 2122,2223,2324,2425,2526,2627
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

from steelmen.clean.footballdata import normalise
from steelmen.io.footballdata import get_season_csv
from steelmen.utils.teams import MOTHERWELL_FD_NAME

DEFAULT_SEASONS = "2122,2223,2324,2425,2526,2627"


def season_label_from_code(code: str) -> str:
    return f"20{code[:2]}-{code[2:]}"


def motherwell_relative(frame: pd.DataFrame, season: str) -> pd.DataFrame:
    """Reshape league rows into Motherwell-relative rows (home/away, result, xG)."""
    involved = (frame["HomeTeam"] == MOTHERWELL_FD_NAME) | (
        frame["AwayTeam"] == MOTHERWELL_FD_NAME
    )
    ours = frame[involved]
    rows = []
    for r in ours.itertuples(index=False):
        home = r.HomeTeam == MOTHERWELL_FD_NAME
        gf, ga = (r.FTHG, r.FTAG) if home else (r.FTAG, r.FTHG)
        result = "W" if gf > ga else "L" if gf < ga else "D"

        def pick(h, a):
            return (h, a) if home else (a, h)

        xg_for, xg_against = pick(getattr(r, "HxG", None), getattr(r, "AxG", None))
        shots_for, shots_against = pick(r.HS, r.AS)
        sot_for, sot_against = pick(r.HST, r.AST)
        corners_for, corners_against = pick(r.HC, r.AC)
        yellows, opp_yellows = pick(r.HY, r.AY)
        reds, opp_reds = pick(r.HR, r.AR)
        odds_for, odds_against = pick(r.B365H, r.B365A)
        rows.append(
            {
                "season": season,
                "date": r.date,
                "home_away": "home" if home else "away",
                "opponent": r.AwayTeam if home else r.HomeTeam,
                "result": result,
                "points": {"W": 3, "D": 1, "L": 0}[result],
                "motherwell_goals": gf,
                "opponent_goals": ga,
                "ht_motherwell": r.HTHG if home else r.HTAG,
                "ht_opponent": r.HTAG if home else r.HTHG,
                "referee": r.Referee,
                "motherwell_xg": xg_for,
                "opponent_xg": xg_against,
                "motherwell_shots": shots_for,
                "opponent_shots": shots_against,
                "motherwell_sot": sot_for,
                "opponent_sot": sot_against,
                "motherwell_corners": corners_for,
                "opponent_corners": corners_against,
                "motherwell_yellows": yellows,
                "motherwell_reds": reds,
                "opponent_yellows": opp_yellows,
                "opponent_reds": opp_reds,
                "odds_motherwell": odds_for,
                "odds_draw": r.B365D,
                "odds_opponent": odds_against,
            }
        )
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", default=DEFAULT_SEASONS, help="Comma-separated season codes")
    parser.add_argument("--force", action="store_true", help="Re-fetch every season")
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    args = parser.parse_args(argv)

    history = []
    for code in [c.strip() for c in args.seasons.split(",") if c.strip()]:
        season = season_label_from_code(code)
        frame = normalise(get_season_csv(code, cache_dir=args.data_root / "raw", force=args.force))
        out = args.data_root / "processed" / "spfl" / f"league_{season}.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(out, index=False)
        ours = motherwell_relative(frame, season)
        history.append(ours)
        print(f"RESULT: {season} {len(frame)} league matches, {len(ours)} Motherwell")
    combined = pd.concat(history, ignore_index=True).sort_values("date").reset_index(drop=True)
    out = args.data_root / "processed" / "motherwell" / "history_matches.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(out, index=False)
    print(f"RESULT: history {len(combined)} Motherwell league matches -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
