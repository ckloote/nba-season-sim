"""Simulation package scaffold for modular Monte Carlo components."""

from .config import SimConfig
from .model import MarginModel
from .season import SeasonState, simulate_regular_season

__all__ = ["MarginModel", "SeasonState", "SimConfig", "simulate_regular_season"]
