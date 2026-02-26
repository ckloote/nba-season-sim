"""Simulation package scaffold for modular Monte Carlo components."""

from .config import SimConfig
from .model import MarginModel
from .season import SeasonState, simulate_regular_season
from .tiebreak import rank_conference_approx, seed_conferences

__all__ = [
    "MarginModel",
    "SeasonState",
    "SimConfig",
    "rank_conference_approx",
    "seed_conferences",
    "simulate_regular_season",
]
