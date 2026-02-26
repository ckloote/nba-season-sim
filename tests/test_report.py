import unittest

from sim.report import build_team_report, expected_pick, p_top_k, pick_probabilities


class ReportHelpersTest(unittest.TestCase):
    def test_probability_and_expectation_helpers(self) -> None:
        pick_counts = {
            "A": [0, 50, 30, 20] + [0] * 11,
            "B": [0] * 15,
        }
        n_sims = 100

        probs = pick_probabilities(pick_counts, "A", n_sims)
        self.assertAlmostEqual(0.5, probs[1])
        self.assertAlmostEqual(0.3, probs[2])
        self.assertAlmostEqual(0.2, probs[3])
        self.assertAlmostEqual(0.0, probs[14])

        self.assertAlmostEqual(0.8, p_top_k(pick_counts, "A", 2, n_sims))
        self.assertAlmostEqual(1.0, p_top_k(pick_counts, "A", 14, n_sims))
        self.assertAlmostEqual(1.7, expected_pick(pick_counts, "A", n_sims))
        self.assertIsNone(expected_pick(pick_counts, "B", n_sims))

        report = build_team_report(pick_counts, n_sims, top_k=3)
        self.assertAlmostEqual(0.5, report["A"]["p_pick_1"])
        self.assertAlmostEqual(1.0, report["A"]["p_top_k"])
        self.assertAlmostEqual(1.7, report["A"]["expected_pick"])


if __name__ == "__main__":
    unittest.main()
