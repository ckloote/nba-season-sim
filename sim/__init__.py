"""Simulation package scaffold for modular Monte Carlo components."""

from .config import SimConfig
from .lottery import assign_picks, draw_lottery_top4, lottery_slots
from .model import MarginModel
from .playin import simulate_playin
from .season import SeasonState, simulate_regular_season
from .tiebreak import rank_conference_approx, seed_conferences

__all__ = [
    "MarginModel",
    "SeasonState",
    "SimConfig",
    "assign_picks",
    "draw_lottery_top4",
    "lottery_slots",
    "rank_conference_approx",
    "seed_conferences",
    "simulate_playin",
    "simulate_regular_season",
]
