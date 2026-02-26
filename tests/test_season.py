import random
import unittest

from sim.model import MarginModel
from sim.season import SeasonState, simulate_regular_season


class SeasonSimulationTest(unittest.TestCase):
    def test_regular_season_updates_all_bookkeeping(self) -> None:
        model = MarginModel(
            net_ratings={"A": 5.0, "B": 1.0, "C": 0.0},
            poss_per_game=100.0,
            hca_points=0.0,
            sigma_margin=0.0,
            rng=random.Random(7),
        )

        team_meta = {"A": {"conference": "E"}, "B": {"conference": "E"}, "C": {"conference": "W"}}
        state = SeasonState.from_teams(
            ["A", "B", "C"],
            wins={"A": 10, "B": 11, "C": 12},
            losses={"A": 5, "B": 4, "C": 3},
        )
        schedule = [
            {"game_id": "g2", "date": "2026-02-02", "home_team_id": "C", "away_team_id": "A"},
            {"game_id": "g1", "date": "2026-02-01", "home_team_id": "A", "away_team_id": "B"},
            {"game_id": "g3", "date": "2026-02-03", "home_team_id": "B", "away_team_id": "C"},
        ]

        simulate_regular_season(state, schedule, model, team_meta)

        self.assertEqual(12, state.wins["A"])
        self.assertEqual(12, state.wins["B"])
        self.assertEqual(12, state.wins["C"])

        self.assertEqual(5, state.losses["A"])
        self.assertEqual(5, state.losses["B"])
        self.assertEqual(5, state.losses["C"])

        self.assertEqual(1, state.conf_wins["A"])
        self.assertEqual(1, state.conf_losses["B"])
        self.assertEqual(0, state.conf_wins["C"])
        self.assertEqual(0, state.conf_losses["C"])

        self.assertEqual(1, state.h2h_games[("A", "B")])
        self.assertEqual(1, state.h2h_games[("B", "A")])
        self.assertEqual(1, state.h2h_games[("A", "C")])
        self.assertEqual(1, state.h2h_games[("C", "A")])
        self.assertEqual(1, state.h2h_games[("B", "C")])
        self.assertEqual(1, state.h2h_games[("C", "B")])

        self.assertEqual(1, state.h2h_wins[("A", "B")])
        self.assertEqual(1, state.h2h_wins[("A", "C")])
        self.assertEqual(1, state.h2h_wins[("B", "C")])
        self.assertEqual(0, state.h2h_wins.get(("B", "A"), 0))
        self.assertEqual(0, state.h2h_wins.get(("C", "A"), 0))
        self.assertEqual(0, state.h2h_wins.get(("C", "B"), 0))

        self.assertEqual(9.0, state.ptdiff["A"])
        self.assertEqual(-3.0, state.ptdiff["B"])
        self.assertEqual(-6.0, state.ptdiff["C"])


if __name__ == "__main__":
    unittest.main()
