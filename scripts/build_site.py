#!/usr/bin/env python3
"""Render the Motherwell reports as a static site.

Reads the committed markdown under reports/motherwell/ (matches/, previews/,
monthly/), the season match log, fixtures and table, and writes a browsable
site: an index grouped by report type, a season page with the league table
and a form chart, and one page per report. Report files are the only
source of prose — this script adds no numbers of its own beyond what is in
the processed CSVs.

Usage:
    python scripts/build_site.py --out site
"""

from __future__ import annotations

import argparse
import re
import shutil
from dataclasses import dataclass
from html import escape
from pathlib import Path

import markdown
import pandas as pd

from steelmen.viz.season import form_figure

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports" / "motherwell"
FIGURES_DIR = REPORTS_DIR / "figures"
DATA_DIR = REPO_ROOT / "data" / "processed" / "motherwell"
REPO_URL = "https://github.com/ideksec/MotherwellFC"
SITE_TITLE = "Motherwell in numbers"

# {date}_{vs|at}-{opp-slug}[_{competition}].md — the contract in statpack.report_filename
MATCH_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(vs|at)-([a-z0-9-]+?)(?:_([a-z0-9-]+))?\.md$")
PREVIEW_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(vs|at)-([a-z0-9-]+?)(?:_([a-z0-9-]+))?\.md$")
MONTHLY_RE = re.compile(r"^(\d{4}-\d{2})(?:_([a-z0-9-]+))?\.md$")

SECTIONS = [
    ("matches", "Match reports", MATCH_RE),
    ("previews", "Previews", PREVIEW_RE),
    ("monthly", "Monthly reviews", MONTHLY_RE),
]

STYLESHEET = """
:root {
  --bg: #fbfaf8; --surface: #ffffff; --border: #e2ded7; --text: #1c1a17; --muted: #6b655c;
  --accent: #7a1e2c; --accent-soft: #f6e9eb; --amber: #f5b41e;
  --win: #1c6b3f; --win-bg: #e4f2ea; --draw: #8a6508; --draw-bg: #fbf1d6;
  --loss: #97341f; --loss-bg: #f8e8e3; --radius: 10px;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #15141a; --surface: #1d1b23; --border: #322f3a; --text: #ebe8e3; --muted: #a29da8;
    --accent: #e08a97; --accent-soft: #3a222a; --amber: #f5c65a;
    --win: #6ed09b; --win-bg: #17301f; --draw: #f5c65a; --draw-bg: #3a2f14;
    --loss: #e89a86; --loss-bg: #331d18;
  }
}
:root[data-theme="dark"] {
  --bg: #15141a; --surface: #1d1b23; --border: #322f3a; --text: #ebe8e3; --muted: #a29da8;
  --accent: #e08a97; --accent-soft: #3a222a; --amber: #f5c65a;
  --win: #6ed09b; --win-bg: #17301f; --draw: #f5c65a; --draw-bg: #3a2f14;
  --loss: #e89a86; --loss-bg: #331d18;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--text);
  font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
.wrap { max-width: 46rem; margin: 0 auto; padding: 2.5rem 1rem 4rem; }
a { color: var(--accent); }
header.masthead {
  border-bottom: 3px solid var(--amber); margin-bottom: 2rem; padding-bottom: 1.5rem;
}
header.masthead h1 {
  font-size: 1.9rem; line-height: 1.2; margin: 0 0 .4rem; letter-spacing: -.02em;
}
header.masthead p { color: var(--muted); margin: 0; }
nav.top { display: flex; gap: 1.2rem; margin: 1rem 0 0; font-size: .9rem; }
.backlink {
  display: inline-block; margin-bottom: 1.5rem; font-size: .9rem; text-decoration: none;
}
.backlink:hover { text-decoration: underline; }
.season { display: flex; flex-wrap: wrap; gap: .5rem 2rem; margin: 1.25rem 0 0; padding: 0; }
.season div { display: flex; flex-direction: column; }
.season .k {
  font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; color: var(--muted);
}
.season .v { margin: 0; font-size: 1.25rem; font-variant-numeric: tabular-nums; font-weight: 600; }
h2.section { font-size: 1.05rem; margin: 2.25rem 0 .75rem; color: var(--muted);
  text-transform: uppercase; letter-spacing: .08em; }
ul.games { list-style: none; margin: 0; padding: 0; }
ul.games li { margin: 0 0 .75rem; }
.game {
  display: block; padding: 1rem 1.1rem; background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius);
  text-decoration: none; color: inherit;
}
.game:hover { border-color: var(--accent); }
.game .meta {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: .6rem; margin-bottom: .3rem;
}
.game .date, .game .score {
  font-size: .8rem; color: var(--muted); font-variant-numeric: tabular-nums;
}
.badge { font-size: .72rem; font-weight: 700; letter-spacing: .06em; padding: .1rem .45rem;
  border-radius: 4px; text-transform: uppercase; }
.badge.w { color: var(--win); background: var(--win-bg); }
.badge.d { color: var(--draw); background: var(--draw-bg); }
.badge.l { color: var(--loss); background: var(--loss-bg); }
.game .title { font-weight: 600; line-height: 1.35; }
article h1 { font-size: 1.75rem; line-height: 1.25; letter-spacing: -.02em; margin: 0 0 1rem; }
article h2 {
  font-size: 1.15rem; margin: 2.25rem 0 .75rem; padding-bottom: .3rem;
  border-bottom: 1px solid var(--border);
}
article h3 { font-size: 1rem; margin: 1.75rem 0 .5rem; color: var(--accent); }
article blockquote {
  margin: 0 0 1.5rem; padding: .6rem 0 .6rem 1rem;
  border-left: 3px solid var(--amber); color: var(--muted); font-size: .9rem;
}
article blockquote p { margin: .15rem 0; }
article code {
  background: var(--accent-soft); padding: .1rem .3rem; border-radius: 3px; font-size: .87em;
  word-break: break-word;
}
article img, .figure img {
  max-width: 100%; height: auto; border: 1px solid var(--border); border-radius: var(--radius);
}
.table-scroll { overflow-x: auto; margin: 1.25rem 0; }
table {
  border-collapse: collapse; width: 100%; font-size: .87rem;
  font-variant-numeric: tabular-nums;
}
th, td {
  padding: .4rem .55rem; text-align: right; border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
th:first-child, td:first-child { text-align: left; }
thead th {
  color: var(--muted); font-size: .72rem; text-transform: uppercase; letter-spacing: .06em;
}
tr.us td { font-weight: 700; color: var(--accent); }
footer.site {
  margin-top: 3.5rem; padding-top: 1.25rem; border-top: 1px solid var(--border);
  color: var(--muted); font-size: .82rem;
}
footer.site a { color: var(--muted); }
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<style>{css}</style>
</head>
<body>
<div class="wrap">
{body}
<footer class="site">
  Generated from the committed reports in
  <a href="{repo}/tree/main/reports/motherwell">reports/motherwell</a>
  by <a href="{repo}/blob/main/scripts/build_site.py">scripts/build_site.py</a>.
  Match data: ESPN box scores; xG and odds: football-data.co.uk.
</footer>
</div>
</body>
</html>
"""


@dataclass
class Report:
    section: str
    path: Path
    date: str
    title: str
    html: str
    home_away: str | None = None
    opponent: str | None = None
    competition: str | None = None

    @property
    def slug(self) -> str:
        return f"{self.section}/{self.path.stem}"

    @property
    def matchup(self) -> str:
        if not self.opponent:
            return ""
        prefix = "vs" if self.home_away == "vs" else "at"
        return f"{prefix} {self.opponent.replace('-', ' ').title()}"


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"espn_id": str}) if path.exists() else pd.DataFrame()


def load_matchlog(data_dir: Path) -> pd.DataFrame:
    frames = [load_csv(p) for p in sorted(data_dir.glob("matchlog_*.csv"))]
    frames = [f for f in frames if not f.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _first_heading(md_text: str) -> str:
    for line in md_text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled report"


def render_markdown(md_text: str, *, depth: int) -> str:
    """Markdown -> HTML, tables wrapped to scroll, figure paths rewritten relative
    to the page (reports link figures as reports/motherwell/figures/x.png)."""
    html = markdown.markdown(md_text, extensions=["tables", "sane_lists"])
    html = html.replace("<table>", '<div class="table-scroll"><table>').replace(
        "</table>", "</table></div>"
    )
    prefix = "../" * depth
    html = html.replace('src="reports/motherwell/figures/', f'src="{prefix}figures/')
    html = html.replace('src="../figures/', f'src="{prefix}figures/')
    return html


def collect_reports(reports_dir: Path) -> list[Report]:
    reports = []
    for section, _, pattern in SECTIONS:
        folder = reports_dir / section
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.md")):
            match = pattern.match(path.name)
            if not match:
                continue
            text = path.read_text()
            groups = match.groups()
            if section == "monthly":
                report = Report(
                    section=section,
                    path=path,
                    date=groups[0],
                    title=_first_heading(text),
                    html=render_markdown(text, depth=1),
                )
            else:
                report = Report(
                    section=section,
                    path=path,
                    date=groups[0],
                    title=_first_heading(text),
                    html=render_markdown(text, depth=1),
                    home_away=groups[1],
                    opponent=groups[2],
                    competition=groups[3],
                )
            reports.append(report)
    reports.sort(key=lambda r: r.date, reverse=True)
    return reports


def game_facts(matchlog: pd.DataFrame, report: Report) -> dict | None:
    if matchlog.empty or report.section != "matches":
        return None
    rows = matchlog[
        (matchlog["date"] == report.date) & (matchlog["opponent_slug"] == report.opponent)
    ]
    if rows.empty:
        return None
    row = rows.iloc[0]
    return {
        "result": str(row["result"]),
        "gf": int(row["motherwell_goals"]),
        "ga": int(row["opponent_goals"]),
        "competition": str(row["competition"]),
    }


def season_strip(matchlog: pd.DataFrame, table: pd.DataFrame, fixtures: pd.DataFrame) -> str:
    if matchlog.empty:
        return ""
    league = matchlog[matchlog["competition_code"] == "sco.1"]
    w = int((league["result"] == "W").sum())
    d = int((league["result"] == "D").sum())
    lo = int((league["result"] == "L").sum())
    pts = 3 * w + d
    gd = int(league["motherwell_goals"].sum() - league["opponent_goals"].sum())
    position = ""
    if not table.empty:
        ours = table[table["team"] == "Motherwell"]
        if not ours.empty:
            position = f"{int(ours.iloc[0]['rank'])} of {len(table)}"
    next_fixture = ""
    if not fixtures.empty:
        nxt = fixtures.sort_values("date").iloc[0]
        prefix = "v" if nxt["home_away"] == "home" else "@"
        next_fixture = f"{nxt['date']} {prefix} {nxt['opponent']}"
    cells = [
        ("Premiership", f"{w}&#8211;{d}&#8211;{lo}"),
        ("Points", str(pts)),
        ("GD", f"{gd:+d}"),
        ("Position", position or "&#8212;"),
        ("Next", escape(next_fixture) or "&#8212;"),
    ]
    return (
        '<div class="season">'
        + "".join(
            f'<div><span class="k">{k}</span><span class="v">{v}</span></div>' for k, v in cells
        )
        + "</div>"
    )


def _masthead(matchlog, table, fixtures, *, depth: int) -> str:
    prefix = "../" * depth
    return (
        '<header class="masthead">'
        f"<h1>{SITE_TITLE}</h1>"
        "<p>Motherwell FC match reports, previews and reviews generated from committed "
        "stat packs. Every number traces to a file in the repository.</p>"
        f'<nav class="top"><a href="{prefix}index.html">Reports</a>'
        f'<a href="{prefix}season.html">Season</a>'
        f'<a href="{REPO_URL}">Repository</a></nav>'
        f"{season_strip(matchlog, table, fixtures)}"
        "</header>"
    )


def render_index(reports, matchlog, table, fixtures) -> str:
    body = [_masthead(matchlog, table, fixtures, depth=0)]
    for section, label, _ in SECTIONS:
        items = []
        for report in [r for r in reports if r.section == section]:
            facts = game_facts(matchlog, report)
            badge = score = ""
            if facts:
                badge = f'<span class="badge {facts["result"].lower()}">{facts["result"]}</span>'
                score = (
                    f'<span class="score">{facts["gf"]}&#8211;{facts["ga"]} &middot; '
                    f"{escape(facts['competition'])}</span>"
                )
            items.append(
                f'<li><a class="game" href="{escape(report.slug)}.html">'
                f'<span class="meta"><span class="date">{escape(report.date)}</span>'
                f'{badge}<span class="score">{escape(report.matchup)}</span>{score}</span>'
                f'<span class="title">{escape(report.title)}</span></a></li>'
            )
        if items:
            body.append(f'<h2 class="section">{label}</h2><ul class="games">{"".join(items)}</ul>')
    if len(body) == 1:
        body.append("<p>No reports yet.</p>")
    return PAGE.format(
        title=SITE_TITLE,
        description="Motherwell FC match reports generated from committed stat packs.",
        css=STYLESHEET,
        body="".join(body),
        repo=REPO_URL,
    )


def render_season(matchlog, table, fixtures, *, figure_rel: str | None) -> str:
    body = [_masthead(matchlog, table, fixtures, depth=0)]
    if figure_rel:
        body.append(
            f'<div class="figure"><img src="{figure_rel}" '
            'alt="Cumulative Premiership points versus expected points"></div>'
        )
    if not table.empty:
        rows = []
        for r in table.sort_values("rank").itertuples():
            cls = ' class="us"' if r.team == "Motherwell" else ""
            rows.append(
                f"<tr{cls}><td>{int(r.rank)}</td><td>{escape(str(r.team))}</td><td>{int(r.played)}</td>"
                f"<td>{int(r.wins)}</td><td>{int(r.draws)}</td><td>{int(r.losses)}</td>"
                f"<td>{int(r.goal_difference):+d}</td><td>{int(r.points)}</td></tr>"
            )
        body.append(
            '<h2 class="section">Premiership table</h2>'
            '<div class="table-scroll"><table><thead><tr><th>#</th><th>Team</th><th>P</th>'
            "<th>W</th><th>D</th><th>L</th><th>GD</th><th>Pts</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>"
        )
    if not matchlog.empty:
        rows = []
        for r in matchlog.sort_values("kickoff_utc", ascending=False).itertuples():
            prefix = "v" if r.home_away == "home" else "@"
            xg = (
                f"{float(r.motherwell_xg):.2f}&#8211;{float(r.opponent_xg):.2f}"
                if pd.notna(r.motherwell_xg) and pd.notna(r.opponent_xg)
                else "&#8212;"
            )
            rows.append(
                f"<tr><td>{escape(str(r.date))}</td><td>{prefix} {escape(str(r.opponent))}</td>"
                f"<td>{escape(str(r.competition))}</td>"
                f'<td><span class="badge {str(r.result).lower()}">'
                f"{escape(str(r.result))}</span></td>"
                f"<td>{int(r.motherwell_goals)}&#8211;{int(r.opponent_goals)}</td><td>{xg}</td></tr>"
            )
        body.append(
            '<h2 class="section">Results</h2>'
            '<div class="table-scroll"><table><thead><tr><th>Date</th><th>Opponent</th>'
            "<th>Competition</th><th></th><th>Score</th><th>xG</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>"
        )
    if not fixtures.empty:
        rows = []
        for r in fixtures.sort_values("date").itertuples():
            prefix = "v" if r.home_away == "home" else "@"
            rows.append(
                f"<tr><td>{escape(str(r.date))}</td><td>{prefix} {escape(str(r.opponent))}</td>"
                f"<td>{escape(str(r.competition))}</td></tr>"
            )
        body.append(
            '<h2 class="section">Fixtures</h2>'
            '<div class="table-scroll"><table><thead><tr><th>Date</th><th>Opponent</th>'
            f"<th>Competition</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        )
    return PAGE.format(
        title=f"Season — {SITE_TITLE}",
        description="Motherwell FC season page: table, results, fixtures, and points versus xPts.",
        css=STYLESHEET,
        body="".join(body),
        repo=REPO_URL,
    )


def render_report(report: Report) -> str:
    body = (
        '<a class="backlink" href="../index.html">&larr; All reports</a>'
        f"<article>{report.html}</article>"
    )
    return PAGE.format(
        title=f"{report.date} {report.matchup} — {SITE_TITLE}".replace("  ", " "),
        description=escape(report.title, quote=True),
        css=STYLESHEET,
        body=body,
        repo=REPO_URL,
    )


def build(
    out_dir: Path,
    *,
    reports_dir: Path = REPORTS_DIR,
    data_dir: Path = DATA_DIR,
    figures_dir: Path = FIGURES_DIR,
) -> int:
    """Write the site to out_dir. Returns the number of reports rendered."""
    reports = collect_reports(reports_dir)
    matchlog = load_matchlog(data_dir)
    table = load_csv(data_dir / "table.csv")
    fixtures = load_csv(data_dir / "fixtures.csv")

    if out_dir.exists():
        shutil.rmtree(out_dir)
    for section, _, _ in SECTIONS:
        (out_dir / section).mkdir(parents=True)
    (out_dir / "figures").mkdir(parents=True, exist_ok=True)
    if figures_dir.exists():
        for png in figures_dir.glob("*.png"):
            shutil.copy(png, out_dir / "figures" / png.name)

    figure_rel = None
    if not matchlog.empty:
        form_figure(matchlog, out_dir / "figures" / "season_form.png")
        figure_rel = "figures/season_form.png"

    (out_dir / "index.html").write_text(render_index(reports, matchlog, table, fixtures))
    (out_dir / "season.html").write_text(
        render_season(matchlog, table, fixtures, figure_rel=figure_rel)
    )
    for report in reports:
        (out_dir / f"{report.slug}.html").write_text(render_report(report))
    (out_dir / ".nojekyll").write_text("")
    return len(reports)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="site", help="output directory (default: site)")
    args = parser.parse_args()
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    count = build(out_dir)
    print(f"RESULT: rendered {count} report(s) to {out_dir}")


if __name__ == "__main__":
    main()
