# Motherwell Match Preview — Routine Instructions (Stage 2b)

Instructions for the scheduled Claude session that writes a match-day preview.

## Mission and hard constraints

1. **Every number comes from committed files**: `data/processed/motherwell/fixtures.csv`
   (today's fixture), `matchlog_{season}.csv` and `history_matches.csv` (form and
   head-to-head), `table.csv` (positions), `data/processed/spfl/league_{season}.csv`
   (the opponent's league results this season and last), and the most recent stat
   packs (`rolling` blocks, lineups used).
2. **Never invent a stat.** No searched statistics. Web search may add team news,
   injuries, suspensions, quotes and the opposition's narrative, with inline links.
3. Do not fetch data from APIs.

## Find the work

1. Pull latest `main`.
2. Read `fixtures.csv`. If no row has `date` equal to today (Europe/London), **end
   quietly** — no commit, no notification.
3. Expected preview path: `reports/motherwell/previews/{date}_{vs|at}-{opponent-slug}.md`
   where the slug follows `steelmen.utils.teams.team_slug` (known Premiership clubs:
   aberdeen, celtic, dundee, dundee-utd, falkirk, hearts, hibs, kilmarnock, rangers,
   st-johnstone, st-mirren; otherwise lowercase-hyphenated name). If the file already
   exists, end quietly.

## Preview structure

- **Title**: fixture-first, e.g. "Motherwell v Celtic: what the numbers say before kick-off".
- **Blockquote**: `> Date: {date}` and `> Author: MotherwellFC match pipeline`.
- **Question**: "What should 'Well fans expect, and what would a good performance look like?"
- **Data**: the files used, one line.
- **Results** — three themed sections:
  1. **Motherwell's form** — last 5 league results, points, xGD and xPts vs points from
     the match log; who has been scoring and creating from recent packs' `player_lines`.
  2. **The opposition** — their league results this season from `league_{season}.csv`
     (record, goals, xG if present), and the head-to-head from `history_matches.csv`
     (last five meetings, results).
  3. **What to watch** — two or three concrete, data-backed things (set pieces from
     corner counts, discipline, home/away splits), plus team news from search with links.
- **Limitations**: small samples, no lineups yet, vendor stats.
- **Takeaway**: 2–3 sentences: a fair expectation and what a good night looks like.

## Voice, commit, failure posture

As in `docs/ROUTINE_MATCH_REPORT.md`. Commit message:
`Preview: {date} {vs|at} {Opponent} [skip ci]`. End with a 2-sentence takeaway for the
push notification. Stop on anything inconsistent; never fabricate; never force-push.
