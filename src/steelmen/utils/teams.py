"""Team identity across sources.

ESPN abbreviations collide (Dundee and Dundee United are both "DUN"), so
slugs and cross-source names key off the ESPN team id, with a display-name
fallback for opponents outside the Premiership (cups, Europe, friendlies).
"""

import re

MOTHERWELL_ESPN_ID = "266"
MOTHERWELL_TSDB_ID = "133640"
MOTHERWELL_FD_NAME = "Motherwell"

# espn_id -> (display name, slug, football-data.co.uk name)
TEAMS: dict[str, dict[str, str]] = {
    "263": {"name": "Aberdeen", "slug": "aberdeen", "fd": "Aberdeen"},
    "256": {"name": "Celtic", "slug": "celtic", "fd": "Celtic"},
    "261": {"name": "Dundee", "slug": "dundee", "fd": "Dundee"},
    "264": {"name": "Dundee United", "slug": "dundee-utd", "fd": "Dundee United"},
    "254": {"name": "Falkirk", "slug": "falkirk", "fd": "Falkirk"},
    "262": {"name": "Heart of Midlothian", "slug": "hearts", "fd": "Hearts"},
    "258": {"name": "Hibernian", "slug": "hibs", "fd": "Hibernian"},
    "260": {"name": "Kilmarnock", "slug": "kilmarnock", "fd": "Kilmarnock"},
    "266": {"name": "Motherwell", "slug": "motherwell", "fd": "Motherwell"},
    "257": {"name": "Rangers", "slug": "rangers", "fd": "Rangers"},
    "267": {"name": "St Johnstone", "slug": "st-johnstone", "fd": "St Johnstone"},
    "250": {"name": "St Mirren", "slug": "st-mirren", "fd": "St Mirren"},
    "255": {"name": "Livingston", "slug": "livingston", "fd": "Livingston"},
    "259": {"name": "Ross County", "slug": "ross-county", "fd": "Ross County"},
}


def slugify(name: str) -> str:
    """Lowercase, ASCII-ish, hyphenated: "St. Johnstone FC" -> "st-johnstone-fc"."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "unknown"


def team_slug(espn_id: str | None, display_name: str) -> str:
    known = TEAMS.get(str(espn_id)) if espn_id is not None else None
    return known["slug"] if known else slugify(display_name)


def footballdata_name(espn_id: str | None, display_name: str) -> str:
    """The name football-data.co.uk uses for this team (best effort)."""
    known = TEAMS.get(str(espn_id)) if espn_id is not None else None
    return known["fd"] if known else display_name
