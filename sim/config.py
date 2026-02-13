from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SimConfig:
    """Top-level simulation parameters for future modular pipeline work."""

    n_sims: int = 20000
    rng_seed: Optional[int] = 42
    poss_per_game: float = 100.0
    hca_points: float = 2.0
    sigma_margin: float = 12.0
    pythag_exponent: float = 14.0
    report: str = "lottery-top4"
