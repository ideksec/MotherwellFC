# CLAUDE.md — conventions for Claude sessions in this repo

This is the Motherwell FC analytics lab. Read `spec.md` for the operating spec. The
rules below apply to every session, whether a scheduled Routine or an interactive one.

## Non-negotiables

- **Every number traces to a committed file.** Stat packs under
  `data/processed/motherwell/statpacks/`, the match log `matchlog_{season}.csv`, the
  history `history_matches.csv`, `table.csv`, `fixtures.csv`, `data/processed/spfl/`.
  Never invent, estimate, or recall a statistic from memory. If it isn't in a file,
  write around it or say it's missing.
- **Web search adds colour, not numbers.** Team news, quotes, opposition storylines are
  fine with inline source links. A searched statistic is not.
- **Never commit secrets.** No API keys, no tokens, no `.env` contents.
- **Never commit raw payloads.** `data/raw/` and `data/interim/` stay gitignored.
- **Do not skip, disable or weaken tests** to get green.

## Where things live

- Package code: `src/steelmen/` (io → clean → metrics → statpack → viz). Reusable logic
  goes here, with a test under `tests/`.
- Scripts: `scripts/` — `nightly_motherwell.py` (Stage 1), `backfill_history.py`,
  `build_site.py`.
- Reports: `reports/motherwell/{matches,previews,monthly}/` with figures in
  `reports/motherwell/figures/`. Filenames follow `steelmen.statpack.report_filename`.
- Notebooks: `notebooks/analysis/` from `notebooks/templates/analysis_template.ipynb`.
  Notebooks never fetch from the network.
- Routine prompts: `docs/ROUTINE_MATCH_REPORT.md`, `docs/ROUTINE_PREVIEW.md`,
  `docs/ROUTINE_MONTHLY.md`. Analysis how-to: `docs/analysis_guide.md`.

## Voice for fan-facing writing

Analytical fan. Written for Motherwell supporters, third person ("Motherwell", never
"we"), thesis-first section headers, numbers woven into sentences, small-sample
humility, no filler enthusiasm, no press-release tone. Honest about bad performances.

## Before you push

```bash
ruff check .
pytest
python scripts/build_site.py --out site   # when reports or data changed
```

Routine commits go straight to `main` with `[skip ci]` in the subject. Development work
goes on a branch and through a pull request.

## Identity constants

Motherwell: ESPN team id `266`, TheSportsDB id `133640`, football-data.co.uk name
`Motherwell`. Time zone `Europe/London`. Seasons run July–June (`2026-27`).
