# TASKS: PR-sized checklist for Codex implementation

This checklist is designed to be executed as small, reviewable increments. Each section can be a PR.

---

## PR 1 — Repo reconnaissance + scaffolding
- [ ] Identify current entrypoint(s): CLI/script used by the pythagorean simulator.
- [ ] Locate current data loaders for standings/schedule and any team metadata.
- [ ] Add a `sim/` package (or follow repo conventions) with submodules:
  - [ ] `sim/model.py` (margin model)
  - [ ] `sim/season.py` (regular season sim + bookkeeping)
  - [ ] `sim/tiebreak.py` (approx conference seeding)
  - [ ] `sim/playin.py` (play-in bracket)
  - [ ] `sim/lottery.py` (slotting + draw)
  - [ ] `sim/report.py` (aggregation + query outputs)
- [ ] Add basic type hints and docstrings.
- [ ] Add a top-level config object or dataclass for parameters (n_sims, seed, sigma, HCA, etc.).
- [ ] Ensure docker build/run still works after refactor (no behavior changes yet).

Acceptance:
- Code compiles, tests still pass (if any), container still runs.

---

## PR 2 — Implement MarginModel (net rating -> margin)
- [ ] Implement `MarginModel`:
  - Inputs: `net_ratings`, `poss_per_game`, `hca_points`, `sigma_margin`, `rng`
  - Method: `simulate_game(home, away) -> (winner_team_id, margin_float)`
  - `mu = (NR_home - NR_away)*(poss/100) + hca`
  - `margin ~ Normal(mu, sigma)`
- [ ] Add deterministic behavior under a fixed seed.
- [ ] Unit test:
  - [ ] With `sigma=0`, margin equals mu and winner matches sign(mu).

Acceptance:
- Unit test green; model returns consistent outputs with fixed seed.

---

## PR 3 — Regular-season simulation state + bookkeeping
- [ ] Implement `SeasonState` data structure:
  - wins/losses
  - conf wins/losses
  - head-to-head wins/games (sparse dict keyed by (team, opp))
  - ptdiff accumulator (float)
- [ ] Write `simulate_regular_season(state, schedule, model, team_meta)`:
  - iterates remaining games (sorted by date/time)
  - updates standings and all bookkeeping
  - ptdiff updates: add margin to home, subtract from away
- [ ] Add a small unit test using a toy schedule to verify updates.

Acceptance:
- Regular-season sim produces correct W/L and h2h counts on toy data.

---

## PR 4 — Approximate conference seeding tiebreaks
- [ ] Implement `rank_conference_approx(teams, state, rng)`:
  - Sort primarily by win%
  - For each win%-tie group, compute for each team:
    - h2h win% within the tied group
    - conference win%
    - ptdiff
  - Sort by those metrics; if still tied, rng shuffle
- [ ] Provide `seed_conferences(state, team_meta, rng)` returning ordered lists for East and West.
- [ ] Unit tests:
  - [ ] A beats B head-to-head => A above B if same W/L
  - [ ] If h2h equal, higher conf win% wins
  - [ ] If still equal, higher ptdiff wins

Acceptance:
- Seeding order matches expectations in synthetic tests.

---

## PR 5 — Play-in simulation
- [ ] Implement `simulate_playin(seeds_1_to_10, model, rng)` for each conference:
  - Game A: 7 hosts 8
  - Game B: 9 hosts 10
  - Final: loser(A) hosts winner(B)
- [ ] Return:
  - playoff teams for the conference (seeds 1–6 + play-in winners 7/8)
  - eliminated play-in teams (2 teams)
- [ ] Unit test with deterministic outcomes (sigma=0, mu large for winners).

Acceptance:
- Correct teams advance/eliminate given deterministic model conditions.

---

## PR 6 — Lottery slotting + lottery draw simulation
- [ ] Implement `lottery_slots(lottery_teams, state, rng)`:
  - Determine each team’s record (wins, losses)
  - Sort worst-to-best by win%
  - Randomize within record ties each run
  - Return slots list length 14
- [ ] Implement `draw_lottery_top4(slots, rng)` using ticket counts:
  - ticket_counts = [140,140,140,125,105,90,75,60,45,30,20,15,10,5]
  - Build 1000 tickets -> team mapping
  - Draw until 4 unique winners (redraw duplicates)
  - Return top4 winners in order
- [ ] Implement `assign_picks(slots, top4)`:
  - picks 1–4 from top4 winners
  - remaining teams assigned picks 5–14 in slot order (excluding top4)
- [ ] Unit test:
  - [ ] Top4 unique
  - [ ] Pick set is exactly 14 teams
  - [ ] Distribution sanity check (optional, probabilistic test with tolerance)

Acceptance:
- Correct pick assignment logic; lottery draw behaves as specified.

---

## PR 7 — Monte Carlo driver + reporting (pick odds queries)
- [ ] Implement `simulate_n_runs(n_sims, inputs..., params...)`:
  - For each run:
    - init state
    - simulate remaining regular season
    - seed conferences
    - simulate play-in (both conferences)
    - build 14 lottery teams
    - create slots
    - run lottery draw + assign picks
    - update `pick_counts[team][pick]`
- [ ] Implement reporting helpers:
  - `pick_probabilities(team) -> dict`
  - `p_top_k(team, k)` (parameterized)
  - `expected_pick(team)`
  - Export to JSON/CSV/markdown (match repo style)
- [ ] Add an end-to-end smoke test on a small toy league or a reduced schedule subset.

Acceptance:
- CLI produces a pick odds table; smoke test passes.

---

## PR 8 — Integrate with existing CLI + docs + container
- [ ] Make new simulator the default path; keep pythagorean option if easy via flag.
- [ ] Add README snippet on usage and parameters:
  - n_sims, seed, sigma, HCA, poss_per_game, top_k
- [ ] Ensure docker container entrypoint runs the new path successfully with default params.
- [ ] Confirm runtime is reasonable for 10k sims in container.

Acceptance:
- Running the container yields pick odds output without manual steps.

---

## Optional PR 9 — Calibration helpers (nice-to-have)
- [ ] Add a simple backtest harness to tune sigma/hca using past games.
- [ ] Add logging of confidence intervals or standard errors for probabilities.

Acceptance:
- Optional; not required for initial functional correctness.

