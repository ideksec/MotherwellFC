# Data Sources

Document every data source used in this repo. Keep this file current.

## Source catalog

| Source | URL | Access method | Refresh cadence | License / ToS | Local-only? |
|--------|-----|---------------|-----------------|---------------|-------------|
| ESPN soccer site API | site.api.espn.com/apis/site/v2/sports/soccer/{league}/… | Undocumented JSON, no key. Plain `requests` with a non-browser User-Agent (browser UAs get an Akamai 403 from cloud IPs). Single-date scoreboards only. | Nightly during the season | Undocumented, no stated terms; treat like MLB Stats API: personal, non-bulk, never redistribute payloads | Yes (`data/raw/espn/`) — only per-match aggregates reach `processed/` |
| football-data.co.uk | football-data.co.uk/mmz4281/{season}/SC0.csv | Season CSV download | Weekly (after each round) | Free for personal use; cite the site. Redistribution of small derived tables with attribution is common practice | Trimmed columns committed to `data/processed/spfl/` and the history file |
| TheSportsDB | thesportsdb.com/api/v1/json/3/… | JSON with the public test key `3` | Nightly | Free tier truncates lists to 5 rows; Premium removes that. Attribution requested | Yes (`data/raw/thesportsdb/`) — fixtures rows reach `fixtures.csv` |
| Match reports / news (BBC Sport, Motherwell FC, Daily Record, The Herald) | various | Web search from the Routines; qualitative facts quoted with inline links | As needed | News content; quote with attribution, no bulk scraping, never a statistic | n/a (cited in reports only) |

League codes used on ESPN: `sco.1` Premiership, `sco.tennents` League Cup, `sco.cis`
Scottish Cup, `uefa.europa.conf_qual` / `uefa.europa_qual` European qualifying,
`uefa.europa.conf` / `uefa.europa` group and knockout stages, `club.friendly` friendlies.
Cup coverage on ESPN was patchy in September 2026 probes; when a cup match is missing
the nightly job simply finds nothing and the fixture still shows via TheSportsDB.

## What each source contributes to a stat pack

| Block | Source |
|-------|--------|
| match (score, venue, attendance, referee, competition) | ESPN summary header + gameInfo |
| lineups (formation, starters, bench, sub minutes → `minutes_est`) | ESPN rosters |
| events (goals, penalties, cards, subs, stoppage-time minutes) | ESPN keyEvents |
| team_stats (possession, shots, SOT, corners, fouls, cards, passes, tackles) | ESPN boxscore |
| player_lines (scorers, assists, most shots, booked) | ESPN roster stats |
| table (Premiership standings after the match) | ESPN standings block |
| xg (team xG for/against, xPts) | football-data.co.uk `HxG` / `AxG` — league only |
| market (Bet365 pre-match odds → implied probabilities, points vs market) | football-data.co.uk |
| footballdata_stats (shots, corners, cards, half-time score; cross-check) | football-data.co.uk |
| fixtures.csv | ESPN team schedule with `?fixture=true` (upcoming, league) + TheSportsDB next events (all competitions) |

## Automated pulls

The nightly workflow (`.github/workflows/nightly-motherwell.yml`) pulls each finished
Motherwell match from ESPN and the current season's football-data.co.uk CSV on a GitHub
Actions runner. Raw payloads stay on the runner (ephemeral, never committed); only the
compact per-match stat pack, the match-log row, the match figure, `fixtures.csv` and
`table.csv` land in the repo.

## Paid options (researched 2026-09-25, not in use)

| Provider | Premiership xG? | Price | Notes |
|----------|-----------------|-------|-------|
| Sportmonks | Yes, as an add-on (league only, no cups) | Starter + xG ≈ €39–48/mo | Free plan includes the Premiership (fixtures, lineups, events, stats) without xG |
| API-Football | `expected_goals` field exists; Premiership coverage unverified | Pro $19/mo | Verify with a free key on a 2024 fixture before paying |
| FootyStats | Team xG incl. cups | Hobby £29.99/mo | No lineups or player stats |
| football-data.org | No xG | Tier 2 €49/mo | Scotland is a paid tier |
| TheSportsDB Premium | Unverified | $9/mo | Removes the 5-row truncation; most redistribution-friendly |
| Opta, StatsBomb, Wyscout | Yes | Enterprise | Out of scope |

`steelmen.io.providers.XGProvider` is the seam: a paid feed becomes another class
returning `{home, away, shots}` and the stat pack's `xg.source` label changes.

## Notes

- **raw/** and **interim/** are gitignored — never committed.
- **processed/** may contain small, reproducible derivatives only.
- Always record how a dataset was obtained so runs are reproducible.
- Check each source's terms before automated access.
