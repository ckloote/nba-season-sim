"""Simulation package scaffold for modular Monte Carlo components."""

from .config import SimConfig
from .model import MarginModel

__all__ = ["MarginModel", "SimConfig"]
