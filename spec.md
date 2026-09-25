# spec.md — Motherwell FC Analytics Lab (Framework)

## Purpose
A long-lived "lab" repo for Motherwell FC analysis, in two halves:

1. **Scheduled** — pull each match's stats, package them, and run automated and agentic
   analysis that becomes regular fan-facing reports.
2. **Playground** — deep, question-driven analysis of Motherwell (notebooks, reports,
   reusable modules) that feeds longer pieces and the monthly reviews.

The intent is content and analysis for Motherwell fans: honest, numbers-first, written
for people who care about the club.

Non-goals:
- perfect engineering from day one
- committing large datasets or raw API payloads to git
- scraping that violates terms of service
- storing secrets or tokens in the repo

---

## Operating principles
1. One question → one primary artifact (notebook, report, or app).
2. Reproducible by default: results must be recreatable from code + documented data steps.
3. Separation of concerns: data, code, analysis, and outputs are clearly separated.
4. Publishable by default: the repo is public, so everything committed should be clean
   and defensible.
5. Messy is allowed, but contained: experiments live in `scratch/` and are promoted or
   removed.
6. Every number traces to a committed file. Reports cite the stat pack or CSV they were
   written from; the LLM stages never invent statistics.

---

## Canonical repository structure

```
MotherwellFC/
├── README.md, spec.md, CLAUDE.md
├── docs/                  # glossary, sources, pipeline design, Routine prompts, analysis guide
├── data/
│   ├── raw/               # local-only pulls; gitignored
│   ├── interim/           # optional staging; gitignored
│   └── processed/         # small reproducible derivatives only
│       ├── motherwell/    # matchlog_{season}.csv, statpacks/, fixtures.csv, table.csv, history
│       └── spfl/          # league_{season}.csv
├── notebooks/             # templates/, exploration/, analysis/, modeling/, viz/
├── reports/
│   ├── motherwell/        # matches/, previews/, monthly/, figures/
│   ├── publishable/
│   └── report_template.md
├── src/steelmen/          # io/, clean/, metrics/, statpack.py, viz/, utils/
├── scripts/               # nightly_motherwell.py, backfill_history.py, build_site.py
├── apps/                  # dashboards/, services/
├── tests/                 # fixtures/ + pytest
└── scratch/_archive/
```

Notes:
- Keep the repo root quiet; most churn should be below it.
- `docs/` contains stable knowledge you intend to reuse.
- `scratch/` is explicitly temporary.

---

## The match pipeline (scheduled half)

| Stage | Runs | Produces | Owner |
|-------|------|----------|-------|
| 1. Stat pack | GitHub Actions, 03:00 UTC daily | `data/processed/motherwell/statpacks/{date}_{espn_id}.json`, match-log row, `reports/motherwell/figures/{stem}.png`, `fixtures.csv`, `table.csv` | `scripts/nightly_motherwell.py` (deterministic) |
| 2a. Match report | Claude Routine, ~08:00 UK daily | `reports/motherwell/matches/{stem}.md` | `docs/ROUTINE_MATCH_REPORT.md` |
| 2b. Preview | Claude Routine, ~09:00 UK on match days | `reports/motherwell/previews/{date}_{vs|at}-{opp}.md` | `docs/ROUTINE_PREVIEW.md` |
| 2c. Monthly review | Claude Routine, 1st of the month | `reports/motherwell/monthly/{YYYY-MM}.md` + figures | `docs/ROUTINE_MONTHLY.md` |
| 3. Site | GitHub Actions on push + 11:00 UTC | GitHub Pages | `scripts/build_site.py` |

The filename stem `{date}_{vs|at}-{opponent-slug}[_{competition}]` is defined once in
`steelmen.statpack.report_filename` and shared by the stat pack, the figure, the report
and the site. Stat packs carry `schema_version`; the Routines stop on a mismatch.

Competitions covered: Scottish Premiership (`sco.1`), League Cup (`sco.tennents`),
Scottish Cup (`sco.cis`), European qualifiers and group/league stages, friendlies.
xG and market blocks only exist for Premiership matches (football-data.co.uk); other
competitions carry ESPN box-score stats only and the pack says so in `notes`.

---

## Notebook standards
Each notebook should include, at minimum:
- **Header:** question, datasets used, time window, assumptions
- **Method:** what was done (not every attempt)
- **Results:** minimal charts or tables that answer the question
- **Conclusion:** 5–10 sentences, limitations, next step

Naming: date prefix + short question identifier (`2026-09-25_xg_vs_results.ipynb`).
Avoid `final.ipynb`. If logic becomes reusable, extract it into `src/` and keep the
notebook narrative. Notebooks never fetch from the network — they read `data/processed/`.

---

## Reports standards
Reports are the durable "answers" worth keeping. Structure (`reports/report_template.md`):
Question · Hypothesis · Data · Method · Results · Limitations · Takeaway · Next iteration.

Voice for the automated reports: **analytical fan**. Written for Motherwell supporters,
third person ("Motherwell", not "we"), honest with the numbers, no press-release
enthusiasm, small-sample humility, no filler. Numbers woven into sentences, one or two
tables at most, the match figure embedded.

---

## Data policy
- Never commit large raw datasets. `data/raw/` and `data/interim/` are local cache only.
- Processed data may be committed only if it is small, reproducible, and licence-safe.
- Every source is documented in `docs/data_sources.md`: origin, access method, refresh
  cadence, licensing / ToS, what is local-only vs committed.
- ESPN payloads are never committed — only per-match aggregates (stat packs) and the
  match log. football-data.co.uk is free for personal use; we commit trimmed season
  tables with attribution.

---

## Quality and hygiene
- Consistent formatting and linting (`ruff`), tests for every parser and metric, fixture
  tests for the orchestration scripts, `TestCommittedReports` for the LLM output.
- Prefer deterministic runs; no silent failures — parsers validate and raise.
- Security: never commit secrets; environment variables locally; example env files with
  names only; assume history is public.

---

## Claude-first workflow
Claude accelerates implementation and writes the daily narrative; you own correctness
and judgment. Every request to Claude should specify goal, repo area, inputs and
outputs, constraints (no secrets, no large data, every number from committed files),
and acceptance criteria. Review outputs for secret leakage, uncontrolled network calls,
licensing or scraping risk, silent exceptions, invented statistics, unlabeled plots,
and unnecessary dependencies. `CLAUDE.md` carries the repo conventions for any session.

---

## Promotion rules
`scratch/` is temporary by design. Every item is promoted into `notebooks/` /
`reports/` / `src/`, archived under `scratch/_archive/`, or deleted. Timebox it.

---

## Public posture
This repo is public: write clearly and defensibly, avoid personal notes, keep data
handling explicit. Code and writing are MIT-licensed; data sources keep their own terms.
CI runs lint and tests on every push and pull request.

---

## Acceptance criteria
The framework is in place when:
- the folder structure exists and cache directories are gitignored
- the nightly workflow commits stat packs and the site publishes them
- at least one match report follows `docs/ROUTINE_MATCH_REPORT.md`
- at least one notebook follows the notebook standards using the package
