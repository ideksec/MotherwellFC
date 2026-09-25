# MotherwellFC

[![CI](https://github.com/ideksec/MotherwellFC/actions/workflows/ci.yml/badge.svg)](https://github.com/ideksec/MotherwellFC/actions/workflows/ci.yml)
[![Publish reports site](https://github.com/ideksec/MotherwellFC/actions/workflows/pages.yml/badge.svg)](https://github.com/ideksec/MotherwellFC/actions/workflows/pages.yml)

An analytics lab for Motherwell FC: automated match reports for 'Well fans, plus a
playground for deeper questions about the club. Sister project to
[Baseball-Thoughts](https://github.com/ideksec/Baseball-Thoughts), which does the same
for the Kansas City Royals.

**📊 Read the reports: [ideksec.github.io/MotherwellFC](https://ideksec.github.io/MotherwellFC/)**

Every Motherwell match is pulled, packaged into a compact stat pack, charted and
narrated automatically the next morning, and the write-ups are published to that
site. See [spec.md](spec.md) for the operating spec, standards and data policies.

## What's here

- **`steelmen`** — a Python package of tested, reusable analysis code:
  - `io`: cache-first fetching from ESPN's match API, football-data.co.uk (team xG,
    shots, corners, cards, odds) and TheSportsDB (fixtures); a pluggable `XGProvider`
    interface for a paid feed later
  - `clean`: ESPN summary parsers (match, lineups with estimated minutes, events, team
    stats, table), football-data blocks (xG, market, stats), idempotent match-log upserts
  - `metrics`: form (rolling and season records, streaks, xG difference, xPts), market
    (implied probabilities, points vs market), discipline (corners, cards)
  - `statpack`: assembles the per-match JSON the reports are written from
  - `viz`: the per-match figure (event timeline + recent form) and the season form chart
- **Reports** — `reports/motherwell/matches/` (automated per-match write-ups),
  `previews/` (match-day previews), `monthly/` (month-in-numbers reviews), all served
  as the [published site](https://ideksec.github.io/MotherwellFC/)
- **Notebooks** — narrative analyses that use the package (`notebooks/analysis/`), plus a
  reusable [template](notebooks/templates/analysis_template.ipynb) and an
  [analysis guide](docs/analysis_guide.md)
- **Docs** — a [glossary](docs/glossary.md), a [data source catalog](docs/data_sources.md),
  the [pipeline design](docs/data_pipeline.md), and the Routine instructions for the
  [match report](docs/ROUTINE_MATCH_REPORT.md), [preview](docs/ROUTINE_PREVIEW.md) and
  [monthly review](docs/ROUTINE_MONTHLY.md)

## Structure

```
docs/           Durable notes: glossary, sources, pipeline design, Routine prompts
data/           raw/ and interim/ are local-only (gitignored); processed/ for small derivatives
                processed/motherwell/  matchlog_{season}.csv, statpacks/, fixtures.csv, table.csv,
                                       history_matches.csv (5 seasons, Motherwell-relative)
                processed/spfl/        league_{season}.csv (every Premiership match, trimmed columns)
notebooks/      templates/, exploration/, analysis/, modeling/, viz/
reports/        motherwell/{matches,previews,monthly,figures}/, publishable/, report_template.md
src/            steelmen Python package (io, clean, metrics, statpack, viz, utils)
scripts/        The nightly pull, the history backfill and the site builder
apps/           dashboards/, services/ (empty for now)
tests/          pytest tests for src/ and scripts/, with trimmed real fixtures
scratch/        Temporary work — promote, archive, or delete
```

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest            # offline by default; `pytest -m live` hits the real endpoints
ruff check .
```

Quick example:

```python
import pandas as pd
from steelmen.metrics import last_n_summary, xpoints

log = pd.read_csv("data/processed/motherwell/matchlog_2026-27.csv", dtype={"espn_id": str})
last_n_summary(log, 5, competition="sco.1")   # form, points, xG difference, streak
xpoints(1.10, 1.36)                            # expected points from team xG
```

## Automation

Every Motherwell match produces a published write-up automatically, in three stages:

1. **Nightly stat pack** — [`nightly-motherwell.yml`](.github/workflows/nightly-motherwell.yml)
   runs at 03:00 UTC, scans the last three days across the Premiership, both domestic
   cups, European ties and friendlies, and for each finished match commits a compact
   JSON stat pack to `data/processed/motherwell/statpacks/`, a match-log row, a match
   figure, and refreshed fixtures and table. Deterministic Python
   (`scripts/nightly_motherwell.py`), covered by offline fixture tests.
2. **Morning narrative** — scheduled Claude Routines read any stat pack that lacks a
   report and write a themed match report (`docs/ROUTINE_MATCH_REPORT.md`), a
   match-day preview (`docs/ROUTINE_PREVIEW.md`) and a monthly review
   (`docs/ROUTINE_MONTHLY.md`). They work entirely from committed data — every number
   traces back to a stat pack or CSV — and push to `main` with `[skip ci]`.
3. **Published site** — [`pages.yml`](.github/workflows/pages.yml) renders the reports,
   the season page (table, results, fixtures, points vs xPts) and the figures to GitHub
   Pages via [`scripts/build_site.py`](scripts/build_site.py). It also rebuilds daily at
   11:00 UTC because `[skip ci]` commits don't trigger the push path.

To build the site locally:

```bash
pip install -e ".[site]"
python scripts/build_site.py --out site
# then open site/index.html
```

## Data policy

- Never commit large raw datasets — `data/raw/` and `data/interim/` are gitignored.
- Document all sources in [`docs/data_sources.md`](docs/data_sources.md).
- Only commit processed data that is small, reproducible, and license-safe: per-match
  aggregates and derived tables, never raw payloads.

## License

[MIT](LICENSE) covers the code and writing in this repo. External data sources keep
their own terms, cataloged in [`docs/data_sources.md`](docs/data_sources.md).
