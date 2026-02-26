import unittest

from sim.report import build_team_report, simulate_n_runs


class DriverSmokeTest(unittest.TestCase):
    def test_simulate_n_runs_smoke_and_reproducible(self) -> None:
        east = [f"E{i}" for i in range(1, 16)]
        west = [f"W{i}" for i in range(1, 16)]
        team_ids = east + west
        team_meta = {team: {"conference": "E"} for team in east}
        team_meta.update({team: {"conference": "W"} for team in west})

        initial_wins = {}
        initial_losses = {}
        initial_conf_wins = {}
        initial_conf_losses = {}
        net_ratings = {}

        # Unique records by conference rank to avoid seeding ties in this smoke test.
        for idx, team in enumerate(east):
            wins = 55 - idx
            losses = 27 + idx
            initial_wins[team] = wins
            initial_losses[team] = losses
            initial_conf_wins[team] = max(0, wins - 20)
            initial_conf_losses[team] = max(0, losses - 20)
            net_ratings[team] = 8.0 - idx * 0.5

        for idx, team in enumerate(west):
            wins = 54 - idx
            losses = 28 + idx
            initial_wins[team] = wins
            initial_losses[team] = losses
            initial_conf_wins[team] = max(0, wins - 20)
            initial_conf_losses[team] = max(0, losses - 20)
            net_ratings[team] = 7.5 - idx * 0.5

        n_sims = 200
        counts_a = simulate_n_runs(
            team_ids=team_ids,
            team_meta=team_meta,
            remaining_schedule=[],
            net_ratings=net_ratings,
            initial_wins=initial_wins,
            initial_losses=initial_losses,
            initial_conf_wins=initial_conf_wins,
            initial_conf_losses=initial_conf_losses,
            n_sims=n_sims,
            rng_seed=101,
            sigma_margin=10.0,
        )
        counts_b = simulate_n_runs(
            team_ids=team_ids,
            team_meta=team_meta,
            remaining_schedule=[],
            net_ratings=net_ratings,
            initial_wins=initial_wins,
            initial_losses=initial_losses,
            initial_conf_wins=initial_conf_wins,
            initial_conf_losses=initial_conf_losses,
            n_sims=n_sims,
            rng_seed=101,
            sigma_margin=10.0,
        )
        self.assertEqual(counts_a, counts_b)

        for team in team_ids:
            self.assertEqual(15, len(counts_a[team]))
            self.assertGreaterEqual(sum(counts_a[team]), 0)
            self.assertLessEqual(sum(counts_a[team]), n_sims)

        for pick in range(1, 15):
            self.assertEqual(n_sims, sum(counts_a[team][pick] for team in team_ids))

        report = build_team_report(counts_a, n_sims, top_k=4)
        self.assertEqual(set(team_ids), set(report.keys()))
        for team in team_ids:
            p_sum = sum(report[team][f"p_pick_{pick}"] for pick in range(1, 15))
            self.assertGreaterEqual(p_sum, 0.0)
            self.assertLessEqual(p_sum, 1.0)
            expected = report[team]["expected_pick"]
            if expected is not None:
                self.assertGreaterEqual(expected, 1.0)
                self.assertLessEqual(expected, 14.0)


if __name__ == "__main__":
    unittest.main()
