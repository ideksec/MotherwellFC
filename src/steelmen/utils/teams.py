"""Team identity across sources.

ESPN abbreviations collide (Dundee and Dundee United are both "DUN"), so
slugs and cross-source names key off the ESPN team id, with a display-name
fallback for opponents outside the Premiership (cups, Europe, friendlies).
"""

import re

MOTHERWELL_ESPN_ID = "266"
MOTHERWELL_TSDB_ID = "133640"
MOTHERWELL_FD_NAME = "Motherwell"

# espn_id -> display name, slug, football-data.co.uk name, unique 3-letter code
TEAMS: dict[str, dict[str, str]] = {
    "263": {"name": "Aberdeen", "slug": "aberdeen", "fd": "Aberdeen", "short": "ABE"},
    "256": {"name": "Celtic", "slug": "celtic", "fd": "Celtic", "short": "CEL"},
    "261": {"name": "Dundee", "slug": "dundee", "fd": "Dundee", "short": "DEE"},
    "264": {"name": "Dundee United", "slug": "dundee-utd", "fd": "Dundee United", "short": "DUN"},
    "254": {"name": "Falkirk", "slug": "falkirk", "fd": "Falkirk", "short": "FAL"},
    "262": {"name": "Heart of Midlothian", "slug": "hearts", "fd": "Hearts", "short": "HEA"},
    "258": {"name": "Hibernian", "slug": "hibs", "fd": "Hibernian", "short": "HIB"},
    "260": {"name": "Kilmarnock", "slug": "kilmarnock", "fd": "Kilmarnock", "short": "KIL"},
    "266": {"name": "Motherwell", "slug": "motherwell", "fd": "Motherwell", "short": "MOT"},
    "257": {"name": "Rangers", "slug": "rangers", "fd": "Rangers", "short": "RAN"},
    "267": {"name": "St Johnstone", "slug": "st-johnstone", "fd": "St Johnstone", "short": "STJ"},
    "250": {"name": "St Mirren", "slug": "st-mirren", "fd": "St Mirren", "short": "STM"},
    "255": {"name": "Livingston", "slug": "livingston", "fd": "Livingston", "short": "LIV"},
    "259": {"name": "Ross County", "slug": "ross-county", "fd": "Ross County", "short": "ROS"},
}
_SLUG_INDEX = {v["slug"]: v for v in TEAMS.values()}


def slugify(name: str) -> str:
    """Lowercase, ASCII-ish, hyphenated: "St. Johnstone FC" -> "st-johnstone-fc"."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "unknown"


def team_slug(espn_id: str | None, display_name: str) -> str:
    known = TEAMS.get(str(espn_id)) if espn_id is not None else None
    return known["slug"] if known else slugify(display_name)


def team_short(espn_id: str | None = None, *, slug: str | None = None, name: str = "") -> str:
    """A unique 3-letter code for figures (Dundee -> DEE, Dundee United -> DUN)."""
    known = TEAMS.get(str(espn_id)) if espn_id is not None else None
    if known is None and slug:
        known = _SLUG_INDEX.get(slug)
    if known:
        return known["short"]
    source = (slug or name).replace("-", "")
    return source[:3].upper() or "UNK"


def ordinal(n: int) -> str:
    """1 -> 1st, 2 -> 2nd, 11 -> 11th, 22 -> 22nd."""
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def footballdata_name(espn_id: str | None, display_name: str) -> str:
    """The name football-data.co.uk uses for this team (best effort)."""
    known = TEAMS.get(str(espn_id)) if espn_id is not None else None
    return known["fd"] if known else display_name
