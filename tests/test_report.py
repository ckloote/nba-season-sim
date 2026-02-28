import unittest

from sim.report import (
    build_team_report,
    expected_pick,
    p_top_k,
    pick_probabilities,
    simulate_n_runs,
    simulate_n_runs_with_diagnostics,
)


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

    def test_simulation_diagnostics_are_consistent(self) -> None:
        east = [f"E{i}" for i in range(1, 16)]
        west = [f"W{i}" for i in range(1, 16)]
        team_ids = east + west
        team_meta = {team: {"conference": "E"} for team in east}
        team_meta.update({team: {"conference": "W"} for team in west})
        net_ratings = {team: 0.0 for team in team_ids}
        initial_wins = {team: 30 for team in team_ids}
        initial_losses = {team: 30 for team in team_ids}

        diagnostics = simulate_n_runs_with_diagnostics(
            team_ids=team_ids,
            team_meta=team_meta,
            remaining_schedule=[],
            net_ratings=net_ratings,
            initial_wins=initial_wins,
            initial_losses=initial_losses,
            n_sims=100,
            rng_seed=11,
        )
        self.assertEqual(set(team_ids), set(diagnostics.pick_counts))
        self.assertEqual(set(team_ids), set(diagnostics.team_diagnostics))
        for team in team_ids:
            diag = diagnostics.team_diagnostics[team]
            self.assertGreaterEqual(diag.final_wins_mean, 0.0)
            self.assertLessEqual(diag.final_wins_mean, 82.0)
            self.assertLessEqual(diag.final_wins_p10, diag.final_wins_p90)
            self.assertGreaterEqual(diag.lottery_prob, 0.0)
            self.assertLessEqual(diag.lottery_prob, 1.0)
            self.assertGreaterEqual(diag.p_slot_1, 0.0)
            self.assertLessEqual(diag.p_slot_1, diag.lottery_prob + 1e-9)
            self.assertGreaterEqual(diag.p_slot_1_4, diag.p_slot_1)
            self.assertLessEqual(diag.p_slot_1_4, diag.lottery_prob + 1e-9)

    def test_simulate_n_runs_matches_diagnostics_pick_counts(self) -> None:
        east = [f"E{i}" for i in range(1, 16)]
        west = [f"W{i}" for i in range(1, 16)]
        team_ids = east + west
        team_meta = {team: {"conference": "E"} for team in east}
        team_meta.update({team: {"conference": "W"} for team in west})
        net_ratings = {team: 0.0 for team in team_ids}
        initial_wins = {team: 30 for team in team_ids}
        initial_losses = {team: 30 for team in team_ids}

        params = {
            "team_ids": team_ids,
            "team_meta": team_meta,
            "remaining_schedule": [],
            "net_ratings": net_ratings,
            "initial_wins": initial_wins,
            "initial_losses": initial_losses,
            "n_sims": 100,
            "rng_seed": 99,
        }
        counts_light = simulate_n_runs(**params)
        diagnostics = simulate_n_runs_with_diagnostics(**params)
        self.assertEqual(counts_light, diagnostics.pick_counts)


if __name__ == "__main__":
    unittest.main()
