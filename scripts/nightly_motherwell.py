#!/usr/bin/env python3
"""Nightly Motherwell stat-pack builder (Stage 1 of the match pipeline).

Default mode scans the last --days-back UK dates across every competition
in steelmen.io.espn.LEAGUES for finished Motherwell matches and builds a
stat pack, match-log row and match figure for each one that doesn't have
one yet (idempotent; --force rebuilds). It also refreshes the fixtures
list and the league table. Designed for a GitHub Actions cron at ~03:00
UTC, after midweek matches end.

Prints machine-greppable "RESULT: ..." lines the workflow folds into its
commit message. No-op runs leave the tree untouched, so the workflow's
commit step naturally skips them.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from steelmen.clean.footballdata import find_match, normalise
from steelmen.clean.match import parse_match_summary, parse_standings
from steelmen.clean.matchlog import load_matchlog, matchlog_row, upsert_matchlog
from steelmen.io.cache import FetchError
from steelmen.io.espn import (
    LEAGUES,
    PREMIERSHIP,
    final_events,
    get_scoreboard,
    get_summary,
    get_team_schedule,
    is_final,
)
from steelmen.io.footballdata import get_season_csv
from steelmen.io.thesportsdb import next_events
from steelmen.statpack import (
    build_stat_pack,
    figure_filename,
    stat_pack_path,
    write_stat_pack,
)
from steelmen.utils.teams import MOTHERWELL_ESPN_ID, MOTHERWELL_FD_NAME, footballdata_name
from steelmen.utils.time import UK, season_code, season_label, uk_date
from steelmen.viz.match import match_figure

XG_RETRY_DAYS = 4  # football-data.co.uk usually posts within a day or two
FIGURES_DIR = Path("reports/motherwell/figures")


def matchlog_path(root: Path, date: str) -> Path:
    return root / "processed" / "motherwell" / f"matchlog_{season_label(date)}.csv"


def fixtures_path(root: Path) -> Path:
    return root / "processed" / "motherwell" / "fixtures.csv"


def table_path(root: Path) -> Path:
    return root / "processed" / "motherwell" / "table.csv"


def recent_uk_dates(days_back: int, *, today: datetime | None = None) -> list[str]:
    """Yesterday backwards in UK time, plus today (a 3pm kickoff is done by 03:00 next day,
    but a run triggered by hand late in the evening should still see today's match)."""
    now = today or datetime.now(UK)
    base = now.date()
    return [(base - timedelta(days=offset)).isoformat() for offset in range(0, days_back + 1)]


def needs_xg_retry(pack_path: Path, date: str, *, today: datetime | None = None) -> bool:
    """An existing league pack without xG gets rebuilt while the match is fresh."""
    pack = json.loads(pack_path.read_text())
    if pack.get("xg", {}).get("available"):
        return False
    if pack.get("match", {}).get("competition", {}).get("code") != PREMIERSHIP:
        return False
    match_date = datetime.strptime(date, "%Y-%m-%d").date()
    now = today or datetime.now(UK)
    return (now.date() - match_date).days <= XG_RETRY_DAYS


def footballdata_row(match: dict, *, root: Path, stamp: str) -> pd.Series | None:
    """The football-data.co.uk row for a league match, or None (cups, not yet posted)."""
    if match["competition"]["code"] != PREMIERSHIP:
        return None
    try:
        frame = normalise(
            get_season_csv(season_code(match["date"]), cache_dir=root / "raw", stamp=stamp)
        )
    except FetchError as err:
        print(f"WARN: football-data.co.uk unavailable: {err}", file=sys.stderr)
        return None
    opponent = footballdata_name(match["opponent"]["espn_id"], match["opponent"]["name"])
    home, away = (
        (MOTHERWELL_FD_NAME, opponent)
        if match["home_away"] == "home"
        else (opponent, MOTHERWELL_FD_NAME)
    )
    return find_match(frame, match["date"], home, away)


def process_event(
    event: dict, league: str, *, root: Path, force: bool, dry_run: bool, stamp: str
) -> str:
    event_id = str(event["id"])
    date = uk_date(event["date"])
    pack_path = stat_pack_path(root, date, event_id)
    if pack_path.exists() and not force and not needs_xg_retry(pack_path, date):
        return f"RESULT: exists {date} {league} event {event_id}"

    summary = get_summary(league, event_id, cache_dir=root / "raw", force=force)
    match = parse_match_summary(summary, league)
    fd_row = footballdata_row(match, root=root, stamp=stamp)

    log_path = matchlog_path(root, match["date"])
    provisional = {
        "match": match,
        "team_stats": {},
        "xg": {"available": False},
        "market": {"available": False},
        "footballdata_stats": {"available": False},
        "season": season_label(match["date"]),
    }
    log = upsert_matchlog(log_path, [matchlog_row(provisional)], write=False)
    pack = build_stat_pack(summary=summary, league=league, matchlog=log, footballdata_row=fd_row)
    pack["_path"] = str(pack_path)
    if dry_run:
        print(json.dumps({k: v for k, v in pack.items() if k != "lineups"}, indent=1))
        return f"RESULT: dry-run {date} {league} event {event_id}"

    write_stat_pack(pack, root)
    log = upsert_matchlog(log_path, [matchlog_row(pack)], write=True)
    figure_path = FIGURES_DIR / figure_filename(pack)
    match_figure(pack, log, figure_path)
    score = match["score"]
    xg_note = "with xG" if pack["xg"]["available"] else "NO xG"
    return (
        f"RESULT: wrote {date} {league} event {event_id} {match['result']} "
        f"{score['motherwell']}-{score['opponent']} {match['home_away']} vs "
        f"{match['opponent']['name']} ({xg_note})"
    )


def process_date(
    date: str, *, root: Path, force: bool, dry_run: bool, stamp: str, leagues: list[str]
) -> list[str]:
    results = []
    seen: set[str] = set()
    for league in leagues:
        try:
            scoreboard = get_scoreboard(league, date, cache_dir=root / "raw", force=force)
        except FetchError as err:
            results.append(f"RESULT: fetch-error {date} {league}: {err}")
            continue
        for event in final_events(scoreboard):
            if str(event["id"]) in seen:
                continue
            seen.add(str(event["id"]))
            results.append(
                process_event(event, league, root=root, force=force, dry_run=dry_run, stamp=stamp)
            )
    if not results:
        results.append(f"RESULT: no-match {date}")
    return results


def refresh_fixtures(*, root: Path, force: bool, dry_run: bool, stamp: str) -> str:
    """Upcoming fixtures from ESPN's team schedule (league) and TheSportsDB (all comps)."""
    rows: dict[str, dict] = {}
    try:
        schedule = get_team_schedule(
            PREMIERSHIP, MOTHERWELL_ESPN_ID, cache_dir=root / "raw", force=True
        )
        for event in schedule.get("events", []):
            if is_final(event):
                continue
            comp = event["competitions"][0]
            ours = next(
                c for c in comp["competitors"] if str(c["team"]["id"]) == MOTHERWELL_ESPN_ID
            )
            theirs = next(
                c for c in comp["competitors"] if str(c["team"]["id"]) != MOTHERWELL_ESPN_ID
            )
            rows[f"espn:{event['id']}"] = {
                "date": uk_date(event["date"]),
                "kickoff_utc": event["date"],
                "competition": (event.get("league") or {}).get("name") or LEAGUES[PREMIERSHIP],
                "competition_code": PREMIERSHIP,
                "home_away": ours.get("homeAway"),
                "opponent": theirs["team"]["displayName"],
                "opponent_espn_id": str(theirs["team"]["id"]),
                "venue": ((comp.get("venue") or {}).get("fullName")),
                "source": "espn",
            }
    except (FetchError, KeyError, StopIteration) as err:
        print(f"WARN: ESPN schedule unavailable: {err}", file=sys.stderr)
    try:
        for event in next_events(cache_dir=root / "raw", force=force, stamp=stamp):
            home = event.get("strHomeTeam") == "Motherwell"
            key = f"tsdb:{event.get('idEvent')}"
            date = (event.get("dateEvent") or "")[:10]
            if any(r["date"] == date for r in rows.values()):
                continue
            rows[key] = {
                "date": date,
                "kickoff_utc": (event.get("strTimestamp") or "").replace(" ", "T") + "Z",
                "competition": event.get("strLeague"),
                "competition_code": None,
                "home_away": "home" if home else "away",
                "opponent": event.get("strAwayTeam") if home else event.get("strHomeTeam"),
                "opponent_espn_id": None,
                "venue": event.get("strVenue"),
                "source": "thesportsdb",
            }
    except FetchError as err:
        print(f"WARN: TheSportsDB unavailable: {err}", file=sys.stderr)
    if not rows:
        return "RESULT: fixtures unavailable"
    frame = pd.DataFrame(list(rows.values())).sort_values("date").reset_index(drop=True)
    if not dry_run:
        path = fixtures_path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
    return f"RESULT: fixtures {len(frame)} upcoming (next {frame.iloc[0]['date']})"


def refresh_table(*, root: Path, dry_run: bool, latest_summary: dict | None) -> str:
    """League table from the most recent league summary's standings block."""
    if latest_summary is None:
        return "RESULT: table unchanged (no league summary this run)"
    standings = parse_standings(latest_summary)
    if not standings:
        return "RESULT: table unavailable"
    frame = pd.DataFrame(standings["table"])
    if not dry_run:
        frame.to_csv(table_path(root), index=False)
    ours = standings["motherwell"]
    return f"RESULT: table updated (Motherwell {ours['rank']}th, {ours['points']} pts)"


def latest_league_summary(root: Path) -> dict | None:
    """The cached summary of the newest league match in the log, for the table."""
    logs = sorted((root / "processed" / "motherwell").glob("matchlog_*.csv"))
    if not logs:
        return None
    log = load_matchlog(logs[-1])
    league = log[log["competition_code"] == PREMIERSHIP]
    if league.empty:
        return None
    newest = league.sort_values("kickoff_utc").iloc[-1]
    cached = root / "raw" / "espn" / "summary" / f"{PREMIERSHIP}_{newest['espn_id']}.json"
    if not cached.exists():
        return None
    return json.loads(cached.read_text())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Process one UK date (YYYY-MM-DD) instead of the lookback")
    parser.add_argument("--days-back", type=int, default=3, help="Lookback window (default 3)")
    parser.add_argument("--force", action="store_true", help="Rebuild even if packs exist")
    parser.add_argument("--dry-run", action="store_true", help="Print packs, write nothing")
    parser.add_argument("--skip-fixtures", action="store_true", help="Don't refresh fixtures")
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument(
        "--leagues", default=",".join(LEAGUES), help="Comma-separated ESPN league codes"
    )
    args = parser.parse_args(argv)

    stamp = datetime.now(UK).date().isoformat()
    leagues = [code.strip() for code in args.leagues.split(",") if code.strip()]
    dates = [args.date] if args.date else recent_uk_dates(args.days_back)
    results: list[str] = []
    for date in sorted(dates):  # oldest first, so rolling numbers build up in order
        results.extend(
            process_date(
                date,
                root=args.data_root,
                force=args.force,
                dry_run=args.dry_run,
                stamp=stamp,
                leagues=leagues,
            )
        )
    if not args.skip_fixtures:
        results.append(
            refresh_fixtures(
                root=args.data_root, force=args.force, dry_run=args.dry_run, stamp=stamp
            )
        )
    results.append(
        refresh_table(
            root=args.data_root,
            dry_run=args.dry_run,
            latest_summary=latest_league_summary(args.data_root),
        )
    )
    for line in results:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
