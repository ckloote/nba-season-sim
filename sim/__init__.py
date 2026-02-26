"""Simulation package scaffold for modular Monte Carlo components."""

from .config import SimConfig
from .lottery import assign_picks, draw_lottery_top4, lottery_slots
from .model import MarginModel
from .playin import simulate_playin
from .report import build_team_report, expected_pick, p_top_k, pick_probabilities, simulate_n_runs
from .season import SeasonState, simulate_regular_season
from .tiebreak import rank_conference_approx, seed_conferences

__all__ = [
    "MarginModel",
    "SeasonState",
    "SimConfig",
    "assign_picks",
    "build_team_report",
    "draw_lottery_top4",
    "expected_pick",
    "lottery_slots",
    "p_top_k",
    "pick_probabilities",
    "rank_conference_approx",
    "seed_conferences",
    "simulate_n_runs",
    "simulate_playin",
    "simulate_regular_season",
]
