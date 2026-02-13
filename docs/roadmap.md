# Roadmap

## Phase 0: Wire-up and refactor (1–2 commits)
- Identify current entry points (CLI/script) for the pythagorean simulator.
- Introduce a `sim/` module (or similar) with clear boundaries:
  - `data/` loading + validation
  - `model/` game margin model
  - `season/` standings + tiebreaks + play-in
  - `lottery/` lottery positioning + draw
  - `report/` aggregation and output

## Phase 1: Regular-season margin simulation
- Implement `MarginModel`:
  - inputs: `net_ratings`, `poss_per_game`, `hca_points`, `sigma_margin`, RNG
  - function: `simulate_game(home, away) -> (winner, margin)`
- Implement schedule iteration per simulation run.
- Track standings W/L + conference W/L + head-to-head + ptdiff accumulator.

## Phase 2: Approximate tiebreak seeding
- Implement conference ranking function:
  - group by win%
  - within ties, apply:
    1) h2h within group
    2) conference win%
    3) ptdiff
    4) rng shuffle as last resort
- Produce seeds 1–15 for each conference.

## Phase 3: Play-in simulation
- Use seeds to select teams 7–10 per conference.
- Simulate play-in bracket to determine playoff participants.
- Derive lottery teams (14).

## Phase 4: Lottery positioning + lottery draw simulation
- Sort lottery teams by record; randomize within record ties.
- Assign slots 1–14.
- Implement 1000-ticket draw for top 4, then fill 5–14.

## Phase 5: Reporting + query parameters
- Store `pick_counts` and derive:
  - pick distribution table (1..14)
  - P(#1), P(top-4), P(top-k)
  - expected pick
- Add CLI flags or config options for:
  - number of sims
  - sigma, HCA, poss_per_game
  - output format (json/csv/markdown)

## Phase 6: Tests and validation
- Unit tests:
  - tiebreak ordering logic on synthetic scenarios
  - play-in bracket logic
  - lottery draw uniqueness + distribution sanity (e.g., slot 14 ~0.5% #1 over many draws)
- Statistical smoke tests:
  - with sigma very small, outcomes become deterministic from mu
  - with sigma very large, outcomes approach 50/50 and standings become diffuse

## Future extensions (optional)
- Pick ownership (protections/swaps) via post-processing mapping rules.
- Rest days / travel effects in margin model.
- Time-varying strengths (explicit, not from simulated game outcomes).
- More faithful NBA tiebreaking (full official logic).

