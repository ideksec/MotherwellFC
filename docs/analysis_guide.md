# Analysis guide — the playground half

How to ask a deep question about Motherwell in this repo, whether in a notebook or an
interactive Claude session.

## 1. Start from committed data

```python
import json
from pathlib import Path
import pandas as pd

log = pd.read_csv("data/processed/motherwell/matchlog_2026-27.csv", dtype={"espn_id": str})
history = pd.read_csv("data/processed/motherwell/history_matches.csv")   # 2021-22 → now, league
league = pd.read_csv("data/processed/spfl/league_2025-26.csv")            # every match that season
table = pd.read_csv("data/processed/motherwell/table.csv")
packs = [json.loads(p.read_text()) for p in sorted(Path("data/processed/motherwell/statpacks").glob("*.json"))]
```

What each holds:

| File | Grain | Highlights |
|------|-------|-----------|
| `matchlog_{season}.csv` | one row per Motherwell match, all competitions | result, points, goals, xG, shots, SOT, possession, corners, cards, odds, attendance, referee |
| `history_matches.csv` | one row per Motherwell league match since 2021-22 | same shape (xG from 2026-27 only) |
| `spfl/league_{season}.csv` | every Premiership match | football-data columns: results, xG (2026-27), shots, corners, cards, odds |
| `statpacks/*.json` | one JSON per match | lineups with `minutes_est`, events with minutes, player lines, table after the match, rolling blocks |
| `table.csv`, `fixtures.csv` | current | league table; upcoming fixtures |

Notebooks never fetch. If you need more data, add a fetcher to `steelmen.io` with a
cache path and a test, then run it from a script.

## 2. Use the package for anything reusable

```python
from steelmen.metrics import last_n_summary, season_summary, xpoints, implied_probabilities
from steelmen.metrics.discipline import discipline_summary
from steelmen.viz import form_figure, match_figure
```

If a notebook grows a helper worth reusing, move it into `src/steelmen/` with a test.

## 3. Follow the notebook template

`notebooks/templates/analysis_template.ipynb`: Header (question, data, window,
assumptions) → Method → Results → Conclusion (finding, limitations, next step). Name it
`YYYY-MM-DD_short-question.ipynb` under `notebooks/analysis/`.

## 4. Promote the answer

A question worth keeping becomes a report under `reports/motherwell/` following
`reports/report_template.md`, with figures in `reports/motherwell/figures/`. Long
pieces for fans go through `reports/publishable/` once polished. The monthly review
Routine (`docs/ROUTINE_MONTHLY.md`) draws on the same files.

## 5. Question backlog (starters)

- Does Motherwell's points total track xPts, and where are the outliers?
- Home vs away splits in shots, xG and points, this season vs the last five.
- Who is carrying the attacking load (shots, goals, assists per 90 from `minutes_est`)?
- Set pieces: corners for and against, and how they relate to results.
- Referee effects: cards and fouls per match by referee across five seasons.
- Market vs reality: cumulative points vs market-expected points; biggest upsets.
- First-half vs second-half goals (`ht_*` columns) and comeback frequency.
