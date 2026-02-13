# Plan: Upgrade season simulator to margin-based Monte Carlo + play-in + lottery draw

## Goal
Replace the current "simple pythagorean expectation" rest-of-season simulator with a schedule-aware **Monte Carlo simulator** that:
1. Simulates each remaining regular-season game using a **margin model** derived from **team Net Rating**.
2. Applies **approximate seeding tiebreakers** (head-to-head within tied group, conference record, point differential proxy, random).
3. Simulates the **NBA Play-In Tournament** to determine the 14 lottery teams.
4. Simulates the **NBA Draft Lottery draw** to produce **actual pick odds** (P(#1), P(top-4), P(pick=n), etc.).
5. Exposes parameters for query-style outputs (e.g., top-k odds) and for model constants (sigma, HCA, etc.).

## Non-goals (for this iteration)
- No player-level modeling.
- No injuries, trades, or roster updates during sims.
- No official NBA full tiebreak procedure (use approximation).
- No pick-swap/protection handling unless already present (optional extension; see roadmap).

## Core approach
### 1) Game model (margin simulation)
Use team Net Rating (points per 100 possessions) to compute expected game margin:
- `mu = (NR_home - NR_away) * (poss_per_game / 100) + hca_points`
- Sample `margin ~ Normal(mu, sigma_margin)`
- Home wins if `margin > 0`, else away wins.

**Important:** Do NOT update team strength (Net Rating) based on simulated games.

### 2) Regular-season simulation
For each sim run:
- Initialize standings from current W/L.
- Iterate remaining games (chronological order):
  - simulate margin and winner
  - update W/L
  - update tie-related bookkeeping:
    - head-to-head results between the two teams
    - conference W/L (if same conference)
    - point differential accumulator (optional but recommended)

### 3) Conference seeding with approximate tiebreakers
Within each conference, rank teams by:
1. Win% (W / (W+L))
2. If tie group:
   a) Head-to-head win% **within the tied group**
   b) Conference win%
   c) Point differential (accumulated; start from current season PD if available and add simulated margins)
   d) Random order

Use this order to assign seeds 1–15 per conference.

### 4) Play-in simulation
Per conference:
- Game A: 7 hosts 8 → winner is seed 7, loser goes to final game
- Game B: 9 hosts 10 → loser eliminated, winner goes to final game
- Final: loser(Game A) hosts winner(Game B) → winner is seed 8, loser eliminated

Simulate these with the SAME margin model.

Now playoff teams = seeds 1–6 plus the two play-in winners (7 and 8).

Lottery teams = all non-playoff teams (14 total).

### 5) Lottery positioning (pre-draw order) and tie handling
Within the 14 lottery teams:
- Sort by record (worst to best).
- Any record ties: randomize order within tied group each simulation run.

This produces **slots 1–14** (slot 1 = worst record among lottery teams).

### 6) Lottery draw simulation (top-4) and assigning picks 5–14
Use the standard odds table (tickets out of 1000):
- Slots 1–3: 140 tickets each
- Slot 4: 125
- Slot 5: 105
- Slot 6: 90
- Slot 7: 75
- Slot 8: 60
- Slot 9: 45
- Slot 10: 30
- Slot 11: 20
- Slot 12: 15
- Slot 13: 10
- Slot 14: 5

Procedure per simulation run:
1. Build a 1000-length ticket list mapping tickets → team (by slot).
2. Draw until you have 4 unique teams (redraw if repeat team).
3. Those winners become picks 1–4 in draw order.
4. Remaining 10 teams get picks 5–14 in lottery-slot order (worst remaining gets pick 5).

### 7) Aggregation and output queries
Maintain `pick_counts[team][pick]` across sims.
Expose query outputs:
- P(#1) = count pick==1 / N
- P(top-4) = sum pick 1..4 / N
- P(1..k) for arbitrary k
- Full distribution P(pick=n) for n=1..14
- Expected pick E[pick]

## Data requirements
### Required
- Remaining schedule with home/away and date ordering.
- Current standings W/L by team.
- Team metadata: conference, division (division optional unless later expanded).
- Team net ratings (NR) for all teams.

### Recommended (improves tie realism)
- Current season point differential (PF-PA) by team to seed `ptdiff` before adding simulated margins.

## Deliverables
- New simulation pipeline implementing the above.
- CLI (or existing entry point) to run sims and output pick-odds report.
- Unit tests for deterministic components and statistical smoke tests for simulator behavior.

## Acceptance criteria
- Runs end-to-end in the existing docker container.
- Produces stable pick odds for teams over 10k+ sims.
- Play-in changes lottery field (teams near 7–10 should have non-trivial lottery-team probability).
- Team strengths remain fixed; no rating update step exists.

