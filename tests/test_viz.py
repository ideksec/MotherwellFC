import pandas as pd

from steelmen.clean.matchlog import load_matchlog
from steelmen.viz import form_figure, match_figure


def test_match_figure_renders(tmp_path, fixtures_dir):
    """Smoke test on a committed real pack + log; Agg backend, no display needed."""
    import json
    from pathlib import Path

    repo = Path(__file__).resolve().parent.parent
    packs = sorted((repo / "data/processed/motherwell/statpacks").glob("*.json"))
    logs = sorted((repo / "data/processed/motherwell").glob("matchlog_*.csv"))
    if not packs or not logs:  # fresh clone without seeded data
        return
    pack = json.loads(packs[-1].read_text())
    out = match_figure(pack, load_matchlog(logs[-1]), tmp_path / "m.png")
    assert out.exists() and out.stat().st_size > 10_000


def test_form_figure_handles_empty(tmp_path):
    empty = pd.DataFrame(
        columns=["competition_code", "kickoff_utc", "espn_id", "points", "motherwell_xg",
                 "opponent_xg", "result"]
    )  # fmt: skip
    out = form_figure(empty, tmp_path / "f.png")
    assert out.exists()
