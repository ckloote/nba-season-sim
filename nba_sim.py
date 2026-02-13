#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import time
import urllib.parse
import urllib.request
from urllib.error import URLError
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Dict, List, Sequence, Tuple

from sim.lottery import LOTTERY_TICKET_COUNTS

TOTAL_GAMES = 82
LOTTERY_TEAMS = 14
TOP_LOTTERY_PICKS = 4


@dataclass(frozen=True)
class TeamState:
    team: str
    wins: int
    losses: int
    games_played: int
    points_for: float
    points_against: float


SAMPLE_TEAMS: List[TeamState] = [
    TeamState("Celtics", 37, 12, 49, 120.7, 111.5),
    TeamState("Cavaliers", 39, 10, 49, 122.0, 111.6),
    TeamState("Knicks", 34, 17, 51, 118.4, 112.0),
    TeamState("Bucks", 28, 21, 49, 114.9, 112.2),
    TeamState("Pacers", 28, 21, 49, 116.1, 115.2),
    TeamState("76ers", 20, 29, 49, 109.4, 112.3),
    TeamState("Heat", 24, 25, 49, 111.2, 110.6),
    TeamState("Magic", 26, 24, 50, 106.1, 104.8),
    TeamState("Bulls", 22, 27, 49, 116.7, 121.3),
    TeamState("Hawks", 24, 27, 51, 116.0, 118.4),
    TeamState("Nets", 17, 33, 50, 105.1, 111.3),
    TeamState("Raptors", 16, 35, 51, 111.6, 117.3),
    TeamState("Hornets", 12, 36, 48, 106.2, 112.6),
    TeamState("Wizards", 9, 41, 50, 108.6, 122.0),
    TeamState("Pistons", 23, 26, 49, 113.8, 115.5),
    TeamState("Thunder", 39, 9, 48, 118.3, 104.9),
    TeamState("Timberwolves", 30, 22, 52, 110.7, 107.9),
    TeamState("Nuggets", 31, 19, 50, 120.9, 116.8),
    TeamState("Clippers", 28, 21, 49, 111.4, 108.5),
    TeamState("Mavericks", 26, 24, 50, 115.0, 113.4),
    TeamState("Suns", 25, 25, 50, 113.0, 111.9),
    TeamState("Kings", 25, 24, 49, 116.8, 114.7),
    TeamState("Lakers", 27, 20, 47, 113.1, 112.4),
    TeamState("Warriors", 25, 25, 50, 112.2, 111.4),
    TeamState("Rockets", 32, 18, 50, 113.1, 107.7),
    TeamState("Grizzlies", 35, 16, 51, 123.2, 115.6),
    TeamState("Spurs", 22, 26, 48, 112.7, 113.9),
    TeamState("Pelicans", 12, 37, 49, 108.9, 117.0),
    TeamState("Trail Blazers", 20, 29, 49, 108.3, 114.2),
    TeamState("Jazz", 11, 37, 48, 111.2, 118.7),
]


def current_nba_season() -> str:
    today = datetime.now(UTC)
    start_year = today.year if today.month >= 10 else today.year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def load_live_teams(
    season: str, timeout_seconds: float, retries: int, backoff_seconds: float
) -> List[TeamState]:
    params = {
        "College": "",
        "Conference": "",
        "Country": "",
        "DateFrom": "",
        "DateTo": "",
        "Division": "",
        "DraftPick": "",
        "DraftYear": "",
        "GameScope": "",
        "GameSegment": "",
        "Height": "",
        "LastNGames": "0",
        "LeagueID": "00",
        "Location": "",
        "MeasureType": "Base",
        "Month": "0",
        "OpponentTeamID": "0",
        "Outcome": "",
        "PORound": "0",
        "PaceAdjust": "N",
        "PerMode": "PerGame",
        "Period": "0",
        "PlayerExperience": "",
        "PlayerPosition": "",
        "PlusMinus": "N",
        "Rank": "N",
        "Season": season,
        "SeasonSegment": "",
        "SeasonType": "Regular Season",
        "ShotClockRange": "",
        "StarterBench": "",
        "TeamID": "0",
        "TwoWay": "0",
        "VsConference": "",
        "VsDivision": "",
        "Weight": "",
    }
    url = "https://stats.nba.com/stats/leaguedashteamstats?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.nba.com/",
            "Origin": "https://www.nba.com",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    last_error: Exception | None = None
    attempts = max(1, retries)
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except (TimeoutError, URLError) as exc:
            last_error = exc
            if attempt >= attempts:
                raise RuntimeError(
                    f"Failed to fetch live NBA data after {attempts} attempts "
                    f"(timeout={timeout_seconds}s): {exc}"
                ) from exc
            time.sleep(backoff_seconds * attempt)
    else:
        raise RuntimeError(f"Failed to fetch live NBA data: {last_error}")

    result_set = payload["resultSets"][0]
    headers = result_set["headers"]
    rows = result_set["rowSet"]
    idx = {key: i for i, key in enumerate(headers)}

    def value(row: Sequence[object], *names: str) -> float:
        for name in names:
            if name in idx and row[idx[name]] is not None:
                return float(row[idx[name]])
        raise KeyError(f"None of these fields exist in API response: {names}")

    teams: List[TeamState] = []
    for row in rows:
        pts_for = value(row, "PTS")
        plus_minus = value(row, "PLUS_MINUS")
        # Some API payloads include OPP_PTS directly; others only provide point differential.
        pts_against = value(row, "OPP_PTS") if "OPP_PTS" in idx else (pts_for - plus_minus)

        teams.append(
            TeamState(
                team=str(row[idx["TEAM_NAME"]]),
                wins=int(row[idx["W"]]),
                losses=int(row[idx["L"]]),
                games_played=int(row[idx["GP"]]),
                points_for=pts_for,
                points_against=pts_against,
            )
        )

    if len(teams) != 30:
        raise RuntimeError(f"Expected 30 teams from API; got {len(teams)}")
    return teams


def load_teams_from_csv(path: str) -> List[TeamState]:
    teams: List[TeamState] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {
            "team",
            "wins",
            "losses",
            "games_played",
            "points_for",
            "points_against",
        }
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV missing required columns: {sorted(missing)}")

        for row in reader:
            teams.append(
                TeamState(
                    team=row["team"],
                    wins=int(row["wins"]),
                    losses=int(row["losses"]),
                    games_played=int(row["games_played"]),
                    points_for=float(row["points_for"]),
                    points_against=float(row["points_against"]),
                )
            )

    if len(teams) != 30:
        raise ValueError(f"Expected 30 teams; got {len(teams)}")
    return teams


def pythag_expectation(points_for: float, points_against: float, exponent: float) -> float:
    if points_for <= 0 or points_against <= 0:
        return 0.5
    pf = math.pow(points_for, exponent)
    pa = math.pow(points_against, exponent)
    return pf / (pf + pa)


def binomial_sample(n: int, p: float, rng: random.Random) -> int:
    return sum(1 for _ in range(n) if rng.random() < p)


def simulate_regular_season(
    teams: Sequence[TeamState], exponent: float, rng: random.Random
) -> Dict[str, int]:
    final_wins: Dict[str, int] = {}
    for team in teams:
        games_remaining = max(0, TOTAL_GAMES - team.games_played)
        p = pythag_expectation(team.points_for, team.points_against, exponent)
        wins_rest = binomial_sample(games_remaining, p, rng)
        final_wins[team.team] = team.wins + wins_rest
    return final_wins


def weighted_choice(items: Sequence[str], weights: Sequence[int], rng: random.Random) -> str:
    total = sum(weights)
    draw = rng.uniform(0, total)
    cumulative = 0.0
    for item, w in zip(items, weights):
        cumulative += w
        if draw <= cumulative:
            return item
    return items[-1]


def assign_draft_order(final_wins: Dict[str, int], rng: random.Random) -> List[str]:
    # Random tie-break noise models coin flips for equal records.
    ordered = sorted(final_wins.items(), key=lambda x: (x[1], rng.random()))
    lottery_teams = [team for team, _ in ordered[:LOTTERY_TEAMS]]
    playoff_teams = [team for team, _ in ordered[LOTTERY_TEAMS:]]

    lottery_available = list(lottery_teams)
    top4: List[str] = []
    for _ in range(TOP_LOTTERY_PICKS):
        weights = [LOTTERY_TICKET_COUNTS[lottery_teams.index(team)] for team in lottery_available]
        winner = weighted_choice(lottery_available, weights, rng)
        top4.append(winner)
        lottery_available.remove(winner)

    remaining_lottery = [team for team in lottery_teams if team not in top4]

    draft_order = []
    draft_order.extend(top4)
    draft_order.extend(remaining_lottery)
    draft_order.extend(playoff_teams)

    if len(draft_order) != 30:
        raise RuntimeError(f"Draft order did not contain 30 teams: {len(draft_order)}")
    return draft_order


def run_simulations(
    teams: Sequence[TeamState],
    simulations: int,
    exponent: float,
    seed: int,
) -> Tuple[Dict[str, List[int]], Dict[str, float]]:
    rng = random.Random(seed)

    pick_counts: Dict[str, List[int]] = {team.team: [0] * 30 for team in teams}
    final_wins_total: Dict[str, float] = {team.team: 0.0 for team in teams}

    for _ in range(simulations):
        final_wins = simulate_regular_season(teams, exponent, rng)
        for team, wins in final_wins.items():
            final_wins_total[team] += wins

        draft_order = assign_draft_order(final_wins, rng)
        for idx, team in enumerate(draft_order):
            pick_counts[team][idx] += 1

    avg_wins = {team: total / simulations for team, total in final_wins_total.items()}
    return pick_counts, avg_wins


def print_all_pick_results(
    teams: Sequence[TeamState],
    pick_counts: Dict[str, List[int]],
    avg_wins: Dict[str, float],
    simulations: int,
    max_pick: int,
) -> None:
    print(f"Simulations: {simulations}")
    print("Columns show probability of landing each pick after season + lottery simulation.")
    print()

    columns = ["Team", "AvgWins"] + [f"P{p}" for p in range(1, max_pick + 1)]
    widths = [24, 8] + [6] * max_pick
    header = " ".join(f"{col:<{w}}" for col, w in zip(columns, widths))
    print(header)
    print("-" * len(header))

    for team in sorted((t.team for t in teams), key=lambda t: avg_wins[t]):
        probs = [100.0 * pick_counts[team][p - 1] / simulations for p in range(1, max_pick + 1)]
        row_values = [team, f"{avg_wins[team]:.2f}"] + [f"{x:5.2f}%" for x in probs]
        print(" ".join(f"{val:<{w}}" for val, w in zip(row_values, widths)))


def print_lottery_top4_summary(
    teams: Sequence[TeamState],
    pick_counts: Dict[str, List[int]],
    avg_wins: Dict[str, float],
    simulations: int,
    exponent: float,
    season: str,
) -> None:
    team_lookup = {team.team: team for team in teams}
    lottery_teams = sorted((team.team for team in teams), key=lambda t: avg_wins[t])[:LOTTERY_TEAMS]

    print(f"Season: {season}")
    print(f"Generated (UTC): {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Simulations: {simulations}")
    print(f"Pythagorean exponent: {exponent}")
    print()
    print("Simulated lottery teams: projected final record and odds of landing a top-4 pick")
    print()

    columns = ["Team", "Now", "Pyth%", "ProjFinal", "P1", "P2", "P3", "P4", "Top4"]
    widths = [24, 9, 7, 12, 6, 6, 6, 6, 6]
    header = " ".join(f"{col:<{w}}" for col, w in zip(columns, widths))
    print(header)
    print("-" * len(header))

    for team in lottery_teams:
        t = team_lookup[team]
        pyth = pythag_expectation(t.points_for, t.points_against, exponent)
        proj_wins = avg_wins[team]
        proj_losses = TOTAL_GAMES - proj_wins
        probs = [100.0 * pick_counts[team][i] / simulations for i in range(4)]
        top4 = sum(probs)
        row = [
            team,
            f"{t.wins}-{t.losses}",
            f"{pyth:.3f}",
            f"{proj_wins:.2f}-{proj_losses:.2f}",
            f"{probs[0]:5.2f}%",
            f"{probs[1]:5.2f}%",
            f"{probs[2]:5.2f}%",
            f"{probs[3]:5.2f}%",
            f"{top4:5.2f}%",
        ]
        print(" ".join(f"{val:<{w}}" for val, w in zip(row, widths)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Naive NBA remainder + draft lottery simulator using Pythagorean expectation."
        )
    )
    parser.add_argument("--source", choices=["sample", "live", "csv"], default="sample")
    parser.add_argument("--csv-path", default="", help="Path to CSV when --source=csv")
    parser.add_argument("--season", default=current_nba_season(), help="Season like 2025-26")
    parser.add_argument("--simulations", type=int, default=20000)
    parser.add_argument("--exponent", type=float, default=14.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-pick", type=int, default=14, help="Max pick column to print")
    parser.add_argument(
        "--http-timeout",
        type=float,
        default=60.0,
        help="HTTP timeout in seconds for live stats fetch",
    )
    parser.add_argument(
        "--http-retries",
        type=int,
        default=4,
        help="Number of fetch attempts for live stats before failing",
    )
    parser.add_argument(
        "--http-backoff-seconds",
        type=float,
        default=2.0,
        help="Base backoff delay between live fetch retries",
    )
    parser.add_argument(
        "--report",
        choices=["all-picks", "lottery-top4"],
        default="lottery-top4",
        help="Output format for terminal report",
    )
    return parser.parse_args()


def load_teams(args: argparse.Namespace) -> List[TeamState]:
    if args.source == "sample":
        return SAMPLE_TEAMS
    if args.source == "live":
        return load_live_teams(
            args.season,
            timeout_seconds=args.http_timeout,
            retries=args.http_retries,
            backoff_seconds=args.http_backoff_seconds,
        )
    if args.source == "csv":
        if not args.csv_path:
            raise ValueError("--csv-path is required when --source=csv")
        return load_teams_from_csv(args.csv_path)
    raise ValueError(f"Unsupported source: {args.source}")


def main() -> None:
    args = parse_args()
    teams = load_teams(args)
    pick_counts, avg_wins = run_simulations(
        teams=teams,
        simulations=args.simulations,
        exponent=args.exponent,
        seed=args.seed,
    )

    if args.report == "all-picks":
        print_all_pick_results(
            teams=teams,
            pick_counts=pick_counts,
            avg_wins=avg_wins,
            simulations=args.simulations,
            max_pick=args.max_pick,
        )
    else:
        print_lottery_top4_summary(
            teams=teams,
            pick_counts=pick_counts,
            avg_wins=avg_wins,
            simulations=args.simulations,
            exponent=args.exponent,
            season=args.season,
        )


if __name__ == "__main__":
    main()
