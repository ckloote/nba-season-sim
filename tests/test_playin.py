import random
import unittest

from sim.model import MarginModel
from sim.playin import simulate_playin


class PlayInTest(unittest.TestCase):
    def test_bracket_deterministic_results(self) -> None:
        seeds = ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10"]
        ratings = {
            "E1": 5.0,
            "E2": 5.0,
            "E3": 5.0,
            "E4": 5.0,
            "E5": 5.0,
            "E6": 5.0,
            "E7": 2.0,
            "E8": 1.0,
            "E9": 0.0,
            "E10": 3.0,
        }
        model = MarginModel(
            net_ratings=ratings,
            poss_per_game=100.0,
            hca_points=0.0,
            sigma_margin=0.0,
            rng=random.Random(7),
        )

        result = simulate_playin(seeds, model)
        playoff_seeds = result["playoff_seeds"]
        eliminated = result["play_in_eliminated"]

        self.assertEqual(["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E10"], playoff_seeds)
        self.assertEqual(["E9", "E8"], eliminated)
        self.assertEqual(8, len(playoff_seeds))
        self.assertEqual(2, len(eliminated))
        self.assertEqual(len(set(playoff_seeds + eliminated)), 10)

    def test_rejects_invalid_seed_length(self) -> None:
        model = MarginModel(net_ratings={"A": 0.0}, sigma_margin=0.0, rng=random.Random(1))
        with self.assertRaises(ValueError):
            simulate_playin(["A"] * 9, model)

    def test_rejects_duplicate_teams(self) -> None:
        model = MarginModel(net_ratings={"A": 0.0, "B": 0.0}, sigma_margin=0.0, rng=random.Random(1))
        with self.assertRaises(ValueError):
            simulate_playin(["A", "B", "A", "B", "A", "B", "A", "B", "A", "B"], model)


if __name__ == "__main__":
    unittest.main()
