# SPEC: NBA Monte Carlo Simulator (Net Rating margin model)

## Entities
### Team
- `team_id` (string, stable key)
- `name` (string)
- `conference` ("E"|"W")
- optional: `division`

### Game
- `game_id` (string or int)
- `date` (date or sortable timestamp)
- `home_team_id`
- `away_team_id`

### SeasonState (per simulation run)
- standings:
  - `wins[team]`, `losses[team]`
  - `conf_wins[team]`, `conf_losses[team]`
- head-to-head:
  - `h2h_wins[(team, opp)]` integer
  - `h2h_games[(team, opp)]` integer
- `ptdiff[team]` float (seed from actual season PD if available; else 0)

## Parameters
- `n_sims` (int)
- `rng_seed` (int or None)
- `poss_per_game` (float; default 100)
- `hca_points` (float; configurable)
- `sigma_margin` (float; configurable)
- `tiebreak_mode = "approx"`
- `lottery_ticket_counts = [140,140,140,125,105,90,75,60,45,30,20,15,10,5]`

## Algorithms
### A) Regular season sim
For each remaining game in chronological order:
1. `mu = (NR_home - NR_away) * (poss/100) + hca`
2. sample `margin ~ Normal(mu, sigma)`
3. winner updates:
   - if margin > 0: home wins else away wins
4. update:
   - wins/losses
   - conference wins/losses if teams same conference
   - head-to-head wins/games for both directions
   - ptdiff: add margin to home, subtract margin from away

### B) Conference seeding (approx)
Sort teams within a conference by tuple key, descending:
1. win% = W/(W+L)
2. tie-break within groups:
   - compute h2h win% within tied group for each team
   - conference win%
   - ptdiff
   - random
Note: multi-team tie resolution can be done via sorting by these computed values; if still tied, random shuffle.

### C) Play-in
Given conference seeds 1..10:
- Simulate games per bracket rules; determine final seeds 7 and 8.
- Lottery teams are all non-playoff teams (14 total).

### D) Lottery positioning
Sort lottery teams by record (worst -> best). Randomize within record ties each run to create slots 1..14.

### E) Lottery draw
Sample 4 unique teams using ticket weights by slot, then assign picks 5..14 by remaining slots order.

## Outputs
- `pick_counts[team][1..14]`
- derived probabilities and expected pick

