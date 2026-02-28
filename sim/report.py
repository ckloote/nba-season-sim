from __future__ import annotations

import random
from dataclasses import dataclass
from collections.abc import Mapping, Sequence
from typing import Any

from .lottery import assign_picks, draw_lottery_top4, lottery_slots
from .model import MarginModel
from .playin import simulate_playin
from .season import SeasonState, simulate_regular_season
from .tiebreak import seed_conferences


@dataclass(frozen=True)
class TeamDiagnostics:
    final_wins_mean: float
    final_wins_p10: float
    final_wins_p90: float
    lottery_prob: float
    avg_slot: float | None
    p_slot_1: float
    p_slot_1_4: float


@dataclass(frozen=True)
class SimulationDiagnostics:
    pick_counts: dict[str, list[int]]
    team_diagnostics: dict[str, TeamDiagnostics]


def _percentile(values: Sequence[int], percentile: float) -> float:
    if not values:
        raise ValueError("values must not be empty")
    if percentile <= 0:
        return float(min(values))
    if percentile >= 100:
        return float(max(values))

    ordered = sorted(values)
    rank = (len(ordered) - 1) * (percentile / 100.0)
    lo = int(rank)
    hi = min(lo + 1, len(ordered) - 1)
    weight = rank - lo
    return ordered[lo] * (1.0 - weight) + ordered[hi] * weight


def simulate_n_runs_with_diagnostics(
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
) -> SimulationDiagnostics:
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
    lottery_appearances: dict[str, int] = {team: 0 for team in team_ids}
    slot_counts: dict[str, list[int]] = {team: [0] * 15 for team in team_ids}
    final_wins_samples: dict[str, list[int]] = {team: [] for team in team_ids}
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
        for team in team_ids:
            final_wins_samples[team].append(int(state.wins.get(team, 0)))

        seeds = seed_conferences(state, team_meta, run_rng)
        east_playin = simulate_playin(seeds["E"][:10], model)
        west_playin = simulate_playin(seeds["W"][:10], model)

        playoff_teams = set(east_playin["playoff_seeds"]) | set(west_playin["playoff_seeds"])
        lottery_teams = [team for team in team_ids if team not in playoff_teams]
        for team in lottery_teams:
            lottery_appearances[team] += 1

        slots = lottery_slots(lottery_teams, state, run_rng)
        for slot_idx, team in enumerate(slots, start=1):
            slot_counts[team][slot_idx] += 1

        top4 = draw_lottery_top4(slots, run_rng)
        picks = assign_picks(slots, top4)
        for pick, team in enumerate(picks, start=1):
            pick_counts[team][pick] += 1

    team_diagnostics: dict[str, TeamDiagnostics] = {}
    for team in team_ids:
        appearances = lottery_appearances[team]
        slot_total = sum(slot * slot_counts[team][slot] for slot in range(1, 15))
        avg_slot = (slot_total / appearances) if appearances > 0 else None
        team_diagnostics[team] = TeamDiagnostics(
            final_wins_mean=sum(final_wins_samples[team]) / n_sims,
            final_wins_p10=_percentile(final_wins_samples[team], 10.0),
            final_wins_p90=_percentile(final_wins_samples[team], 90.0),
            lottery_prob=appearances / n_sims,
            avg_slot=avg_slot,
            p_slot_1=slot_counts[team][1] / n_sims,
            p_slot_1_4=sum(slot_counts[team][slot] for slot in range(1, 5)) / n_sims,
        )

    return SimulationDiagnostics(
        pick_counts=pick_counts,
        team_diagnostics=team_diagnostics,
    )


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
    diagnostics = simulate_n_runs_with_diagnostics(
        team_ids=team_ids,
        team_meta=team_meta,
        remaining_schedule=remaining_schedule,
        net_ratings=net_ratings,
        initial_wins=initial_wins,
        initial_losses=initial_losses,
        initial_conf_wins=initial_conf_wins,
        initial_conf_losses=initial_conf_losses,
        initial_ptdiff=initial_ptdiff,
        n_sims=n_sims,
        rng_seed=rng_seed,
        poss_per_game=poss_per_game,
        hca_points=hca_points,
        sigma_margin=sigma_margin,
    )
    return diagnostics.pick_counts


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
    team_diagnostics: Mapping[str, TeamDiagnostics] | None = None,
    explain_details: bool = False,
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
        if team_diagnostics is not None and team in team_diagnostics:
            diag = team_diagnostics[team]
            payload["final_wins_mean"] = diag.final_wins_mean
            if explain_details:
                payload["final_wins_p10"] = diag.final_wins_p10
                payload["final_wins_p90"] = diag.final_wins_p90
                payload["lottery_prob"] = diag.lottery_prob
                payload["avg_slot"] = diag.avg_slot
                payload["p_slot_1"] = diag.p_slot_1
                payload["p_slot_1_4"] = diag.p_slot_1_4
        else:
            payload["final_wins_mean"] = None

        for pick in range(1, 15):
            payload[f"p_pick_{pick}"] = probs[pick]
        report[team] = payload
    return report
