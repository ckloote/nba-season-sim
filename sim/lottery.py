from __future__ import annotations

import random
from collections.abc import Sequence

from .season import SeasonState

LOTTERY_TICKET_COUNTS = [140, 140, 140, 125, 105, 90, 75, 60, 45, 30, 20, 15, 10, 5]


def _validate_teams_14(teams: Sequence[str], label: str) -> None:
    if len(teams) != 14:
        raise ValueError(f"{label} must contain exactly 14 teams")
    if len(set(teams)) != 14:
        raise ValueError(f"{label} must contain unique teams")


def _win_pct(wins: int, losses: int) -> float:
    total = wins + losses
    return 0.0 if total == 0 else wins / total


def lottery_slots(
    lottery_teams: Sequence[str],
    state: SeasonState,
    rng: random.Random,
) -> list[str]:
    """Return pre-draw lottery slots (worst->best), randomized within record ties."""
    _validate_teams_14(lottery_teams, "lottery_teams")

    groups: dict[float, list[str]] = {}
    for team in lottery_teams:
        pct = _win_pct(state.wins.get(team, 0), state.losses.get(team, 0))
        groups.setdefault(pct, []).append(team)

    slots: list[str] = []
    for pct in sorted(groups.keys()):
        group = list(groups[pct])
        if len(group) > 1:
            group.sort(key=lambda _: rng.random())
        slots.extend(group)
    return slots


def draw_lottery_top4(
    slots: Sequence[str],
    rng: random.Random,
    ticket_counts: Sequence[int] = LOTTERY_TICKET_COUNTS,
) -> list[str]:
    """Draw top 4 unique teams by weighted lottery odds, redrawing duplicate teams."""
    _validate_teams_14(slots, "slots")
    if len(ticket_counts) != 14:
        raise ValueError("ticket_counts must contain exactly 14 values")
    if any(t < 0 for t in ticket_counts):
        raise ValueError("ticket_counts must be non-negative")

    total_tickets = sum(ticket_counts)
    if total_tickets <= 0:
        raise ValueError("ticket_counts sum must be > 0")

    winners: list[str] = []
    while len(winners) < 4:
        draw = rng.uniform(0, total_tickets)
        cumulative = 0.0
        selected = slots[-1]
        for team, tickets in zip(slots, ticket_counts):
            cumulative += tickets
            if draw <= cumulative:
                selected = team
                break
        if selected not in winners:
            winners.append(selected)
    return winners


def assign_picks(slots: Sequence[str], top4: Sequence[str]) -> list[str]:
    """Assign picks 1-14 from slots and top4 winners; return ordered pick list."""
    _validate_teams_14(slots, "slots")
    if len(top4) != 4:
        raise ValueError("top4 must contain exactly 4 teams")
    if len(set(top4)) != 4:
        raise ValueError("top4 must contain unique teams")
    if any(team not in slots for team in top4):
        raise ValueError("all top4 teams must be present in slots")

    picks = list(top4)
    picks.extend(team for team in slots if team not in top4)
    return picks
