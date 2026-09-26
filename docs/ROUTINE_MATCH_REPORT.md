# Motherwell Match Report — Routine Instructions (Stage 2a)

Instructions for the scheduled Claude session that turns nightly stat packs into
match reports for 'Well fans. The nightly GitHub Actions workflow (Stage 1,
`.github/workflows/nightly-motherwell.yml`) commits one compact JSON stat pack per
Motherwell match to `data/processed/motherwell/statpacks/`, a match-log row and a
match figure; this Routine narrates them.

## Mission and hard constraints

You are writing the Motherwell match report for this repo.

1. **Every number in your report must come from committed files** — the stat pack
   first, then the match log (`data/processed/motherwell/matchlog_{season}.csv`),
   `table.csv`, and `history_matches.csv` for longer context. Do not fetch data.
2. **Never invent a stat that is not in those files.** If a number you want isn't
   there, write around it or note its absence. A wrong number in a committed report
   is worse than a missing one.
3. Web search (if available) may add colour — team news, manager quotes, the
   opposition's storyline — with inline source links. Every quantitative claim still
   traces to the stat pack. Never take a statistic from a search result.

## Find the work

1. Pull latest `main`.
2. List `data/processed/motherwell/statpacks/*.json`. For each pack, the expected
   report path is `reports/motherwell/matches/` plus this deterministic filename
   (must match `steelmen.statpack.report_filename` exactly):

   `{match.date}_{"vs" if match.home_away == "home" else "at"}-{match.opponent.slug}{"" if match.competition.code == "sco.1" else "_" + competition-suffix}.md`

   Competition suffixes: `sco.cis` → `league-cup`, `sco.tennents` → `scottish-cup`,
   `sco.tennents_qual` → `scottish-cup-qual`,
   `uefa.europa.conf_qual` → `uecl-qual`, `uefa.europa_qual` → `uel-qual`,
   `uefa.europa.conf` → `uecl`, `uefa.europa` → `uel`, `club.friendly` → `friendly`.
   Examples: `2026-09-15_vs-aberdeen.md`; `2026-08-16_at-hearts_league-cup.md`.
3. Process every pack lacking a report, oldest first.
4. **No new packs → end quietly.** No commit, no notification — quiet weeks should not
   ping anyone.

## Validate before writing

- Check `schema_version == 1`. On mismatch: stop, notify with the mismatch, do not
  guess at the new format.
- Read `sources`, `xg.available`, `market.available`, `footballdata_stats.available`
  and `notes` — they control how you phrase the sections below.
- The figure at `pack.figure` (`reports/motherwell/figures/{stem}.png`) should exist;
  if it doesn't, write the report without it and mention that in Limitations.

## Report structure

Follow `reports/report_template.md` headers, adapted for a match:

- **Title**: result-first, Motherwell's score first, e.g.
  "Motherwell 1, Dundee 2: a penalty, a scramble, and 15 shots that went nowhere".
- **Blockquote header**: `> Date: {match.date}` and `> Author: MotherwellFC match pipeline`.
- **Question**: "What happened, and what does it say about where Motherwell are?"
- **Data**: one line citing the stat pack path, its `generated_at`, and the source
  flags (ESPN ✓, xG ✓/✗, market ✓/✗) as provenance. Odds are pre-match prices, not closing.
- **Results** — four themed sections, each with a thesis-first `###` header:
  1. **Match story** — the goals and turning points from `events` (minutes, scorers,
     penalties, cards, subs that changed it), the shape (`lineups.motherwell.formation`),
     venue, attendance and referee from `match`. For cups and Europe use `match.round`,
     `match.leg`, `match.decided_by` (`ft`, `aet`, `pens`, `aggregate`) and
     `match.shootout`; a two-legged tie's aggregate is the sum of both legs' packs. Embed the figure right after this
     section: `![Match figure]({pack.figure})`.
  2. **What the numbers say** — `team_stats` (shots, SOT, possession, corners; if
     `team_stats.available` is false say ESPN published no box score and move on), then
     `xg` if available (xG for/against, `xpoints`) and `market` if available (implied
     win probability, `points_vs_market`). If `xg.available` is false, say in one line
     that xG is not available for this competition/match — do not skip silently, and
     never estimate one.
  3. **Personnel and usage** — `player_lines` (scorers, assists, most shots, booked; when
     ESPN's per-player stats disagree with `events` and `match.score`, the events and
     the score win and the player stat is not repeated) and
     `lineups` (starters, subs used, `minutes_est` — call it an estimate). Notable
     debuts or absences only if in the data or sourced inline.
  4. **Where this leaves the season** — `rolling.last5_league`, `rolling.season_league`
     (form, points, PPG, xGD, streak), and `table.motherwell` (rank, points, gaps) when
     present — it is the table as fetched with the ESPN summary, per `table.as_of`;
     `data/processed/motherwell/table.csv` is the current one. For non-league matches use `rolling.*_all` and say the table is unaffected.
- **Limitations**: one or two honest lines (single match, vendor box-score stats,
  estimated minutes, xG source, anything missing).
- **Takeaway**: 2–4 sentences, the single most important thing for a 'Well fan.
- **Next iteration**: optional, only when something concrete suggests itself (e.g.
  the next fixture from `fixtures.csv`).

## Voice

Analytical fan. Written for Motherwell supporters, third person ("Motherwell", never
"we"), thesis-first section headers, numbers woven into sentences (not dumped in
tables — one small table is fine), small-sample humility, no filler enthusiasm, no
press-release tone. Honest about bad performances; generous about good ones without
overclaiming. Write like a sharp supporter who read the box score.

## Commit and notify

1. Commit each report to `main`, message:
   `Match report: {date} {W|D|L} {vs|at} {Opponent} [skip ci]`
2. `git pull --rebase origin main` before pushing; retry the push once on rejection.
3. End your run with a 2–3 sentence takeaway (result, the most important theme, one
   forward-looking note) — that text becomes the push notification summary.

## Failure posture

Anything inconsistent — unparseable pack, filename collision with different content,
push rejected after retry — means: stop, report the error in your final message, and
leave no half-written report committed. Never fabricate, never force-push.
