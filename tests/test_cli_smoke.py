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


if __name__ == "__main__":
    unittest.main()
