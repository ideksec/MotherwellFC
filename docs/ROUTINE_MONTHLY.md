# Motherwell Monthly Review — Routine Instructions (Stage 2c)

Instructions for the scheduled Claude session that writes the month-in-numbers review
on the first of each month (covering the previous calendar month).

## Mission and hard constraints

1. **Every number comes from committed files**: `matchlog_{season}.csv`, the month's
   stat packs, `history_matches.csv` (for "compared with previous seasons"),
   `table.csv`, `data/processed/spfl/league_{season}.csv`.
2. **Never invent a stat.** Web search only for context (managerial changes, injuries,
   transfer news) with inline links.
3. Figures are rendered with the package, never hand-drawn: use
   `steelmen.viz.form_figure` and matplotlib via `steelmen.viz.palette.apply_style`,
   saved to `reports/motherwell/figures/{YYYY-MM}_{slug}.png`, and embedded.

## Find the work

1. Pull latest `main`.
2. Target month = the previous calendar month. Expected path:
   `reports/motherwell/monthly/{YYYY-MM}.md`. If it exists, end quietly.
3. If the match log has no matches in that month (June/July off-season), end quietly.

## Review structure

- **Title**: e.g. "September in numbers: three defeats, an xG line that says two".
- **Blockquote**: `> Date: {first of this month}` and `> Author: MotherwellFC match pipeline`.
- **Question**: "What did the month tell us, and what should change?"
- **Data**: files and the month window, one line.
- **Results** — themed sections with figures:
  1. **Results and table** — the month's W-D-L, points, PPG, goals; table movement
     (`table.csv` now; the stat packs' `table.motherwell` at month start vs end).
  2. **Performance vs results** — xG for/against, xGD, xPts vs points, shots and SOT
     per match; a figure of cumulative points vs xPts (`form_figure`).
  3. **Squad usage** — minutes (from `lineups.*.minutes_est`, labelled estimates),
     starters by match, subs used, who scored and assisted, bookings.
  4. **Market vs reality** — implied probabilities vs outcomes, `points_vs_market`
     summed over the month, the biggest upset either way.
  5. **Set pieces and discipline** — corners for/against, cards, fouls, referees.
  6. **Compared with previous seasons** — the same month in `history_matches.csv`
     (points, goals) for the last five seasons.
- **Limitations**, **Takeaway** (3–5 sentences), **Next iteration** (the fixtures
  ahead from `fixtures.csv`).

## Voice, commit, failure posture

As in `docs/ROUTINE_MATCH_REPORT.md`. Commit message:
`Monthly review: {YYYY-MM} [skip ci]` (commit the figures in the same commit). End with a
3-sentence takeaway for the push notification. Stop on anything inconsistent; never
fabricate; never force-push.
