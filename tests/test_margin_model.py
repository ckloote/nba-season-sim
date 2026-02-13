import random
import unittest

from sim.model import MarginModel


class MarginModelTest(unittest.TestCase):
    def test_sigma_zero_margin_equals_mu_and_winner_matches_sign(self) -> None:
        model = MarginModel(
            net_ratings={"A": 4.0, "B": 1.0},
            poss_per_game=100.0,
            hca_points=0.0,
            sigma_margin=0.0,
            rng=random.Random(123),
        )
        winner, margin = model.simulate_game("A", "B")
        self.assertEqual(3.0, margin)
        self.assertEqual("A", winner)

        model2 = MarginModel(
            net_ratings={"A": 1.0, "B": 4.0},
            poss_per_game=100.0,
            hca_points=0.0,
            sigma_margin=0.0,
            rng=random.Random(123),
        )
        winner2, margin2 = model2.simulate_game("A", "B")
        self.assertEqual(-3.0, margin2)
        self.assertEqual("B", winner2)

    def test_fixed_seed_produces_repeatable_sequence(self) -> None:
        ratings = {"HOME": 2.5, "AWAY": 0.5}
        model_a = MarginModel(ratings, sigma_margin=11.0, rng=random.Random(42))
        model_b = MarginModel(ratings, sigma_margin=11.0, rng=random.Random(42))

        seq_a = [model_a.simulate_game("HOME", "AWAY") for _ in range(5)]
        seq_b = [model_b.simulate_game("HOME", "AWAY") for _ in range(5)]

        self.assertEqual(seq_a, seq_b)


if __name__ == "__main__":
    unittest.main()
