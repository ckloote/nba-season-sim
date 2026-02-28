import json
import subprocess
import sys
import unittest
from pathlib import Path


class CLISmokeTest(unittest.TestCase):
    def test_cli_sample_smoke(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        cmd = [
            sys.executable,
            str(repo_root / "nba_sim.py"),
            "--source",
            "sample",
            "--simulations",
            "50",
            "--report",
            "lottery-top4",
        ]
        completed = subprocess.run(
            cmd, capture_output=True, text=True, check=True, cwd=repo_root
        )

        stdout = completed.stdout
        self.assertIn("Simulated lottery teams", stdout)
        self.assertIn("Top4", stdout)
        self.assertIn("FinalW Mean", stdout)

    def test_cli_json_all_picks_and_simulations_alias(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        cmd = [
            sys.executable,
            str(repo_root / "nba_sim.py"),
            "--source",
            "sample",
            "--simulations",
            "25",
            "--report",
            "all-picks",
            "--output-format",
            "json",
        ]
        completed = subprocess.run(
            cmd, capture_output=True, text=True, check=True, cwd=repo_root
        )
        payload = json.loads(completed.stdout)
        self.assertEqual(25, payload["simulations"])
        self.assertIn("report", payload)
        team_name = next(iter(payload["report"]))
        self.assertIn("final_wins_mean", payload["report"][team_name])

    def test_cli_json_detailed_report_contains_diagnostics(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        cmd = [
            sys.executable,
            str(repo_root / "nba_sim.py"),
            "--source",
            "sample",
            "--simulations",
            "25",
            "--report",
            "lottery-top4",
            "--output-format",
            "json",
            "--explain-details",
        ]
        completed = subprocess.run(
            cmd, capture_output=True, text=True, check=True, cwd=repo_root
        )
        payload = json.loads(completed.stdout)
        lottery_team = payload["lottery_teams"][0]
        team_data = payload["report"][lottery_team]
        self.assertIn("final_wins_mean", team_data)
        self.assertIn("final_wins_p10", team_data)
        self.assertIn("final_wins_p90", team_data)
        self.assertIn("lottery_prob", team_data)
        self.assertIn("avg_slot", team_data)
        self.assertIn("p_slot_1", team_data)
        self.assertIn("p_slot_1_4", team_data)

    def test_cli_csv_detailed_report_has_expected_headers(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        cmd = [
            sys.executable,
            str(repo_root / "nba_sim.py"),
            "--source",
            "sample",
            "--simulations",
            "25",
            "--report",
            "lottery-top4",
            "--output-format",
            "csv",
            "--explain-details",
        ]
        completed = subprocess.run(
            cmd, capture_output=True, text=True, check=True, cwd=repo_root
        )
        header = completed.stdout.splitlines()[0]
        self.assertIn("final_wins_mean", header)
        self.assertIn("final_wins_p10", header)
        self.assertIn("lottery_prob", header)
        self.assertIn("p_slot_1_4", header)


if __name__ == "__main__":
    unittest.main()
