"""TheSportsDB (free key "3") — upcoming fixtures for previews.

The free key truncates list endpoints to five rows and lags on lineups,
so it is a fixtures source only. Premium removes the truncation.
"""

from pathlib import Path

from steelmen.io.cache import DATA_RAW, cached_get_json
from steelmen.utils.teams import MOTHERWELL_TSDB_ID

BASE = "https://www.thesportsdb.com/api/v1/json/3"


def next_events(
    team_id: str = MOTHERWELL_TSDB_ID,
    *,
    cache_dir: Path = DATA_RAW,
    force: bool = False,
    stamp: str | None = None,
) -> list[dict]:
    suffix = f"_{stamp}" if stamp else ""
    payload = cached_get_json(
        f"{BASE}/eventsnext.php",
        params={"id": team_id},
        cache_path=cache_dir / "thesportsdb" / f"next_{team_id}{suffix}.json",
        force=force,
    )
    return payload.get("events") or []
