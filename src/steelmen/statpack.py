"""Stat pack assembly — the contract between the nightly pull and the
morning narrative.

One compact JSON per match (target <= 30 KB) committed to
data/processed/motherwell/statpacks/. The report Routines consume packs
and the match log and nothing else, so validate_stat_pack is the drift
alarm for the whole handoff.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from steelmen.clean.footballdata import market_block, stats_block, xg_block
from steelmen.clean.match import (
    parse_events,
    parse_lineups,
    parse_match_summary,
    parse_player_lines,
    parse_standings,
    parse_team_stats,
)
from steelmen.io.espn import PREMIERSHIP
from steelmen.metrics.form import last_n_summary, season_summary, through_match
from steelmen.metrics.xg import xpoints
from steelmen.utils.time import season_label

STAT_PACK_VERSION = 1

_REQUIRED_KEYS = {
    "schema_version",
    "generated_at",
    "sources",
    "season",
    "match",
    "lineups",
    "events",
    "team_stats",
    "player_lines",
    "xg",
    "market",
    "footballdata_stats",
    "rolling",
    "table",
    "figure",
    "notes",
}

COMPETITION_SLUGS = {
    "sco.1": "",
    "sco.cis": "league-cup",
    "sco.tennents": "scottish-cup",
    "sco.tennents_qual": "scottish-cup-qual",
    "uefa.europa.conf_qual": "uecl-qual",
    "uefa.europa_qual": "uel-qual",
    "uefa.europa.conf": "uecl",
    "uefa.europa": "uel",
    "club.friendly": "friendly",
}


class StatPackError(RuntimeError):
    """A stat pack failed validation — do not commit it."""


def _stem(pack: dict) -> str:
    match = pack["match"]
    prefix = "vs" if match["home_away"] == "home" else "at"
    stem = f"{match['date']}_{prefix}-{match['opponent']['slug']}"
    suffix = COMPETITION_SLUGS.get(match["competition"]["code"], match["competition"]["code"])
    return f"{stem}_{suffix}" if suffix else stem


def report_filename(pack: dict) -> str:
    """Deterministic report filename shared by both pipeline stages:
    {date}_{vs|at}-{opponent-slug}[_{competition}].md"""
    return _stem(pack) + ".md"


def figure_filename(pack: dict) -> str:
    return _stem(pack) + ".png"


def stat_pack_path(root: Path, date: str, espn_id: str | int) -> Path:
    """data/processed/motherwell/statpacks/{date}_{espn_id}.json under the data root."""
    return root / "processed" / "motherwell" / "statpacks" / f"{date}_{espn_id}.json"


def build_stat_pack(
    *,
    summary: dict,
    league: str,
    matchlog: pd.DataFrame,
    footballdata_row: pd.Series | None = None,
    xg_source: str = "football-data.co.uk",
    generated_at: datetime | None = None,
) -> dict:
    """Assemble a stat pack from an ESPN summary plus optional football-data row.

    matchlog must include this match's row (the caller upserts a provisional
    row first). It may extend past it — the rolling block is trimmed to this
    match so the numbers describe the match being written up.
    """
    match = parse_match_summary(summary, league)
    home = match["home_away"] == "home"
    if league != PREMIERSHIP:
        footballdata_row = None  # football-data.co.uk covers league matches only
    lineups = parse_lineups(summary)
    events = parse_events(summary)
    team_stats = parse_team_stats(summary)
    player_lines = {
        "motherwell": parse_player_lines(lineups, "motherwell"),
        "opponent": parse_player_lines(lineups, "opponent") if "opponent" in lineups else None,
    }
    xg = xg_block(footballdata_row, home, source=xg_source)
    if xg["available"]:
        xg["xpoints"] = round(xpoints(xg["motherwell"], xg["opponent"]), 2)
    market = market_block(footballdata_row, home, match["result"])
    fd_stats = stats_block(footballdata_row, home)
    table = parse_standings(summary) if league == PREMIERSHIP else None
    if table is not None:
        # ESPN attaches the table as it stood when the summary was fetched (the
        # morning after, for nightly runs; earlier than generated_at on rebuilds)
        table["as_of"] = "when the ESPN summary was fetched, not full time"

    log = through_match(matchlog, espn_id=match["espn_id"])
    if xg["available"]:
        # the caller's provisional row predates the xG lookup; patch it so this
        # match's own xG counts in the rolling blocks
        last = log.index[-1]
        log.loc[last, "motherwell_xg"] = xg["motherwell"]
        log.loc[last, "opponent_xg"] = xg["opponent"]
    rolling = {
        "last5_all": last_n_summary(log, 5),
        "last5_league": last_n_summary(log, 5, competition=PREMIERSHIP),
        "season_all": season_summary(log),
        "season_league": season_summary(log, competition=PREMIERSHIP),
    }

    notes = []
    if not team_stats["available"]:
        notes.append("ESPN box score empty for this match: team stats unavailable")
    if not xg["available"]:
        reason = (
            "non-league match" if league != PREMIERSHIP else "football-data row not yet published"
        )
        notes.append(f"xG unavailable: {reason}")
    if table is None:
        notes.append("no league table attached (non-league match)")

    when = generated_at or datetime.now(timezone.utc)
    pack = {
        "schema_version": STAT_PACK_VERSION,
        "generated_at": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": {
            "espn_summary": True,
            "footballdata_row": footballdata_row is not None,
            "footballdata_xg": xg["available"],
            "footballdata_market": market["available"],
        },
        "season": season_label(match["date"]),
        "match": match,
        "lineups": lineups,
        "events": events,
        "team_stats": team_stats,
        "player_lines": player_lines,
        "xg": xg,
        "market": market,
        "footballdata_stats": fd_stats,
        "rolling": rolling,
        "table": table,
        "figure": f"reports/motherwell/figures/{figure_filename({'match': match})}",
        "notes": notes,
    }
    return pack


def validate_stat_pack(pack: dict) -> None:
    """Raise StatPackError if the pack is structurally unsound."""
    missing = _REQUIRED_KEYS - set(pack)
    if missing:
        raise StatPackError(f"Stat pack missing keys: {sorted(missing)}")
    if pack["schema_version"] != STAT_PACK_VERSION:
        raise StatPackError(
            f"Stat pack schema_version {pack['schema_version']} != {STAT_PACK_VERSION}"
        )
    match = pack["match"]
    for key in (
        "espn_id",
        "date",
        "result",
        "score",
        "opponent",
        "competition",
        "home_away",
        "decided_by",
    ):
        if key not in match:
            raise StatPackError(f"Stat pack match section missing '{key}'")
    if match["result"] not in ("W", "D", "L"):
        raise StatPackError(f"Invalid result: {match['result']}")
    if match["home_away"] not in ("home", "away"):
        raise StatPackError(f"Invalid home_away: {match['home_away']}")
    if match["decided_by"] not in ("ft", "aet", "pens", "aggregate"):
        raise StatPackError(f"Invalid decided_by: {match['decided_by']}")
    if not isinstance(pack["xg"].get("available"), bool):
        raise StatPackError("xg.available must be a bool")
    if not isinstance(pack["market"].get("available"), bool):
        raise StatPackError("market.available must be a bool")
    if "motherwell" not in pack["lineups"]:
        raise StatPackError("lineups.motherwell missing")
    if not isinstance(pack["team_stats"].get("available"), bool):
        raise StatPackError("team_stats.available must be a bool")


def write_stat_pack(pack: dict, root: Path) -> Path:
    validate_stat_pack(pack)
    path = stat_pack_path(root, pack["match"]["date"], pack["match"]["espn_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {k: v for k, v in pack.items() if not k.startswith("_")}
    path.write_text(json.dumps(body, indent=1, sort_keys=True) + "\n")
    return path
