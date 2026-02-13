# Testing guide

## Unit tests (recommended)
### 1) Lottery draw
- Ensure top-4 winners are unique.
- Run many draws with a fixed slot assignment and verify:
  - slot 14 gets #1 roughly 0.5% (within tolerance)
  - slot 1 gets #1 roughly 14% (within tolerance)

### 2) Play-in bracket
- Create a deterministic margin model (sigma=0, mu large positive for a chosen team).
- Assert bracket produces correct final 7/8 seeds and correct eliminated teams.

### 3) Approximate tiebreaks
- Synthetic scenario with equal W/L but:
  - Team A beats B head-to-head -> A ranks above B
  - If h2h equal, higher conference win% wins
  - If still equal, higher ptdiff wins

## End-to-end smoke test
- Tiny league (e.g., 4 teams, one conference) with a short schedule.
- Fixed RNG seed.
- Assert simulator returns:
  - pick distribution for all teams
  - probabilities sum to 1 across picks for each team (within floating tolerance)
  - expected pick is between 1 and 14 (or within league-specific range)

## Statistical sanity checks
- sigma -> 0: outcomes become deterministic; repeated sims identical
- sigma -> very large: each game ~50/50; standings distribution broadens

