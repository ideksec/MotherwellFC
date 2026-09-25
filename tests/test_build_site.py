import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "build_site.py"


@pytest.fixture(scope="module")
def site():
    spec = importlib.util.spec_from_file_location("build_site", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_site"] = module  # dataclasses need the module importable by name
    spec.loader.exec_module(module)
    return module


SAMPLE_REPORT = """# Motherwell 1, Dundee 2: a penalty and a scramble

> Date: 2026-09-19
> Author: MotherwellFC match pipeline

## Question

What happened?

## Results

| Team | Shots | xG |
|------|-------|----|
| Motherwell | 15 | 1.10 |
| Dundee | 8 | 1.36 |

![Match figure](reports/motherwell/figures/2026-09-19_at-dundee.png)
"""


def _make_repo(tmp_path):
    reports = tmp_path / "reports"
    for section in ("matches", "previews", "monthly"):
        (reports / section).mkdir(parents=True)
    (reports / "matches" / "2026-09-19_at-dundee.md").write_text(SAMPLE_REPORT)
    (reports / "previews" / "2026-10-11_vs-celtic.md").write_text("# Celtic preview\n\ntext\n")
    (reports / "monthly" / "2026-09.md").write_text("# September in numbers\n\ntext\n")
    (reports / "matches" / "notes.md").write_text("# ignored\n")
    figures = reports / "figures"
    figures.mkdir()
    (figures / "2026-09-19_at-dundee.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    data = tmp_path / "data"
    data.mkdir()
    (data / "matchlog_2026-27.csv").write_text(
        "espn_id,date,kickoff_utc,season,competition_code,competition,home_away,opponent,"
        "opponent_slug,result,points,motherwell_goals,opponent_goals,motherwell_xg,opponent_xg\n"
        "401878380,2026-09-19,2026-09-19T14:00Z,2026-27,sco.1,Scottish Premiership,away,Dundee,"
        "dundee,L,0,1,2,1.1,1.36\n"
    )
    (data / "table.csv").write_text(
        "rank,team,espn_id,played,wins,draws,losses,goal_difference,points\n"
        "1,Celtic,256,7,6,0,1,10,18\n8,Motherwell,266,7,2,2,3,-2,8\n"
    )
    (data / "fixtures.csv").write_text(
        "date,kickoff_utc,competition,competition_code,home_away,opponent,"
        "opponent_espn_id,venue,source\n"
        "2026-10-11,2026-10-11T11:00:00Z,Scottish Premier League,,home,Celtic,,"
        "Fir Park,thesportsdb\n"
    )
    return reports, data, figures


def test_collect_reports_by_section(site, tmp_path):
    reports, _, _ = _make_repo(tmp_path)
    found = site.collect_reports(reports)
    assert [(r.section, r.date) for r in found] == [
        ("previews", "2026-10-11"),
        ("matches", "2026-09-19"),
        ("monthly", "2026-09"),
    ]
    match = next(r for r in found if r.section == "matches")
    assert match.opponent == "dundee" and match.home_away == "at"
    assert match.title.startswith("Motherwell 1, Dundee 2")


def test_build_renders_everything(site, tmp_path):
    reports, data, figures = _make_repo(tmp_path)
    out = tmp_path / "site"
    count = site.build(out, reports_dir=reports, data_dir=data, figures_dir=figures)
    assert count == 3
    index = (out / "index.html").read_text()
    assert 'class="badge l"' in index and "Match reports" in index and "Previews" in index
    assert "8 of 2" in index  # position cell from table.csv
    assert "2026-10-11 v Celtic" in index
    page = (out / "matches" / "2026-09-19_at-dundee.html").read_text()
    assert '<div class="table-scroll"><table>' in page
    assert 'src="../figures/2026-09-19_at-dundee.png"' in page
    season = (out / "season.html").read_text()
    assert 'class="us"' in season and "figures/season_form.png" in season
    assert (out / "figures" / "season_form.png").exists()
    assert (out / ".nojekyll").exists()


def test_build_with_no_data(site, tmp_path):
    out = tmp_path / "site"
    count = site.build(
        out,
        reports_dir=tmp_path / "none",
        data_dir=tmp_path / "none",
        figures_dir=tmp_path / "none",
    )
    assert count == 0
    assert "No reports yet" in (out / "index.html").read_text()


class TestCommittedReports:
    """Every committed match report must follow the filename contract and render."""

    def test_filenames_follow_contract(self, site):
        folder = REPO / "reports" / "motherwell" / "matches"
        for path in folder.glob("*.md"):
            assert site.MATCH_RE.match(path.name), path.name

    def test_reports_cite_a_pack_and_render(self, site):
        folder = REPO / "reports" / "motherwell" / "matches"
        for path in folder.glob("*.md"):
            text = path.read_text()
            assert re.search(
                r"data/processed/motherwell/statpacks/\d{4}-\d{2}-\d{2}_\d+\.json", text
            ), f"{path.name} does not cite its stat pack"
            html = site.render_markdown(text, depth=1)
            assert "<h1>" in html

    def test_full_site_builds(self, site, tmp_path):
        count = site.build(tmp_path / "site")
        assert count >= 0
