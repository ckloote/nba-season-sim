# AGENTS.md (Codex instructions)

You are implementing an upgrade to an existing NBA season simulation repo.
The repo currently has a simple pythagorean expectation method. Replace/extend it to the Monte Carlo margin + play-in + lottery draw pipeline described below.

## High-level requirements
1. Simulate remaining regular-season games one-by-one using a **margin model** derived from team **Net Rating**.
2. Use **approximate** conference seeding tiebreakers:
   - head-to-head win% within tied group
   - conference win%
   - point differential proxy
   - random as last resort
3. Simulate play-in bracket to determine the 14 lottery teams.
4. Simulate NBA draft lottery draw to produce actual pick odds (P(#1), P(top-4), P(pick=n)).
5. Provide a parameter that returns common queries like P(top-k).
6. Do **NOT** update team strengths from simulated outcomes.

## Architectural expectations
- Keep it modular; avoid putting all logic into one script.
- Provide type hints where practical.
- Provide deterministic behavior under a fixed RNG seed.
- Preserve or extend existing CLI entrypoints if present.

## Data expectations
- Use existing data loading patterns in the repo if they exist.
- Required inputs:
  - schedule of remaining games with home/away and ordering
  - current standings W/L
  - team net ratings
  - conference mapping
- If current season point differential exists in data, seed `ptdiff` from it; else start at 0 and accumulate simulated margins.

## Margin model specification
Inputs:
- `NR[team]` (points per 100 possessions)
- `poss_per_game` (default 100)
- `hca_points` (default: pick a reasonable constant, make configurable)
- `sigma_margin` (default: configurable)

Compute:
- `mu = (NR_home - NR_away) * (poss_per_game/100) + hca_points`
- `margin ~ Normal(mu, sigma_margin)`
Winner is sign(margin).

## Play-in simulation specification
Per conference after seeding:
- A: 7 hosts 8 -> winner is seed 7
- B: 9 hosts 10 -> loser eliminated
- Final: loser(A) hosts winner(B) -> winner seed 8; loser eliminated

Use same margin model.

## Lottery draw specification
Given ordered lottery slots 1..14 and ticket counts out of 1000:
- [140,140,140,125,105,90,75,60,45,30,20,15,10,5]

Create a 1000-length ticket list mapping each ticket to the team in that slot.
Draw picks 1..4 by sampling tickets uniformly, redrawing if team already selected.
Assign picks 5..14 to remaining teams in slot order (worst remaining gets pick 5).

## Output specification
At minimum output a JSON or CSV table per team including:
- `p_pick_1`
- `p_top_4`
- `p_top_k` (for user-supplied k)
- `p_pick_1..14` (full distribution)
- `expected_pick`

## Testing requirements
- Unit tests for:
  - play-in bracket correctness
  - lottery draw uniqueness and distribution sanity
  - approximate tiebreak ordering on small synthetic cases
- Include one end-to-end smoke test that runs a tiny schedule with fixed seed and asserts outputs shape.

## What to change in existing code
- Keep the original pythagorean approach available if easy (optional), but the default path should use the new simulator.
- Update docker/entrypoint scripts if necessary so `docker run ...` still works.

