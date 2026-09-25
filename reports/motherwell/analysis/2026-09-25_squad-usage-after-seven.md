# Squad usage after seven: six ever-presents, one striker by committee, and Lowry doing the shooting

> Date: 2026-09-25
> Author: MotherwellFC (compiled with Claude)

## Question

Who has actually been playing for Motherwell in the first seven Premiership matches of 2026-27, and where is the attacking load sitting?

## Hypothesis

A settled back five and midfield, with the forward positions rotated, and the shot volume concentrated in one or two players rather than spread across the front line.

## Data

- Source: the seven committed stat packs in `data/processed/motherwell/statpacks/` (ESPN lineups and per-player box-score stats), aggregated by `steelmen.metrics.usage.squad_usage`.
- Time window: 2026-08-02 to 2026-09-19, league matches only.
- Minutes are `minutes_est` from the packs: estimated from substitution times, 90 for an unsubbed starter, no stoppage time. Every minute available is 630.
- Known limitations: vendor per-player stats; no cup matches in the packs yet; ESPN assists are its own attribution.

## Method

Aggregate each player's appearances, starts, estimated minutes, goals, assists, shots and shots on target across the seven packs, and normalise shots per 90 estimated minutes. Figure rendered with `steelmen.viz.usage_figure`.

## Results

### Six players have started every match, and five of them have barely come off

Alex Paulsen has played all 630 estimated minutes. Martin Moormann (605), Lukas Fadinger (599), Emmanuel Longelo (566) and Tom Sparrow (537) have started all seven too; Tawanda Maswanhise has also appeared in all seven, with six starts and 484 minutes. That is the spine: goalkeeper, a centre-back, both full-backs, a midfielder and a wide forward. Alexander Lowry has appeared in all seven as well, but only five from the start, for 452 minutes.

![Squad usage](reports/motherwell/figures/2026-09-25_squad-usage-after-seven.png)

The other centre-back slot and the front line are where the rotation lives. Jake Girdwood-Reich (four starts, 406 minutes) and Jamie Knight-Lebel (three starts, 249) have shared the second centre-back role. Up front, Regan Charles-Cook (four starts, 291 minutes), Ibrahim Sa'Id (five starts, 412), Jardell Kanga (two starts, 233), Seb Palmer-Houlden (two starts, 231) and Willy Gabriel Vogt Veigantes (two starts, 191) have all had turns. Twenty-four players have been used; four more have sat on the bench without coming on.

### The shooting runs through Lowry

Lowry has 21 shots and 10 on target in 452 minutes, 4.18 shots per 90, and both of his goals. The next-highest shot counts are Maswanhise (15 shots, 5 on target, 2.79 per 90), Longelo (12, from left-back, 1.91 per 90), Fadinger (9, 6 on target) and Palmer-Houlden (9 in 231 minutes, 3.51 per 90). Nobody else has more than six. Across the squad that is 102 shots and 33 on target for 9 goals.

The forwards' output is thin relative to their minutes: Charles-Cook 6 shots and 1 goal in 291 minutes, Sa'Id 5 shots and 1 goal in 412, Kanga 4 shots and 1 goal in 233. Palmer-Houlden's 3.51 shots per 90 is the exception and has come mostly from the bench. Among short cameos, Eythor Bjørgolfsson has 3 shots (2 on target) in 74 minutes and Dylan Levitt 2 shots and a goal in 70.

### Creation is coming from the full-backs and Maswanhise

Sparrow has two assists from right-back, Maswanhise two, Lowry one and Dylan Williams one. No striker has an assist. Bookings, per the packs' player stats, are spread thinly: two each for Moormann, Fadinger and Sparrow, one each for Longelo, Palmer-Houlden, Oscar Priestman, Williams and Stephen O'Donnell, and no red cards.

### Shape

The formation has moved between 4-4-2 (Hibernian), 4-2-3-1 (Falkirk, St Mirren, Rangers, Dundee) and 4-2-2-2 (Dundee United, Aberdeen), which explains the rotation up front more than form does: two-striker shapes have used Kanga and Palmer-Houlden, the 4-2-3-1 has used a lone forward with Lowry behind.

## Limitations

Seven matches. Minutes are estimates and ignore stoppage time, so ever-presents are slightly undercounted relative to reality. ESPN's per-player shot and assist counts are one vendor's; football-data.co.uk's team-level shot totals for the same matches differ slightly in places. The packs hold league matches only.

## Takeaway

The defence and Fadinger pick themselves; the attack does not. Lowry takes a fifth of the team's shots and has scored two of its nine goals, while the five players who have shared the striker minutes have four goals between them from 27 shots. Over the last three matches the team has scored once, and this table says why: the volume runs through one attacking midfielder and two full-backs, not through the front line.

## Next iteration

Re-run after the Celtic match on 11 October, and add the cup matches once the packs cover them. A per-90 view of shots on target per player, and a comparison of Palmer-Houlden's and Charles-Cook's starts, would be the natural follow-up.
