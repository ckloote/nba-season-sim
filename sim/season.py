from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .model import MarginModel


@dataclass
class SeasonState:
    """Mutable standings/bookkeeping state for one simulation run."""

    wins: dict[str, int] = field(default_factory=dict)
    losses: dict[str, int] = field(default_factory=dict)
    conf_wins: dict[str, int] = field(default_factory=dict)
    conf_losses: dict[str, int] = field(default_factory=dict)
    h2h_wins: dict[tuple[str, str], int] = field(default_factory=dict)
    h2h_games: dict[tuple[str, str], int] = field(default_factory=dict)
    ptdiff: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_teams(
        cls,
        team_ids: Sequence[str],
        wins: Mapping[str, int] | None = None,
        losses: Mapping[str, int] | None = None,
        conf_wins: Mapping[str, int] | None = None,
        conf_losses: Mapping[str, int] | None = None,
        ptdiff: Mapping[str, float] | None = None,
    ) -> "SeasonState":
        state = cls(
            wins={team: 0 for team in team_ids},
            losses={team: 0 for team in team_ids},
            conf_wins={team: 0 for team in team_ids},
            conf_losses={team: 0 for team in team_ids},
            ptdiff={team: 0.0 for team in team_ids},
        )
        if wins:
            state.wins.update({team: int(value) for team, value in wins.items()})
        if losses:
            state.losses.update({team: int(value) for team, value in losses.items()})
        if conf_wins:
            state.conf_wins.update({team: int(value) for team, value in conf_wins.items()})
        if conf_losses:
            state.conf_losses.update({team: int(value) for team, value in conf_losses.items()})
        if ptdiff:
            state.ptdiff.update({team: float(value) for team, value in ptdiff.items()})
        return state


def _conference_for(team_id: str, team_meta: Mapping[str, Any]) -> str | None:
    value = team_meta.get(team_id)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        conference = value.get("conference")
        return str(conference) if conference is not None else None
    return None


def _sorted_schedule(schedule: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(
        schedule,
        key=lambda game: (
            str(game.get("date", "")),
            str(game.get("game_id", "")),
        ),
    )


def _bump(mapping: dict[Any, int], key: Any, inc: int = 1) -> None:
    mapping[key] = mapping.get(key, 0) + inc


def _bump_float(mapping: dict[str, float], key: str, inc: float) -> None:
    mapping[key] = mapping.get(key, 0.0) + inc


def simulate_regular_season(
    state: SeasonState,
    schedule: Sequence[Mapping[str, Any]],
    model: MarginModel,
    team_meta: Mapping[str, Any],
) -> SeasonState:
    """Simulate remaining games in chronological order and update in-place state."""
    for game in _sorted_schedule(schedule):
        home = str(game["home_team_id"])
        away = str(game["away_team_id"])
        winner, margin = model.simulate_game(home, away)
        loser = away if winner == home else home

        _bump(state.wins, winner, 1)
        _bump(state.losses, loser, 1)

        if _conference_for(home, team_meta) == _conference_for(away, team_meta):
            _bump(state.conf_wins, winner, 1)
            _bump(state.conf_losses, loser, 1)

        _bump(state.h2h_games, (home, away), 1)
        _bump(state.h2h_games, (away, home), 1)
        _bump(state.h2h_wins, (winner, loser), 1)

        _bump_float(state.ptdiff, home, float(margin))
        _bump_float(state.ptdiff, away, -float(margin))

    return state
