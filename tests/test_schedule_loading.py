import argparse
import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from nba_sim import SAMPLE_TEAMS, load_schedule_from_csv, run_modular_simulations
from sim.model import MarginModel
from sim.season import SeasonState, simulate_regular_season


class ScheduleLoadingTest(unittest.TestCase):
    def test_load_schedule_from_csv_parses_and_skips_completed(self) -> None:
        csv_text = """date,home_team_id,away_team_id,is_completed,game_id
2026-03-01,BOS,NYK,0,g1
2026-03-02,Los Angeles Lakers,GSW,false,g2
2026-02-20,Celtics,Knicks,1,g3
"""
        known_teams = {"Celtics", "Knicks", "Lakers", "Warriors"}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "schedule.csv"
            path.write_text(csv_text, encoding="utf-8")
            schedule = load_schedule_from_csv(str(path), known_teams)

        self.assertEqual(2, len(schedule))
        self.assertEqual("Celtics", schedule[0]["home_team_id"])
        self.assertEqual("Knicks", schedule[0]["away_team_id"])
        self.assertEqual("Lakers", schedule[1]["home_team_id"])
        self.assertEqual("Warriors", schedule[1]["away_team_id"])

    def test_run_modular_falls_back_when_schedule_load_fails(self) -> None:
        args = argparse.Namespace(
            source="sample",
            csv_path="",
            schedule_csv_path="/does/not/exist.csv",
            http_timeout=2.0,
            http_retries=1,
            http_backoff_seconds=0.1,
            n_sims=10,
            seed=7,
            poss_per_game=100.0,
            hca_points=2.0,
            sigma_margin=12.0,
            top_k=4,
        )

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            report = run_modular_simulations(SAMPLE_TEAMS, args)

        self.assertEqual(30, len(report))
        warning_text = stderr.getvalue()
        self.assertIn("failed to load remaining schedule", warning_text)
        self.assertIn("using current records only", warning_text)

    def test_mini_schedule_fixture_updates_records_deterministically(self) -> None:
        csv_text = """date,home_team_id,away_team_id,is_completed,game_id
2026-03-01,Celtics,Nets,0,g1
2026-03-02,Nets,Celtics,0,g2
"""
        known_teams = {"Celtics", "Nets"}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "mini_schedule.csv"
            path.write_text(csv_text, encoding="utf-8")
            schedule = load_schedule_from_csv(str(path), known_teams)

        state = SeasonState.from_teams(
            ["Celtics", "Nets"],
            wins={"Celtics": 40, "Nets": 20},
            losses={"Celtics": 20, "Nets": 40},
            conf_wins={"Celtics": 25, "Nets": 12},
            conf_losses={"Celtics": 10, "Nets": 25},
        )
        model = MarginModel(
            net_ratings={"Celtics": 10.0, "Nets": -10.0},
            poss_per_game=100.0,
            hca_points=2.0,
            sigma_margin=0.0,
        )
        team_meta = {"Celtics": {"conference": "E"}, "Nets": {"conference": "E"}}
        simulate_regular_season(state, schedule, model, team_meta)

        self.assertEqual(42, state.wins["Celtics"])
        self.assertEqual(20, state.losses["Celtics"])
        self.assertEqual(20, state.wins["Nets"])
        self.assertEqual(42, state.losses["Nets"])
        self.assertEqual(27, state.conf_wins["Celtics"])
        self.assertEqual(10, state.conf_losses["Celtics"])
        self.assertEqual(12, state.conf_wins["Nets"])
        self.assertEqual(27, state.conf_losses["Nets"])
        self.assertEqual(2, state.h2h_wins[("Celtics", "Nets")])
        self.assertEqual(0, state.h2h_wins.get(("Nets", "Celtics"), 0))


if __name__ == "__main__":
    unittest.main()
