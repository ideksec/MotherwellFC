# Data Pipeline Design

> Date: 2026-09-25
> Status: implemented (free stack); paid xG adapter reserved

## Goal

A reproducible pipeline for Motherwell match data — results, lineups, events, box-score
stats, team xG and market odds — so every report and notebook reads cached, structured
data instead of news snippets. Same shape as Baseball-Thoughts' Royals pipeline.

## Requirements

- Every Motherwell match in every competition: result, lineups, events, team stats
- Team xG and pre-match market odds where a source exists (Premiership)
- League table and upcoming fixtures for previews and the site
- Five seasons of league history for the playground
- Respect data-source terms; keep the public repo licence-safe
- Free where possible; a seam for one cheap paid xG feed later

## Source landscape (verified 2026-09-25)

See `docs/data_sources.md` for the catalog. Findings that shaped the design:

- **ESPN's site API** is the workhorse: box score, lineups with substitutions, key events,
  attendance, referee, odds and the league table in one summary call. No key. Works from
  cloud IPs only with a non-browser User-Agent. Date-range scoreboards return 400, so
  the nightly job asks per date. Cup coverage looked patchy in probes.
- **football-data.co.uk** added team xG (`HxG`, `AxG`) to the Scottish Premiership CSV
  for 2026-27, alongside shots, corners, cards and closing odds. Free, league only,
  posted within a day or two of the match — hence the xG retry window in Stage 1.
- **football-data.org** puts Scotland on a paid tier and has no xG. **Understat** has no
  Scotland. **FBref** forbids tools built on its data and blocks scripts. Sportmonks and
  API-Football need keys; their xG for the Premiership is paid or unverified.
- **TheSportsDB** free key is fine for upcoming fixtures but truncates lists to 5 rows.

## Architecture

```
                 ┌───────────────────────────────────────────────────────┐
 sources         │ site.api.espn.com    football-data.co.uk   thesportsdb │
                 └──────────────────────────┬────────────────────────────┘
 ingest          steelmen.io  (cache-first clients, retry/backoff, one User-Agent)
                                            │  → data/raw/<source>/…          (gitignored)
 normalize       steelmen.clean  (ESPN summary → match/lineups/events/stats/table;
                                  football-data row → xg/market/stats blocks)
 derive          steelmen.metrics  (form, market, xG/xPts, discipline)
                 steelmen.statpack (one JSON per match, schema_version, validator)
                 steelmen.viz      (match figure, season form chart)
                                            │  → data/processed/motherwell/…   (committed)
                                            │  → reports/motherwell/figures/…  (committed)
 narrate         Claude Routines (docs/ROUTINE_*.md) → reports/motherwell/…
 publish         scripts/build_site.py → GitHub Pages
```

Principles:

1. **Cache-first ingest.** Every fetch is keyed (source, endpoint, date/params) and lands
   verbatim in `data/raw/`. Re-runs read from disk. The in-progress football-data season
   file is cache-busted per day so the nightly job sees this week's rows.
2. **Raw is immutable, processed is precious.** Only `data/processed/` is committed.
3. **Notebooks never fetch.** All network access goes through `steelmen.io`.
4. **No silent failures.** Parsers validate expected fields and raise `ParseError`; the
   stat pack validator is the drift alarm for the LLM handoff.
5. **Motherwell-relative everywhere.** `home_away`, `result`, `score`, lineups and events
   are labelled `motherwell` / `opponent`, so downstream code never re-derives sides.

## Stage 1 details (`scripts/nightly_motherwell.py`)

- Scans yesterday and `--days-back` earlier UK dates, oldest first, across every league
  code in `steelmen.io.espn.LEAGUES`. The first league to report an event id wins.
- For each finished Motherwell match: ESPN summary → football-data row (league only) →
  provisional match-log upsert → stat pack → final upsert → match figure.
- Idempotent: an existing pack is skipped unless `--force`, or it is a league pack
  without xG and the match is ≤ 4 days old (`XG_RETRY_DAYS`).
- Always refreshes `fixtures.csv` (ESPN schedule + TheSportsDB) and `table.csv` (from
  the newest cached league summary's standings block).
- Prints `RESULT:` lines that the workflow folds into the commit message. No-op runs
  leave the tree clean, so the commit step naturally skips them.

## Stat pack schema (v1)

Top-level keys: `schema_version`, `generated_at`, `sources`, `season`, `match`,
`lineups`, `events`, `team_stats`, `player_lines`, `xg`, `market`, `footballdata_stats`,
`rolling` (`last5_all`, `last5_league`, `season_all`, `season_league`), `table`,
`figure`, `notes`. Target ≤ 30 KB. `table` is the standings as fetched (the morning after, for nightly runs; `table.as_of` says so). `xg.available`, `market.available` and
`footballdata_stats.available` are booleans the Routines branch on.

## Testing

- `tests/fixtures/` holds trimmed real ESPN payloads (Motherwell 0-4 Aberdeen,
  Dundee 2-1 Motherwell, a gameday and an empty scoreboard, the team schedule) and a
  football-data sample with Motherwell's 2026-27 rows.
- Parsers, metrics, stat packs, the match log, the cache, the site builder and the
  nightly orchestration (fetchers monkeypatched, clock frozen) run offline in CI.
- Live checks sit behind `pytest -m live`, runnable from the nightly workflow.

## Phased plan

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 1 | `io.espn` + `clean.match`; committed season match log | Done |
| 2 | Stat packs + match figures + match-report Routine | Done (Routine created disabled) |
| 3 | football-data.co.uk xG and market blocks; 5-season history backfill | Done |
| 4 | Previews and monthly reviews (Routines + prompts) | Prompts done; Routines created disabled |
| 5 | Site with season page | Done |
| 6 | Paid xG provider for cups / per-shot data via `XGProvider` | Not started |
| 7 | Player-usage tables across the season (from `lineups.minutes_est`) | Not started |

## Environments

- **GitHub Actions** does all fetching. **Claude Routine sessions** need only GitHub
  access: they read committed files and push reports. If a Routine environment cannot
  reach `site.api.espn.com`, that is expected and fine.
- Local runs: `python scripts/nightly_motherwell.py --days-back 7` after a match.
