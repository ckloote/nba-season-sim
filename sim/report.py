from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from typing import Any

from .lottery import assign_picks, draw_lottery_top4, lottery_slots
from .model import MarginModel
from .playin import simulate_playin
from .season import SeasonState, simulate_regular_season
from .tiebreak import seed_conferences


def simulate_n_runs(
    *,
    team_ids: Sequence[str],
    team_meta: Mapping[str, Any],
    remaining_schedule: Sequence[Mapping[str, Any]],
    net_ratings: Mapping[str, float],
    initial_wins: Mapping[str, int],
    initial_losses: Mapping[str, int],
    initial_conf_wins: Mapping[str, int] | None = None,
    initial_conf_losses: Mapping[str, int] | None = None,
    initial_ptdiff: Mapping[str, float] | None = None,
    n_sims: int = 10000,
    rng_seed: int | None = 42,
    poss_per_game: float = 100.0,
    hca_points: float = 2.0,
    sigma_margin: float = 12.0,
) -> dict[str, list[int]]:
    """Run end-to-end season + play-in + lottery simulation and return pick counts."""
    if n_sims <= 0:
        raise ValueError("n_sims must be > 0")
    if len(team_ids) != 30:
        raise ValueError("team_ids must contain exactly 30 teams for NBA lottery simulation")
    if len(set(team_ids)) != 30:
        raise ValueError("team_ids must contain unique teams")

    missing_meta = [team for team in team_ids if team not in team_meta]
    if missing_meta:
        raise ValueError(f"team_meta missing teams: {missing_meta[:3]}")
    missing_nr = [team for team in team_ids if team not in net_ratings]
    if missing_nr:
        raise ValueError(f"net_ratings missing teams: {missing_nr[:3]}")

    pick_counts: dict[str, list[int]] = {team: [0] * 15 for team in team_ids}
    run_rng = random.Random(rng_seed)

    for _ in range(n_sims):
        state = SeasonState.from_teams(
            team_ids,
            wins=initial_wins,
            losses=initial_losses,
            conf_wins=initial_conf_wins,
            conf_losses=initial_conf_losses,
            ptdiff=initial_ptdiff,
        )
        model = MarginModel(
            net_ratings=net_ratings,
            poss_per_game=poss_per_game,
            hca_points=hca_points,
            sigma_margin=sigma_margin,
            rng=run_rng,
        )

        simulate_regular_season(state, remaining_schedule, model, team_meta)
        seeds = seed_conferences(state, team_meta, run_rng)
        east_playin = simulate_playin(seeds["E"][:10], model)
        west_playin = simulate_playin(seeds["W"][:10], model)

        playoff_teams = set(east_playin["playoff_seeds"]) | set(west_playin["playoff_seeds"])
        lottery_teams = [team for team in team_ids if team not in playoff_teams]
        slots = lottery_slots(lottery_teams, state, run_rng)
        top4 = draw_lottery_top4(slots, run_rng)
        picks = assign_picks(slots, top4)

        for pick, team in enumerate(picks, start=1):
            pick_counts[team][pick] += 1

    return pick_counts


def pick_probabilities(
    pick_counts: Mapping[str, Sequence[int]],
    team: str,
    n_sims: int,
) -> dict[int, float]:
    """Return per-pick probabilities for picks 1..14 for a team."""
    if n_sims <= 0:
        raise ValueError("n_sims must be > 0")
    counts = pick_counts[team]
    return {pick: counts[pick] / n_sims for pick in range(1, 15)}


def p_top_k(
    pick_counts: Mapping[str, Sequence[int]],
    team: str,
    k: int,
    n_sims: int,
) -> float:
    """Return probability of team getting any pick in 1..k."""
    if k < 1 or k > 14:
        raise ValueError("k must be between 1 and 14")
    probs = pick_probabilities(pick_counts, team, n_sims)
    return sum(probs[pick] for pick in range(1, k + 1))


def expected_pick(
    pick_counts: Mapping[str, Sequence[int]],
    team: str,
    n_sims: int,
) -> float | None:
    """Return expected pick number for a team, or None if never lottery-selected."""
    probs = pick_probabilities(pick_counts, team, n_sims)
    lottery_prob = sum(probs.values())
    if lottery_prob == 0:
        return None
    return sum(pick * probs[pick] for pick in range(1, 15)) / lottery_prob


def build_team_report(
    pick_counts: Mapping[str, Sequence[int]],
    n_sims: int,
    *,
    top_k: int = 4,
) -> dict[str, dict[str, float | None]]:
    """Build JSON-serializable team-level lottery report."""
    if top_k < 1 or top_k > 14:
        raise ValueError("top_k must be between 1 and 14")

    report: dict[str, dict[str, float | None]] = {}
    for team in pick_counts:
        probs = pick_probabilities(pick_counts, team, n_sims)
        payload: dict[str, float | None] = {
            "p_pick_1": probs[1],
            "p_top_4": sum(probs[pick] for pick in range(1, 5)),
            "p_top_k": sum(probs[pick] for pick in range(1, top_k + 1)),
            "expected_pick": expected_pick(pick_counts, team, n_sims),
        }
        for pick in range(1, 15):
            payload[f"p_pick_{pick}"] = probs[pick]
        report[team] = payload
    return report
