#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
import time
import urllib.parse
import urllib.request
from urllib.error import URLError
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Dict, List, Mapping, Sequence, Tuple

from sim.lottery import LOTTERY_TICKET_COUNTS
from sim.report import build_team_report, simulate_n_runs

TOTAL_GAMES = 82
LOTTERY_TEAMS = 14
TOP_LOTTERY_PICKS = 4

TEAM_CONFERENCES: dict[str, str] = {
    "76ers": "E",
    "Bucks": "E",
    "Bulls": "E",
    "Cavaliers": "E",
    "Celtics": "E",
    "Hawks": "E",
    "Heat": "E",
    "Hornets": "E",
    "Knicks": "E",
    "Magic": "E",
    "Nets": "E",
    "Pacers": "E",
    "Pistons": "E",
    "Raptors": "E",
    "Wizards": "E",
    "Clippers": "W",
    "Grizzlies": "W",
    "Jazz": "W",
    "Kings": "W",
    "Lakers": "W",
    "Mavericks": "W",
    "Nuggets": "W",
    "Pelicans": "W",
    "Rockets": "W",
    "Spurs": "W",
    "Suns": "W",
    "Thunder": "W",
    "Timberwolves": "W",
    "Trail Blazers": "W",
    "Warriors": "W",
}

TRICODE_TO_TEAM: dict[str, str] = {
    "ATL": "Hawks",
    "BOS": "Celtics",
    "BKN": "Nets",
    "CHA": "Hornets",
    "CHI": "Bulls",
    "CLE": "Cavaliers",
    "DAL": "Mavericks",
    "DEN": "Nuggets",
    "DET": "Pistons",
    "GSW": "Warriors",
    "HOU": "Rockets",
    "IND": "Pacers",
    "LAC": "Clippers",
    "LAL": "Lakers",
    "MEM": "Grizzlies",
    "MIA": "Heat",
    "MIL": "Bucks",
    "MIN": "Timberwolves",
    "NOP": "Pelicans",
    "NYK": "Knicks",
    "OKC": "Thunder",
    "ORL": "Magic",
    "PHI": "76ers",
    "PHX": "Suns",
    "POR": "Trail Blazers",
    "SAC": "Kings",
    "SAS": "Spurs",
    "TOR": "Raptors",
    "UTA": "Jazz",
    "WAS": "Wizards",
}

TEAM_NAME_ALIASES: dict[str, str] = {
    "atlanta hawks": "Hawks",
    "boston celtics": "Celtics",
    "brooklyn nets": "Nets",
    "charlotte hornets": "Hornets",
    "chicago bulls": "Bulls",
    "cleveland cavaliers": "Cavaliers",
    "dallas mavericks": "Mavericks",
    "denver nuggets": "Nuggets",
    "detroit pistons": "Pistons",
    "golden state warriors": "Warriors",
    "houston rockets": "Rockets",
    "indiana pacers": "Pacers",
    "la clippers": "Clippers",
    "los angeles clippers": "Clippers",
    "la lakers": "Lakers",
    "los angeles lakers": "Lakers",
    "memphis grizzlies": "Grizzlies",
    "miami heat": "Heat",
    "milwaukee bucks": "Bucks",
    "minnesota timberwolves": "Timberwolves",
    "new orleans pelicans": "Pelicans",
    "new york knicks": "Knicks",
    "oklahoma city thunder": "Thunder",
    "orlando magic": "Magic",
    "philadelphia 76ers": "76ers",
    "phoenix suns": "Suns",
    "portland trail blazers": "Trail Blazers",
    "sacramento kings": "Kings",
    "san antonio spurs": "Spurs",
    "toronto raptors": "Raptors",
    "utah jazz": "Jazz",
    "washington wizards": "Wizards",
}


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


def _normalize_team_token(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _canonical_team_name(raw_value: str, known_teams: set[str]) -> str | None:
    value = raw_value.strip()
    if value in known_teams:
        return value

    tricode = value.upper()
    if tricode in TRICODE_TO_TEAM:
        mapped = TRICODE_TO_TEAM[tricode]
        if mapped in known_teams:
            return mapped

    normalized = _normalize_team_token(value)
    mapped_alias = TEAM_NAME_ALIASES.get(normalized)
    if mapped_alias in known_teams:
        return mapped_alias
    return None


def _request_json(
    url: str,
    timeout_seconds: float,
    retries: int,
    backoff_seconds: float,
) -> Mapping[str, object]:
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
    attempts = max(1, retries)
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, Mapping):
                raise RuntimeError(f"Unexpected JSON payload type: {type(payload)}")
            return payload
        except (TimeoutError, URLError, ValueError) as exc:
            last_error = exc
            if attempt >= attempts:
                raise RuntimeError(
                    f"Failed to fetch JSON after {attempts} attempts "
                    f"(timeout={timeout_seconds}s): {exc}"
                ) from exc
            time.sleep(backoff_seconds * attempt)
    raise RuntimeError(f"Failed to fetch JSON: {last_error}")


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "t", "yes", "y"}


def _extract_csv_field(row: Mapping[str, str], keys: Sequence[str]) -> str | None:
    for key in keys:
        if key in row and row[key] is not None and str(row[key]).strip() != "":
            return str(row[key]).strip()
    return None


def load_schedule_from_csv(path: str, known_teams: set[str]) -> list[dict[str, str]]:
    schedule: list[dict[str, str]] = []
    unknown_teams: set[str] = set()

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        home_fields = ["home_team_id", "home_team", "home", "home_team_name"]
        away_fields = ["away_team_id", "away_team", "away", "away_team_name"]
        date_fields = ["date", "game_date", "scheduled_date"]
        has_completion_status = bool({"is_completed", "completed", "final", "status"} & fields)

        if not any(field in fields for field in home_fields):
            raise ValueError("Schedule CSV missing home team column")
        if not any(field in fields for field in away_fields):
            raise ValueError("Schedule CSV missing away team column")

        for idx, row in enumerate(reader, start=1):
            if has_completion_status:
                completed_raw = _extract_csv_field(row, ["is_completed", "completed", "final"])
                status_raw = _extract_csv_field(row, ["status"])
                is_completed = completed_raw is not None and _parse_bool(completed_raw)
                is_final = status_raw is not None and status_raw.lower() in {"final", "postponed", "cancelled"}
                if is_completed or is_final:
                    continue

            home_raw = _extract_csv_field(row, home_fields)
            away_raw = _extract_csv_field(row, away_fields)
            if not home_raw or not away_raw:
                continue

            home_team = _canonical_team_name(home_raw, known_teams)
            away_team = _canonical_team_name(away_raw, known_teams)
            if home_team is None:
                unknown_teams.add(home_raw)
                continue
            if away_team is None:
                unknown_teams.add(away_raw)
                continue
            if home_team == away_team:
                continue

            date_raw = _extract_csv_field(row, date_fields) or "9999-12-31"
            game_id = _extract_csv_field(row, ["game_id", "id"]) or f"csv-{idx}"
            schedule.append(
                {
                    "game_id": game_id,
                    "date": date_raw,
                    "home_team_id": home_team,
                    "away_team_id": away_team,
                }
            )

    if unknown_teams:
        sample = ", ".join(sorted(unknown_teams)[:3])
        raise ValueError(f"Unknown team names in schedule CSV: {sample}")
    return schedule


def _team_name_from_live_schedule_team_obj(
    team_obj: Mapping[str, object] | None,
    known_teams: set[str],
) -> str | None:
    if not team_obj:
        return None
    tricode = str(team_obj.get("teamTricode", "")).strip()
    if tricode:
        mapped = _canonical_team_name(tricode, known_teams)
        if mapped is not None:
            return mapped

    team_name = str(team_obj.get("teamName", "")).strip()
    if team_name:
        mapped = _canonical_team_name(team_name, known_teams)
        if mapped is not None:
            return mapped

    city = str(team_obj.get("teamCity", "")).strip()
    full_name = f"{city} {team_name}".strip()
    if full_name:
        return _canonical_team_name(full_name, known_teams)
    return None


def _is_finished_game(game: Mapping[str, object]) -> bool:
    status = str(game.get("gameStatus", "")).strip()
    if status == "3":
        return True
    status_text = str(game.get("gameStatusText", "")).strip().lower()
    return status_text in {"final", "postponed", "cancelled"}


def _parse_iso_date(raw: str) -> date:
    token = raw.strip()
    if "T" in token:
        token = token.split("T", 1)[0]
    return date.fromisoformat(token)


def load_live_remaining_schedule(
    timeout_seconds: float,
    retries: int,
    backoff_seconds: float,
    known_teams: set[str],
) -> list[dict[str, str]]:
    urls = [
        "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json",
        "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json",
    ]
    payload: Mapping[str, object] | None = None
    errors: list[str] = []
    for url in urls:
        try:
            payload = _request_json(url, timeout_seconds, retries, backoff_seconds)
            break
        except RuntimeError as exc:
            errors.append(str(exc))
    if payload is None:
        raise RuntimeError("Unable to fetch live schedule feed. " + " | ".join(errors[:2]))

    league_schedule = payload.get("leagueSchedule")
    if not isinstance(league_schedule, Mapping):
        raise RuntimeError("Unexpected live schedule payload: missing leagueSchedule")
    game_dates = league_schedule.get("gameDates")
    if not isinstance(game_dates, Sequence):
        raise RuntimeError("Unexpected live schedule payload: missing gameDates")

    today = datetime.now(UTC).date()
    schedule: list[dict[str, str]] = []
    unknown_teams: set[str] = set()

    for block in game_dates:
        if not isinstance(block, Mapping):
            continue
        block_date = str(block.get("gameDate", "")).strip()
        if not block_date:
            continue
        try:
            parsed_date = _parse_iso_date(block_date)
        except ValueError:
            continue
        if parsed_date < today:
            continue

        games = block.get("games")
        if not isinstance(games, Sequence):
            continue
        for game in games:
            if not isinstance(game, Mapping):
                continue
            if _is_finished_game(game):
                continue

            home_obj = game.get("homeTeam")
            away_obj = game.get("awayTeam")
            home_team = _team_name_from_live_schedule_team_obj(
                home_obj if isinstance(home_obj, Mapping) else None,
                known_teams,
            )
            away_team = _team_name_from_live_schedule_team_obj(
                away_obj if isinstance(away_obj, Mapping) else None,
                known_teams,
            )
            if home_team is None:
                unknown_teams.add(str(home_obj))
                continue
            if away_team is None:
                unknown_teams.add(str(away_obj))
                continue
            if home_team == away_team:
                continue

            game_id = str(game.get("gameId", "")).strip() or f"{block_date}-{home_team}-{away_team}"
            schedule.append(
                {
                    "game_id": game_id,
                    "date": block_date,
                    "home_team_id": home_team,
                    "away_team_id": away_team,
                }
            )

    if unknown_teams:
        sample = ", ".join(sorted(unknown_teams)[:2])
        raise RuntimeError(f"Unrecognized live schedule team identifiers: {sample}")
    return schedule


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


def _normalize_conference(value: str) -> str | None:
    conf = value.strip().upper()
    if conf in {"E", "EAST", "EASTERN"}:
        return "E"
    if conf in {"W", "WEST", "WESTERN"}:
        return "W"
    return None


def csv_team_meta(path: str) -> dict[str, dict[str, str]]:
    team_meta: dict[str, dict[str, str]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        if "conference" not in fields:
            return team_meta
        for row in reader:
            team = str(row["team"])
            conference_raw = str(row["conference"])
            conference = _normalize_conference(conference_raw)
            if conference is not None:
                team_meta[team] = {"conference": conference}
    return team_meta


def build_team_meta(teams: Sequence[TeamState], args: argparse.Namespace) -> dict[str, dict[str, str]]:
    team_meta = {team.team: {"conference": TEAM_CONFERENCES.get(team.team, "")} for team in teams}

    if args.source == "csv" and args.csv_path:
        team_meta.update(csv_team_meta(args.csv_path))

    missing = [team for team in team_meta if team_meta[team].get("conference") not in {"E", "W"}]
    if missing:
        preview = ", ".join(sorted(missing)[:3])
        raise ValueError(
            "Conference metadata missing for team(s): "
            f"{preview}. For --source=csv, add a 'conference' column."
        )
    return team_meta


def load_remaining_schedule(
    teams: Sequence[TeamState],
    args: argparse.Namespace,
) -> list[dict[str, str]]:
    known_teams = {team.team for team in teams}

    if args.schedule_csv_path:
        return load_schedule_from_csv(args.schedule_csv_path, known_teams)

    if args.source == "live":
        return load_live_remaining_schedule(
            timeout_seconds=args.http_timeout,
            retries=args.http_retries,
            backoff_seconds=args.http_backoff_seconds,
            known_teams=known_teams,
        )

    if args.source == "csv":
        return []

    return []


def run_modular_simulations(
    teams: Sequence[TeamState],
    args: argparse.Namespace,
) -> dict[str, dict[str, float | None]]:
    team_ids = [team.team for team in teams]
    team_meta = build_team_meta(teams, args)
    net_ratings = {team.team: team.points_for - team.points_against for team in teams}
    initial_wins = {team.team: team.wins for team in teams}
    initial_losses = {team.team: team.losses for team in teams}
    initial_ptdiff = {team.team: team.points_for - team.points_against for team in teams}

    remaining_schedule: list[dict[str, str]]
    try:
        remaining_schedule = load_remaining_schedule(teams, args)
    except Exception as exc:
        print(
            "Warning: failed to load remaining schedule; falling back to current-record simulation "
            f"(play-in + lottery only). Reason: {exc}",
            file=sys.stderr,
        )
        remaining_schedule = []

    if not remaining_schedule:
        print(
            "Warning: remaining schedule unavailable/empty; using current records only "
            "(play-in + lottery dynamics still applied).",
            file=sys.stderr,
        )

    pick_counts = simulate_n_runs(
        team_ids=team_ids,
        team_meta=team_meta,
        remaining_schedule=remaining_schedule,
        net_ratings=net_ratings,
        initial_wins=initial_wins,
        initial_losses=initial_losses,
        initial_ptdiff=initial_ptdiff,
        n_sims=args.n_sims,
        rng_seed=args.seed,
        poss_per_game=args.poss_per_game,
        hca_points=args.hca_points,
        sigma_margin=args.sigma_margin,
    )
    return build_team_report(pick_counts, args.n_sims, top_k=args.top_k)


def print_all_pick_results_modular(
    teams: Sequence[TeamState],
    report: Mapping[str, Mapping[str, float | None]],
    n_sims: int,
    max_pick: int,
    output_format: str,
) -> None:
    if output_format == "json":
        payload = {
            "simulations": n_sims,
            "report": {team: report[team] for team in sorted(report)},
        }
        print(json.dumps(payload, sort_keys=True, indent=2))
        return

    if output_format == "csv":
        writer = csv.writer(sys.stdout)
        headers = ["team", "expected_pick"] + [f"p_pick_{pick}" for pick in range(1, max_pick + 1)]
        writer.writerow(headers)
        for team in sorted(report):
            expected = report[team]["expected_pick"]
            row = [team, "" if expected is None else f"{expected:.4f}"]
            for pick in range(1, max_pick + 1):
                value = report[team][f"p_pick_{pick}"] or 0.0
                row.append(f"{float(value):.6f}")
            writer.writerow(row)
        return

    print(f"Simulations: {n_sims}")
    print("Columns show probability of landing each pick after season + lottery simulation.")
    print()
    columns = ["Team", "ExpPick"] + [f"P{p}" for p in range(1, max_pick + 1)]
    widths = [24, 8] + [6] * max_pick
    header = " ".join(f"{col:<{w}}" for col, w in zip(columns, widths))
    print(header)
    print("-" * len(header))

    def sort_key(team_name: str) -> tuple[float, str]:
        expected_pick = report[team_name]["expected_pick"]
        rank = float(expected_pick) if expected_pick is not None else 99.0
        return (rank, team_name)

    for team in sorted(report, key=sort_key):
        expected = report[team]["expected_pick"]
        row_values = [team, "-" if expected is None else f"{float(expected):.2f}"]
        for pick in range(1, max_pick + 1):
            row_values.append(f"{100.0 * float(report[team][f'p_pick_{pick}'] or 0.0):5.2f}%")
        print(" ".join(f"{val:<{w}}" for val, w in zip(row_values, widths)))


def print_lottery_top4_summary_modular(
    teams: Sequence[TeamState],
    report: Mapping[str, Mapping[str, float | None]],
    n_sims: int,
    season: str,
    output_format: str,
) -> None:
    lottery_teams = sorted((team.team for team in teams), key=lambda t: (next(x.wins for x in teams if x.team == t), t))[
        :LOTTERY_TEAMS
    ]

    if output_format == "json":
        payload = {
            "season": season,
            "generated_utc": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
            "simulations": n_sims,
            "lottery_teams": lottery_teams,
            "report": {team: report[team] for team in lottery_teams},
        }
        print(json.dumps(payload, sort_keys=True, indent=2))
        return

    if output_format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(["team", "p_pick_1", "p_pick_2", "p_pick_3", "p_pick_4", "p_top_4", "expected_pick"])
        for team in lottery_teams:
            writer.writerow(
                [
                    team,
                    f"{float(report[team]['p_pick_1'] or 0.0):.6f}",
                    f"{float(report[team]['p_pick_2'] or 0.0):.6f}",
                    f"{float(report[team]['p_pick_3'] or 0.0):.6f}",
                    f"{float(report[team]['p_pick_4'] or 0.0):.6f}",
                    f"{float(report[team]['p_top_4'] or 0.0):.6f}",
                    "" if report[team]["expected_pick"] is None else f"{float(report[team]['expected_pick']):.4f}",
                ]
            )
        return

    print(f"Season: {season}")
    print(f"Generated (UTC): {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Simulations: {n_sims}")
    print("Model: net-rating margin Monte Carlo + play-in + lottery draw")
    print()
    print("Simulated lottery teams: odds of landing a top-4 pick")
    print()

    team_lookup = {team.team: team for team in teams}
    columns = ["Team", "Now", "P1", "P2", "P3", "P4", "Top4", "ExpPick"]
    widths = [24, 9, 6, 6, 6, 6, 6, 7]
    header = " ".join(f"{col:<{w}}" for col, w in zip(columns, widths))
    print(header)
    print("-" * len(header))
    for team in lottery_teams:
        state = team_lookup[team]
        p1 = 100.0 * float(report[team]["p_pick_1"] or 0.0)
        p2 = 100.0 * float(report[team]["p_pick_2"] or 0.0)
        p3 = 100.0 * float(report[team]["p_pick_3"] or 0.0)
        p4 = 100.0 * float(report[team]["p_pick_4"] or 0.0)
        top4 = 100.0 * float(report[team]["p_top_4"] or 0.0)
        expected = report[team]["expected_pick"]
        row = [
            team,
            f"{state.wins}-{state.losses}",
            f"{p1:5.2f}%",
            f"{p2:5.2f}%",
            f"{p3:5.2f}%",
            f"{p4:5.2f}%",
            f"{top4:5.2f}%",
            "-" if expected is None else f"{float(expected):.2f}",
        ]
        print(" ".join(f"{val:<{w}}" for val, w in zip(row, widths)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "NBA season + lottery simulator (default: net-rating margin Monte Carlo)."
        )
    )
    parser.add_argument("--source", choices=["sample", "live", "csv"], default="sample")
    parser.add_argument("--csv-path", default="", help="Path to CSV when --source=csv")
    parser.add_argument(
        "--schedule-csv-path",
        default="",
        help="Optional path to remaining schedule CSV (home/away/date columns)",
    )
    parser.add_argument("--season", default=current_nba_season(), help="Season like 2025-26")
    parser.add_argument("--n-sims", type=int, default=20000, help="Number of Monte Carlo runs")
    parser.add_argument(
        "--simulations",
        type=int,
        default=None,
        help="Deprecated alias for --n-sims",
    )
    parser.add_argument("--exponent", type=float, default=14.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sigma-margin", type=float, default=12.0)
    parser.add_argument("--hca-points", type=float, default=2.0)
    parser.add_argument("--poss-per-game", type=float, default=100.0)
    parser.add_argument("--top-k", type=int, default=4, help="Top-k probability for JSON reports")
    parser.add_argument("--max-pick", type=int, default=14, help="Max pick column to print")
    parser.add_argument(
        "--mode",
        choices=["modular", "legacy"],
        default="modular",
        help="Simulation engine mode (modular is default)",
    )
    parser.add_argument(
        "--output-format",
        choices=["table", "json", "csv"],
        default="table",
        help="Report rendering format",
    )
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
        help="Report type to print",
    )
    args = parser.parse_args()
    if args.simulations is not None:
        args.n_sims = args.simulations
    return args


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

    if args.mode == "legacy":
        pick_counts, avg_wins = run_simulations(
            teams=teams,
            simulations=args.n_sims,
            exponent=args.exponent,
            seed=args.seed,
        )
        if args.report == "all-picks":
            print_all_pick_results(
                teams=teams,
                pick_counts=pick_counts,
                avg_wins=avg_wins,
                simulations=args.n_sims,
                max_pick=args.max_pick,
            )
        else:
            print_lottery_top4_summary(
                teams=teams,
                pick_counts=pick_counts,
                avg_wins=avg_wins,
                simulations=args.n_sims,
                exponent=args.exponent,
                season=args.season,
            )
    else:
        report = run_modular_simulations(teams, args)
        if args.report == "all-picks":
            print_all_pick_results_modular(
                teams=teams,
                report=report,
                n_sims=args.n_sims,
                max_pick=args.max_pick,
                output_format=args.output_format,
            )
        else:
            print_lottery_top4_summary_modular(
                teams=teams,
                report=report,
                n_sims=args.n_sims,
                season=args.season,
                output_format=args.output_format,
            )


if __name__ == "__main__":
    main()
