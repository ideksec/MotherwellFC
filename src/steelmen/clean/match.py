"""ESPN match summary -> the building blocks of a stat pack.

Everything here is Motherwell-relative: `home_away`, `result`, `score`
and the lineups/events are labelled `motherwell` / `opponent`. The API is
undocumented, so `_require` validates the field paths we depend on and
raises ParseError rather than guessing.
"""

import math
import re
from typing import Any

from steelmen.io.espn import LEAGUES
from steelmen.utils.teams import MOTHERWELL_ESPN_ID, team_slug
from steelmen.utils.time import parse_espn_datetime, uk_date

TEAM_STAT_KEYS = {
    "possessionPct": "possession_pct",
    "totalShots": "shots",
    "shotsOnTarget": "shots_on_target",
    "blockedShots": "shots_blocked",  # this team's own shots that were blocked
    "wonCorners": "corners",
    "foulsCommitted": "fouls",
    "yellowCards": "yellow_cards",
    "redCards": "red_cards",
    "offsides": "offsides",
    "saves": "saves",
    "totalPasses": "passes",
    "accuratePasses": "passes_accurate",
    "passPct": "pass_pct",
    "totalTackles": "tackles",
    "effectiveTackles": "tackles_won",
    "interceptions": "interceptions",
    "totalClearance": "clearances",
}

PLAYER_STAT_KEYS = {
    "totalGoals": "goals",
    "goalAssists": "assists",
    "totalShots": "shots",
    "shotsOnTarget": "shots_on_target",
    "yellowCards": "yellow_cards",
    "redCards": "red_cards",
    "foulsCommitted": "fouls",
    "foulsSuffered": "fouled",
    "saves": "saves",
    "goalsConceded": "goals_conceded",
    "ownGoals": "own_goals",
}

EVENT_KINDS = {
    "goal": "goal",
    "own-goal": "own_goal",
    "penalty---scored": "penalty_goal",
    "penalty-scored": "penalty_goal",
    "penalty---missed": "penalty_missed",
    "penalty-missed": "penalty_missed",
    "penalty---saved": "penalty_saved",
    "yellow-card": "yellow_card",
    "red-card": "red_card",
    "yellow-red-card": "second_yellow",
    "substitution": "substitution",
    "var": "var",
}


class ParseError(RuntimeError):
    """An expected field is missing or malformed — the ESPN payload drifted."""


def _require(mapping: Any, path: str) -> Any:
    node = mapping
    for key in path.split("."):
        if isinstance(node, list):
            try:
                node = node[int(key)]
            except (ValueError, IndexError) as err:
                raise ParseError(f"Missing '{path}' at '{key}'") from err
        elif isinstance(node, dict) and key in node:
            node = node[key]
        else:
            raise ParseError(f"Missing '{path}' at '{key}'")
    return node


def _number(value: Any) -> float | int | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def _competitors(summary: dict) -> tuple[dict, dict]:
    """(motherwell competitor, opponent competitor) from the header."""
    competitors = _require(summary, "header.competitions.0.competitors")
    ours = [c for c in competitors if str(_require(c, "team.id")) == MOTHERWELL_ESPN_ID]
    theirs = [c for c in competitors if str(_require(c, "team.id")) != MOTHERWELL_ESPN_ID]
    if len(ours) != 1 or len(theirs) != 1:
        raise ParseError("Summary does not involve exactly one Motherwell side")
    return ours[0], theirs[0]


def parse_match_summary(summary: dict, league: str) -> dict:
    ours, theirs = _competitors(summary)
    kickoff = parse_espn_datetime(_require(summary, "header.competitions.0.date"))
    status = _require(summary, "header.competitions.0.status.type")
    our_goals = int(_require(ours, "score"))
    their_goals = int(_require(theirs, "score"))
    result = "W" if our_goals > their_goals else "L" if our_goals < their_goals else "D"
    game_info = summary.get("gameInfo", {})
    officials = game_info.get("officials") or []
    referee = next(
        (
            o.get("displayName")
            for o in officials
            if (o.get("position") or {}).get("name", "Referee") == "Referee"
        ),
        None,
    )
    opponent_id = str(_require(theirs, "team.id"))
    opponent_name = _require(theirs, "team.displayName")
    return {
        "espn_id": str(_require(summary, "header.id")),
        "date": uk_date(kickoff),
        "kickoff_utc": kickoff.strftime("%Y-%m-%dT%H:%MZ"),
        "competition": {"code": league, "name": LEAGUES.get(league, league)},
        "season": (summary.get("header", {}).get("season") or {}).get("name"),
        "status": status.get("name"),
        "home_away": "home" if ours.get("homeAway") == "home" else "away",
        "neutral_site": bool(summary["header"]["competitions"][0].get("neutralSite")),
        "opponent": {
            "espn_id": opponent_id,
            "name": opponent_name,
            "slug": team_slug(opponent_id, opponent_name),
            "abbrev": theirs["team"].get("abbreviation"),
        },
        "result": result,
        "score": {"motherwell": our_goals, "opponent": their_goals},
        "venue": (game_info.get("venue") or {}).get("fullName"),
        "city": ((game_info.get("venue") or {}).get("address") or {}).get("city"),
        "attendance": game_info.get("attendance") or None,  # ESPN writes 0 when unknown
        "referee": referee,
    }


def _side(team_id: str) -> str:
    return "motherwell" if str(team_id) == MOTHERWELL_ESPN_ID else "opponent"


def _minute(clock: dict | None) -> tuple[int | None, str | None]:
    """(numeric minute, display like "45'+2'") from an ESPN clock block."""
    if not clock:
        return None, None
    display = clock.get("displayValue")
    value = clock.get("value")
    if display:
        # "90'+3'" -> 93: ESPN's numeric clock stops at 45:00 / 90:00 in stoppage time
        stoppage = re.match(r"(\d+)'\+(\d+)'", display)
        if stoppage:
            return int(stoppage.group(1)) + int(stoppage.group(2)), display
    if value is not None:
        return int(math.ceil(float(value) / 60)), display
    if display:
        match = re.match(r"(\d+)", display)
        if match:
            return int(match.group(1)), display
    return None, display


def parse_events(summary: dict) -> list[dict]:
    """Goals, cards, subs and VAR calls in match order, Motherwell-labelled."""
    events = []
    for raw in summary.get("keyEvents") or []:
        kind_raw = (raw.get("type") or {}).get("type", "")
        kind = EVENT_KINDS.get(kind_raw, kind_raw or "other")
        text = (raw.get("type") or {}).get("text", "")
        if kind == "goal" and "own" in text.lower():
            kind = "own_goal"
        if kind == "goal" and "penalty" in text.lower():
            kind = "penalty_goal"
        minute, display = _minute(raw.get("clock"))
        participants = [
            p["athlete"].get("displayName")
            for p in raw.get("participants") or []
            if p.get("athlete")
        ]
        team = raw.get("team") or {}
        event = {
            "minute": minute,
            "minute_display": display,
            "period": (raw.get("period") or {}).get("number"),
            "kind": kind,
            "label": text,
            "team": _side(team.get("id", "")) if team.get("id") else None,
            "team_name": team.get("displayName"),
            "player": participants[0] if participants else None,
            "scoring": bool(raw.get("scoringPlay")),
            "text": raw.get("text"),
        }
        if kind == "substitution":
            event["player_on"] = participants[0] if participants else None
            event["player_off"] = participants[1] if len(participants) > 1 else None
        events.append(event)
    events.sort(key=lambda e: (e["period"] or 0, e["minute"] or 0))
    return events


def _stat_map(stats: list[dict], keys: dict[str, str]) -> dict:
    out = {}
    for stat in stats or []:
        name = stat.get("name")
        if name in keys:
            value = stat.get("value", stat.get("displayValue"))
            out[keys[name]] = _number(value)
    return out


def parse_team_stats(summary: dict) -> dict:
    """Box-score team stats, keyed motherwell/opponent with compact names."""
    teams = _require(summary, "boxscore.teams")
    out: dict[str, dict] = {}
    for team in teams:
        side = _side(_require(team, "team.id"))
        out[side] = _stat_map(team.get("statistics", []), TEAM_STAT_KEYS)
    if set(out) != {"motherwell", "opponent"}:
        raise ParseError("Box score does not have both teams")
    return out


def _player_entry(entry: dict) -> dict:
    athlete = entry.get("athlete") or {}
    plays = entry.get("plays") or []
    sub_minutes = [
        _minute(p.get("clock"))[0] for p in plays if p.get("substitution") and p.get("clock")
    ]
    starter = bool(entry.get("starter"))
    on = 0 if starter else (min(sub_minutes) if sub_minutes else None)
    off = None
    if starter and entry.get("subbedOut") and sub_minutes:
        off = min(sub_minutes)
    elif not starter and entry.get("subbedOut") and len(sub_minutes) > 1:
        off = max(sub_minutes)
    minutes = None
    if on is not None:
        minutes = max(0, (off if off is not None else 90) - on)
    stats = {
        k: v for k, v in _stat_map(entry.get("stats", []), PLAYER_STAT_KEYS).items() if v
    }  # zero-valued stats are dropped to keep packs compact; absent means 0
    return {
        "name": athlete.get("displayName"),
        "espn_id": str(athlete.get("id")) if athlete.get("id") is not None else None,
        "jersey": entry.get("jersey"),
        "position": (entry.get("position") or {}).get("abbreviation"),
        "starter": starter,
        "subbed_in": bool(entry.get("subbedIn")),
        "subbed_out": bool(entry.get("subbedOut")),
        "on_minute": on,
        "off_minute": off,
        "minutes_est": minutes,
        **stats,
    }


def parse_lineups(summary: dict) -> dict:
    """Formation, starters and bench for both sides, with estimated minutes.

    Minutes are estimated from substitution clocks (90 for an unsubbed
    starter, no stoppage time) — good enough for usage trends, and labelled
    `minutes_est` so nobody mistakes them for official figures.
    """
    out: dict[str, dict] = {}
    for roster in summary.get("rosters") or []:
        side = _side(_require(roster, "team.id"))
        players = [_player_entry(p) for p in roster.get("roster", [])]
        starters = [p for p in players if p["starter"]]
        bench = [p for p in players if not p["starter"]]
        out[side] = {
            "formation": roster.get("formation"),
            "starters": starters,
            "bench": bench,
            "used_subs": sum(1 for p in bench if p["subbed_in"]),
        }
    if "motherwell" not in out:
        raise ParseError("No Motherwell roster in summary")
    return out


def parse_player_lines(lineups: dict, side: str = "motherwell") -> dict:
    """Highlights from one side's player entries: scorers, assisters, shots, cards."""
    players = lineups[side]["starters"] + lineups[side]["bench"]
    played = [p for p in players if p["starter"] or p["subbed_in"]]

    def top(key: str, n: int = 3) -> list[dict]:
        ranked = sorted(
            (p for p in played if (p.get(key) or 0) > 0),
            key=lambda p: -(p.get(key) or 0),
        )
        return [{"name": p["name"], key: p[key]} for p in ranked[:n]]

    return {
        "scorers": [{"name": p["name"], "goals": p["goals"]} for p in played if p.get("goals")],
        "assists": [
            {"name": p["name"], "assists": p["assists"]} for p in played if p.get("assists")
        ],
        "most_shots": top("shots"),
        "most_shots_on_target": top("shots_on_target"),
        "booked": [p["name"] for p in played if p.get("yellow_cards")],
        "sent_off": [p["name"] for p in played if p.get("red_cards")],
        "players_used": len(played),
    }


def _standings_entries(payload: dict) -> list[dict]:
    """Entries from either a match summary (standings.groups[0]) or the
    standings endpoint (children[0]); [] when there is no table."""
    groups = (payload.get("standings") or {}).get("groups") or payload.get("children") or []
    if not groups:
        return []
    return groups[0].get("standings", {}).get("entries", []) or []


def parse_standings(payload: dict, *, team_id: str = MOTHERWELL_ESPN_ID) -> dict | None:
    """League table from a summary's standings block or the standings endpoint.

    Returns None when there is no table (cups, friendlies). `motherwell` is None
    when the table exists but does not contain the team.
    """
    entries = _standings_entries(payload)
    if not entries:
        return None
    rows = []
    for entry in entries:
        stats = {s["name"]: s.get("value") for s in entry.get("stats", [])}
        team = entry.get("team")
        if isinstance(team, dict):
            espn_id, team_name = str(team.get("id")), team.get("displayName")
        else:
            espn_id, team_name = str(entry.get("id")), team
        row = {
            "rank": int(stats.get("rank") or 0),
            "team": team_name,
            "espn_id": espn_id,
            "played": int(stats.get("gamesPlayed") or 0),
            "wins": int(stats.get("wins") or 0),
            "draws": int(stats.get("ties") or 0),
            "losses": int(stats.get("losses") or 0),
            "goal_difference": int(stats.get("pointDifferential") or 0),
            "points": int(stats.get("points") or 0),
        }
        if stats.get("pointsFor") is not None:
            row["goals_for"] = int(stats["pointsFor"])
            row["goals_against"] = int(stats.get("pointsAgainst") or 0)
        rows.append(row)
    rows.sort(key=lambda r: r["rank"])
    ours = next((r for r in rows if r["espn_id"] == str(team_id)), None)
    if ours is None:
        return {"table": rows, "motherwell": None}
    above = next((r for r in rows if r["rank"] == ours["rank"] - 1), None)
    below = next((r for r in rows if r["rank"] == ours["rank"] + 1), None)
    return {
        "table": rows,
        "motherwell": {
            **ours,
            "gap_to_above": (above["points"] - ours["points"]) if above else None,
            "gap_to_below": (ours["points"] - below["points"]) if below else None,
            "teams": len(rows),
        },
    }
