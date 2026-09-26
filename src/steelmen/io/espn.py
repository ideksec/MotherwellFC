"""ESPN's undocumented site API — scoreboards, match summaries, team schedules.

No key. Served by Akamai, which rejects browser-like User-Agents from
cloud IPs but accepts our plain one (see io.cache.USER_AGENT). Date
ranges return 400, so every scoreboard call is a single date.
"""

from pathlib import Path

from steelmen.io.cache import DATA_RAW, cached_get_json
from steelmen.utils.teams import MOTHERWELL_ESPN_ID

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
STANDINGS_BASE = "https://site.api.espn.com/apis/v2/sports/soccer"

# league code -> display name. Order matters: the nightly script scans in
# this order and the first hit wins for a given event id.
LEAGUES: dict[str, str] = {
    "sco.1": "Scottish Premiership",
    "sco.cis": "Scottish League Cup",  # ESPN kept the old CIS Cup code
    "sco.tennents": "Scottish Cup",  # ... and the Tennent's Scottish Cup code
    "uefa.europa.conf_qual": "UEFA Conference League qualifying",
    "uefa.europa_qual": "UEFA Europa League qualifying",
    "uefa.europa.conf": "UEFA Conference League",
    "uefa.europa": "UEFA Europa League",
    "club.friendly": "Club friendly",
}
PREMIERSHIP = "sco.1"

FINAL_STATUSES = {"STATUS_FULL_TIME", "STATUS_FINAL", "STATUS_FINAL_PEN", "STATUS_FINAL_AET"}


def get_scoreboard(
    league: str, date: str, *, cache_dir: Path = DATA_RAW, force: bool = False
) -> dict:
    """All matches in a league on one date (YYYY-MM-DD, UTC day as ESPN sees it)."""
    compact = date.replace("-", "")
    return cached_get_json(
        f"{BASE}/{league}/scoreboard",
        params={"dates": compact},
        cache_path=cache_dir / "espn" / "scoreboard" / f"{league}_{compact}.json",
        force=force,
    )


def get_season_scoreboard(
    league: str,
    year: int | str,
    *,
    cache_dir: Path = DATA_RAW,
    force: bool = False,
    stamp: str | None = None,
) -> dict:
    """Every match ESPN lists for a competition in a calendar year (dates=YYYY).

    The cheapest way to find cup and European ties, whose dates are not on a
    weekly rhythm. stamp is a cache-buster (e.g. today's date).
    """
    suffix = f"_{stamp}" if stamp else ""
    return cached_get_json(
        f"{BASE}/{league}/scoreboard",
        params={"dates": str(year), "limit": "1000"},
        cache_path=cache_dir / "espn" / "season" / f"{league}_{year}{suffix}.json",
        force=force,
    )


def get_summary(
    league: str, event_id: str | int, *, cache_dir: Path = DATA_RAW, force: bool = False
) -> dict:
    """Box score, rosters, key events, standings and odds for one match."""
    return cached_get_json(
        f"{BASE}/{league}/summary",
        params={"event": str(event_id)},
        cache_path=cache_dir / "espn" / "summary" / f"{league}_{event_id}.json",
        force=force,
    )


def get_team_schedule(
    league: str,
    team_id: str = MOTHERWELL_ESPN_ID,
    *,
    fixtures: bool = False,
    cache_dir: Path = DATA_RAW,
    force: bool = False,
) -> dict:
    """A team's season in one league: played matches by default, upcoming
    fixtures with fixtures=True (ESPN's ?fixture=true switch)."""
    suffix = "_fixtures" if fixtures else ""
    return cached_get_json(
        f"{BASE}/{league}/teams/{team_id}/schedule",
        params={"fixture": "true"} if fixtures else None,
        cache_path=cache_dir / "espn" / "schedule" / f"{league}_t{team_id}{suffix}.json",
        force=force,
    )


def get_standings(
    league: str,
    *,
    cache_dir: Path = DATA_RAW,
    force: bool = False,
    stamp: str | None = None,
) -> dict:
    """The league table as ESPN has it now (stamp = cache-buster, e.g. today's date)."""
    suffix = f"_{stamp}" if stamp else ""
    return cached_get_json(
        f"{STANDINGS_BASE}/{league}/standings",
        cache_path=cache_dir / "espn" / "standings" / f"{league}{suffix}.json",
        force=force,
    )


def event_status(event: dict) -> str:
    comp = event["competitions"][0]
    status = comp.get("status") or event.get("status") or {}
    return status.get("type", {}).get("name", "")


def is_final(event: dict) -> bool:
    comp = event["competitions"][0]
    status = comp.get("status") or event.get("status") or {}
    kind = status.get("type", {})
    return kind.get("name") in FINAL_STATUSES or bool(kind.get("completed"))


def involves_team(event: dict, team_id: str = MOTHERWELL_ESPN_ID) -> bool:
    return any(
        str(c["team"]["id"]) == str(team_id) for c in event["competitions"][0]["competitors"]
    )


def team_events(scoreboard: dict, team_id: str = MOTHERWELL_ESPN_ID) -> list[dict]:
    """This team's events on a scoreboard, in kickoff order."""
    events = [e for e in scoreboard.get("events", []) if involves_team(e, team_id)]
    return sorted(events, key=lambda e: e["date"])


def final_events(scoreboard: dict, team_id: str = MOTHERWELL_ESPN_ID) -> list[dict]:
    return [e for e in team_events(scoreboard, team_id) if is_final(e)]
