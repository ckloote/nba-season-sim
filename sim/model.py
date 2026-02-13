from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Mapping


@dataclass
class MarginModel:
    """Simulate game outcomes from team net ratings via a normal margin model."""

    net_ratings: Mapping[str, float]
    poss_per_game: float = 100.0
    hca_points: float = 2.0
    sigma_margin: float = 12.0
    rng: random.Random | None = None

    def __post_init__(self) -> None:
        if self.sigma_margin < 0:
            raise ValueError("sigma_margin must be >= 0")
        if self.poss_per_game <= 0:
            raise ValueError("poss_per_game must be > 0")
        if self.rng is None:
            self.rng = random.Random()

    def expected_margin(self, home_team_id: str, away_team_id: str) -> float:
        """Compute expected margin (home minus away)."""
        try:
            nr_home = float(self.net_ratings[home_team_id])
            nr_away = float(self.net_ratings[away_team_id])
        except KeyError as exc:
            raise KeyError(f"Missing net rating for team: {exc.args[0]}") from exc

        return (nr_home - nr_away) * (self.poss_per_game / 100.0) + self.hca_points

    def simulate_game(self, home_team_id: str, away_team_id: str) -> tuple[str, float]:
        """Return (winner_team_id, sampled_margin)."""
        mu = self.expected_margin(home_team_id, away_team_id)
        margin = mu if self.sigma_margin == 0 else self.rng.normalvariate(mu, self.sigma_margin)
        winner_team_id = home_team_id if margin > 0 else away_team_id
        return winner_team_id, margin
