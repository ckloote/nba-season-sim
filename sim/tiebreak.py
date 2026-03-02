from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from typing import Any

from .season import SeasonState, _conference_for


def _win_pct(wins: int, losses: int) -> float:
    total = wins + losses
    return 0.0 if total == 0 else wins / total


def _h2h_group_pct(team: str, group: Sequence[str], state: SeasonState) -> float:
    wins = 0
    games = 0
    for opp in group:
        if opp == team:
            continue
        wins += state.h2h_wins.get((team, opp), 0)
        games += state.h2h_games.get((team, opp), 0)
    return 0.0 if games == 0 else wins / games


def _conf_pct(team: str, state: SeasonState) -> float:
    return _win_pct(state.conf_wins.get(team, 0), state.conf_losses.get(team, 0))


def rank_conference_approx(
    teams: Sequence[str],
    state: SeasonState,
    rng: random.Random,
) -> list[str]:
    """Rank teams within a conference by approximate NBA tiebreak hierarchy."""
    if not teams:
        return []

    winpct_groups: dict[float, list[str]] = {}
    for team in teams:
        pct = _win_pct(state.wins.get(team, 0), state.losses.get(team, 0))
        winpct_groups.setdefault(pct, []).append(team)

    ordered: list[str] = []
    for pct in sorted(winpct_groups.keys(), reverse=True):
        group = winpct_groups[pct]
        if len(group) == 1:
            ordered.extend(group)
            continue

        # Randomized fallback key ensures deterministic ordering under fixed seed.
        random_key = {team: rng.random() for team in group}
        ranked_group = sorted(
            group,
            key=lambda team: (
                _h2h_group_pct(team, group, state),
                _conf_pct(team, state),
                state.ptdiff.get(team, 0.0),
                random_key[team],
            ),
            reverse=True,
        )
        ordered.extend(ranked_group)

    return ordered


def seed_conferences(
    state: SeasonState,
    team_meta: Mapping[str, Any],
    rng: random.Random,
) -> dict[str, list[str]]:
    """Return conference seeds (ordered lists) for East and West."""
    by_conference: dict[str, list[str]] = {"E": [], "W": []}
    all_teams = set(state.wins.keys()) | set(state.losses.keys())

    for team in all_teams:
        conf = _conference_for(team, team_meta)
        if conf in by_conference:
            by_conference[conf].append(team)

    return {
        "E": rank_conference_approx(by_conference["E"], state, rng),
        "W": rank_conference_approx(by_conference["W"], state, rng),
    }
