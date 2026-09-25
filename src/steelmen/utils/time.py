"""UK-local dates and season codes.

Scottish seasons run July to May. Everything user-facing (match dates,
lookback windows, filenames) is in Europe/London; ESPN timestamps are UTC.
"""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

UK = ZoneInfo("Europe/London")


def parse_espn_datetime(value: str) -> datetime:
    """ESPN writes "2026-09-15T18:45Z" (no seconds). Returns an aware UTC datetime."""
    text = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def uk_date(value: str | datetime) -> str:
    """ISO date of a UTC timestamp in UK local time (the match day fans remember)."""
    when = parse_espn_datetime(value) if isinstance(value, str) else value
    return when.astimezone(UK).date().isoformat()


def season_label(day: str | date) -> str:
    """ "2026-27" for any date from July 2026 to June 2027."""
    d = date.fromisoformat(day) if isinstance(day, str) else day
    start = d.year if d.month >= 7 else d.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def season_code(day: str | date) -> str:
    """football-data.co.uk's 4-digit season code: "2627" for 2026-27."""
    label = season_label(day)
    return label[2:4] + label[-2:]
