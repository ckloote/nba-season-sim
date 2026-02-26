import random
import unittest

from sim.season import SeasonState
from sim.tiebreak import rank_conference_approx, seed_conferences


class TiebreakTest(unittest.TestCase):
    def test_head_to_head_breaks_tie(self) -> None:
        state = SeasonState.from_teams(
            ["A", "B"],
            wins={"A": 40, "B": 40},
            losses={"A": 30, "B": 30},
            conf_wins={"A": 20, "B": 20},
            conf_losses={"A": 15, "B": 15},
            ptdiff={"A": 5.0, "B": 50.0},
        )
        state.h2h_games[("A", "B")] = 4
        state.h2h_games[("B", "A")] = 4
        state.h2h_wins[("A", "B")] = 3
        state.h2h_wins[("B", "A")] = 1

        ranked = rank_conference_approx(["A", "B"], state, random.Random(1))
        self.assertEqual(["A", "B"], ranked)

    def test_conference_win_pct_breaks_tie_when_h2h_equal(self) -> None:
        state = SeasonState.from_teams(
            ["A", "B"],
            wins={"A": 42, "B": 42},
            losses={"A": 28, "B": 28},
            conf_wins={"A": 25, "B": 22},
            conf_losses={"A": 10, "B": 13},
            ptdiff={"A": 0.0, "B": 100.0},
        )
        state.h2h_games[("A", "B")] = 2
        state.h2h_games[("B", "A")] = 2
        state.h2h_wins[("A", "B")] = 1
        state.h2h_wins[("B", "A")] = 1

        ranked = rank_conference_approx(["A", "B"], state, random.Random(2))
        self.assertEqual(["A", "B"], ranked)

    def test_ptdiff_breaks_tie_when_h2h_and_conf_equal(self) -> None:
        state = SeasonState.from_teams(
            ["A", "B"],
            wins={"A": 38, "B": 38},
            losses={"A": 32, "B": 32},
            conf_wins={"A": 21, "B": 21},
            conf_losses={"A": 19, "B": 19},
            ptdiff={"A": 12.0, "B": 3.0},
        )
        state.h2h_games[("A", "B")] = 2
        state.h2h_games[("B", "A")] = 2
        state.h2h_wins[("A", "B")] = 1
        state.h2h_wins[("B", "A")] = 1

        ranked = rank_conference_approx(["A", "B"], state, random.Random(3))
        self.assertEqual(["A", "B"], ranked)

    def test_seed_conferences_groups_and_orders(self) -> None:
        state = SeasonState.from_teams(
            ["E1", "E2", "W1", "W2"],
            wins={"E1": 50, "E2": 50, "W1": 40, "W2": 39},
            losses={"E1": 20, "E2": 20, "W1": 30, "W2": 31},
            conf_wins={"E1": 30, "E2": 28, "W1": 24, "W2": 20},
            conf_losses={"E1": 10, "E2": 12, "W1": 16, "W2": 20},
            ptdiff={"E1": 100.0, "E2": 0.0, "W1": 30.0, "W2": 5.0},
        )
        state.h2h_games[("E1", "E2")] = 2
        state.h2h_games[("E2", "E1")] = 2
        state.h2h_wins[("E1", "E2")] = 1
        state.h2h_wins[("E2", "E1")] = 1

        team_meta = {
            "E1": {"conference": "E"},
            "E2": {"conference": "E"},
            "W1": {"conference": "W"},
            "W2": {"conference": "W"},
        }
        seeds = seed_conferences(state, team_meta, random.Random(11))

        self.assertEqual(["E1", "E2"], seeds["E"])
        self.assertEqual(["W1", "W2"], seeds["W"])


if __name__ == "__main__":
    unittest.main()
