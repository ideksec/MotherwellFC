# Glossary

Metric definitions used across the package, the stat packs and the reports.

## Results and form

- **Points**: W = 3, D = 1, L = 0. **PPG**: points per game.
- **Form string**: results oldest → newest, e.g. `WDLLW`. **Streak**: the current run of
  identical results, e.g. `L3`. **Unbeaten / winless runs**: consecutive non-losses /
  non-wins counted back from the latest match.
- **Goal difference (GD)**: goals for minus goals against.
- **Clean sheet**: opponent scored 0. **Failed to score**: Motherwell scored 0.

## Expected goals

- **xG** (expected goals): the sum, over a team's shots, of each shot's probability of
  scoring. Here it is *team* xG per match from football-data.co.uk (`HxG`, `AxG`);
  their model is not published, so treat values as one vendor's estimate.
- **xG difference (xGD)**: xG for minus xG against.
- **xPts** (expected points): the points a team would earn on average if goals were
  independent Poisson draws at the xG rates. `steelmen.metrics.xg.xpoints` sums win and
  draw probabilities over a 0–10 goal grid. Crude but standard for "did the result match
  the performance?".
- **Points vs xPts**: actual minus expected. Sustained positive values suggest finishing
  or luck running hot; negative suggests the opposite.

## Market

- **Implied probability**: 1 / decimal odds, normalised so home + draw + away = 1
  (proportional removal of the bookmaker's **overround**).
- **Expected points from the market**: 3 × P(win) + P(draw).
- **Points vs market**: actual points minus market expectation. "Beating the market".
- Odds are Bet365 pre-match prices from football-data.co.uk (`B365H/D/A`); `AvgH/D/A`
  are the market averages.

## Box score (ESPN)

- **Possession %**, **shots**, **shots on target (SOT)**, **blocked shots** (the team's own
  shots that were blocked — Dundee United's 2026-09-02 pack shows 9 for Motherwell against
  United's 5 total shots), **corners**,
  **fouls**, **offsides**, **saves**, **passes / accurate passes / pass %**, **tackles /
  tackles won**, **clearances**. Vendor-defined; use for within-match comparison, not
  cross-vendor comparison.
- **minutes_est**: minutes estimated from substitution clocks (90 for an unsubbed
  starter, no stoppage time). Labelled as an estimate everywhere.

## Match events

- Kinds: `goal`, `penalty_goal`, `own_goal`, `penalty_missed`, `yellow_card`,
  `second_yellow`, `red_card`, `substitution`, `var`.
- **minute** is numeric with stoppage added (90'+3' → 93); **minute_display** keeps the
  broadcast form.
