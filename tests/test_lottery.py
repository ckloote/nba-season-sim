import random
import unittest

from sim.lottery import (
    LOTTERY_TICKET_COUNTS,
    assign_picks,
    draw_lottery_top4,
    lottery_slots,
)
from sim.season import SeasonState


class LotteryTest(unittest.TestCase):
    def test_lottery_slots_randomizes_ties_with_seeded_rng(self) -> None:
        teams = [f"T{i}" for i in range(1, 15)]
        wins = {team: 20 for team in teams}
        losses = {team: 30 for team in teams}
        state = SeasonState.from_teams(teams, wins=wins, losses=losses)

        slots_a = lottery_slots(teams, state, random.Random(123))
        slots_b = lottery_slots(teams, state, random.Random(123))
        slots_c = lottery_slots(teams, state, random.Random(124))

        self.assertEqual(slots_a, slots_b)
        self.assertNotEqual(slots_a, slots_c)
        self.assertEqual(set(teams), set(slots_a))

    def test_draw_lottery_top4_unique_and_in_slots(self) -> None:
        slots = [f"S{i}" for i in range(1, 15)]
        winners = draw_lottery_top4(slots, random.Random(7), LOTTERY_TICKET_COUNTS)

        self.assertEqual(4, len(winners))
        self.assertEqual(4, len(set(winners)))
        self.assertTrue(all(team in slots for team in winners))

    def test_assign_picks_matches_top4_and_remaining_slot_order(self) -> None:
        slots = [f"S{i}" for i in range(1, 15)]
        top4 = ["S3", "S1", "S8", "S2"]
        picks = assign_picks(slots, top4)

        self.assertEqual(top4, picks[:4])
        self.assertEqual(14, len(picks))
        self.assertEqual(14, len(set(picks)))
        self.assertEqual(
            ["S4", "S5", "S6", "S7", "S9", "S10", "S11", "S12", "S13", "S14"],
            picks[4:],
        )

    def test_distribution_sanity_slot1_and_slot14_pick1_odds(self) -> None:
        slots = [f"S{i}" for i in range(1, 15)]
        rng = random.Random(9)
        n = 30000
        pick1_counts = {team: 0 for team in slots}
        for _ in range(n):
            winner = draw_lottery_top4(slots, rng, LOTTERY_TICKET_COUNTS)[0]
            pick1_counts[winner] += 1

        slot1_rate = pick1_counts["S1"] / n
        slot14_rate = pick1_counts["S14"] / n

        self.assertGreater(slot1_rate, 0.12)
        self.assertLess(slot1_rate, 0.16)
        self.assertGreater(slot14_rate, 0.003)
        self.assertLess(slot14_rate, 0.008)


if __name__ == "__main__":
    unittest.main()
