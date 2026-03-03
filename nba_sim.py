#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from urllib.error import URLError
from dataclasses import dataclass
from datetime import UTC, date, datetime
from collections.abc import Mapping, Sequence

from sim.lottery import LOTTERY_TICKET_COUNTS
from sim.report import build_team_report, simulate_n_runs_with_diagnostics

TOTAL_GAMES = 82
LOTTERY_TEAMS = 14

# Headers that pass Akamai bot-detection on stats.nba.com and cdn.nba.com.
# A realistic User-Agent and Accept-Encoding are the critical fields; the
# rest mirror what a browser sends for a same-site XHR.
_NBA_REQUEST_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}
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


@dataclass(frozen=True)
class SimulationResult:
    season: str
    started_at: datetime
    finished_at: datetime
    source: str            # "live" | "sample" | "csv"
    n_sims: int
    schedule_games: int    # how many remaining games were simulated
    report: dict[str, dict[str, float | None]]


SAMPLE_TEAMS: list[TeamState] = [
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
) -> list[TeamState]:
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
    req = urllib.request.Request(url, headers=_NBA_REQUEST_HEADERS)

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

    teams: list[TeamState] = []
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


def load_teams_from_csv(path: str) -> list[TeamState]:
    teams: list[TeamState] = []
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

    normalized_known = {_normalize_team_token(team): team for team in known_teams}
    normalized_direct = _normalize_team_token(value)
    if normalized_direct in normalized_known:
        return normalized_known[normalized_direct]

    def resolve_short_name(short_name: str) -> str | None:
        if short_name in known_teams:
            return short_name
        for known in known_teams:
            normalized_known_name = _normalize_team_token(known)
            mapped_short = TEAM_NAME_ALIASES.get(normalized_known_name)
            if mapped_short == short_name:
                return known
        return None

    tricode = value.upper()
    if tricode in TRICODE_TO_TEAM:
        resolved = resolve_short_name(TRICODE_TO_TEAM[tricode])
        if resolved is not None:
            return resolved

    mapped_alias = TEAM_NAME_ALIASES.get(normalized_direct)
    if mapped_alias is not None:
        resolved = resolve_short_name(mapped_alias)
        if resolved is not None:
            return resolved
    return None


def _request_json(
    url: str,
    timeout_seconds: float,
    retries: int,
    backoff_seconds: float,
) -> Mapping[str, object]:
    req = urllib.request.Request(url, headers=_NBA_REQUEST_HEADERS)
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

            date_field = _extract_csv_field(row, date_fields)
            try:
                date_str = _parse_iso_date(date_field).isoformat() if date_field else "9999-12-31"
            except ValueError:
                date_str = "9999-12-31"
            game_id = _extract_csv_field(row, ["game_id", "id"]) or f"csv-{idx}"
            schedule.append(
                {
                    "game_id": game_id,
                    "date": date_str,
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


def _is_placeholder_live_team_obj(team_obj: Mapping[str, object] | None) -> bool:
    if not isinstance(team_obj, Mapping):
        return True
    team_id = int(team_obj.get("teamId", 0) or 0)
    tricode = str(team_obj.get("teamTricode", "")).strip()
    team_name = str(team_obj.get("teamName", "")).strip()
    team_city = str(team_obj.get("teamCity", "")).strip()
    return team_id == 0 and tricode == "" and team_name == "" and team_city == ""


def _is_finished_game(game: Mapping[str, object]) -> bool:
    status = str(game.get("gameStatus", "")).strip()
    if status == "3":
        return True
    status_text = str(game.get("gameStatusText", "")).strip().lower()
    return status_text in {"final", "postponed", "cancelled"}


def _parse_iso_date(raw: str) -> date:
    token = raw.strip()
    if not token:
        raise ValueError("empty date token")

    # Try ISO-like forms first, including datetime variants.
    iso_candidates = [token]
    if "T" in token:
        iso_candidates.append(token.split("T", 1)[0])
    if " " in token:
        iso_candidates.append(token.split(" ", 1)[0])

    seen: set[str] = set()
    for candidate in iso_candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            return date.fromisoformat(candidate)
        except ValueError:
            continue

    # Fallback for NBA static schedule feed format like "10/02/2025 00:00:00".
    for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y"):
        try:
            return datetime.strptime(token, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Unsupported date format: {raw}")


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
                if _is_placeholder_live_team_obj(home_obj if isinstance(home_obj, Mapping) else None):
                    continue
                unknown_teams.add(str(home_obj))
                continue
            if away_team is None:
                if _is_placeholder_live_team_obj(away_obj if isinstance(away_obj, Mapping) else None):
                    continue
                unknown_teams.add(str(away_obj))
                continue
            if home_team == away_team:
                continue

            game_id = str(game.get("gameId", "")).strip() or f"{block_date}-{home_team}-{away_team}"
            schedule.append(
                {
                    "game_id": game_id,
                    "date": parsed_date.isoformat(),
                    "home_team_id": home_team,
                    "away_team_id": away_team,
                }
            )

    if unknown_teams:
        sample = ", ".join(sorted(unknown_teams)[:2])
        raise RuntimeError(f"Unrecognized live schedule team identifiers: {sample}")
    return schedule



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


def build_team_meta(
    teams: Sequence[TeamState],
    *,
    source: str,
    csv_path: str = "",
) -> dict[str, dict[str, str]]:
    def conference_for_team_name(team_name: str) -> str:
        direct = TEAM_CONFERENCES.get(team_name)
        if direct in {"E", "W"}:
            return direct
        mapped_short = TEAM_NAME_ALIASES.get(_normalize_team_token(team_name))
        if mapped_short is not None:
            mapped_conf = TEAM_CONFERENCES.get(mapped_short)
            if mapped_conf in {"E", "W"}:
                return mapped_conf
        return ""

    team_meta = {team.team: {"conference": conference_for_team_name(team.team)} for team in teams}

    if source == "csv" and csv_path:
        team_meta.update(csv_team_meta(csv_path))

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
    *,
    source: str,
    schedule_csv_path: str = "",
    http_timeout: float = 60.0,
    http_retries: int = 4,
    http_backoff_seconds: float = 2.0,
) -> list[dict[str, str]]:
    known_teams = {team.team for team in teams}

    if schedule_csv_path:
        return load_schedule_from_csv(schedule_csv_path, known_teams)

    if source == "live":
        return load_live_remaining_schedule(
            timeout_seconds=http_timeout,
            retries=http_retries,
            backoff_seconds=http_backoff_seconds,
            known_teams=known_teams,
        )

    return []


def run_modular_simulations(
    teams: Sequence[TeamState],
    *,
    source: str,
    season: str,
    n_sims: int,
    seed: int | None,
    poss_per_game: float,
    hca_points: float,
    sigma_margin: float,
    top_k: int,
    explain_details: bool,
    http_timeout: float = 60.0,
    http_retries: int = 4,
    http_backoff_seconds: float = 2.0,
    schedule_csv_path: str = "",
    csv_path: str = "",
) -> SimulationResult:
    started_at = datetime.now(UTC)
    team_ids = [team.team for team in teams]
    team_meta = build_team_meta(teams, source=source, csv_path=csv_path)
    net_ratings = {team.team: team.points_for - team.points_against for team in teams}
    initial_wins = {team.team: team.wins for team in teams}
    initial_losses = {team.team: team.losses for team in teams}
    initial_ptdiff = {team.team: team.games_played * (team.points_for - team.points_against) for team in teams}

    try:
        remaining_schedule = load_remaining_schedule(
            teams,
            source=source,
            schedule_csv_path=schedule_csv_path,
            http_timeout=http_timeout,
            http_retries=http_retries,
            http_backoff_seconds=http_backoff_seconds,
        )
    except Exception:
        remaining_schedule = []

    schedule_games = len(remaining_schedule)

    sim_diagnostics = simulate_n_runs_with_diagnostics(
        team_ids=team_ids,
        team_meta=team_meta,
        remaining_schedule=remaining_schedule,
        net_ratings=net_ratings,
        initial_wins=initial_wins,
        initial_losses=initial_losses,
        initial_ptdiff=initial_ptdiff,
        n_sims=n_sims,
        rng_seed=seed,
        poss_per_game=poss_per_game,
        hca_points=hca_points,
        sigma_margin=sigma_margin,
    )
    report = build_team_report(
        sim_diagnostics.pick_counts,
        n_sims,
        top_k=top_k,
        team_diagnostics=sim_diagnostics.team_diagnostics,
        explain_details=explain_details,
    )
    finished_at = datetime.now(UTC)
    return SimulationResult(
        season=season,
        started_at=started_at,
        finished_at=finished_at,
        source=source,
        n_sims=n_sims,
        schedule_games=schedule_games,
        report=report,
    )


def print_all_pick_results_modular(
    report: Mapping[str, Mapping[str, float | None]],
    n_sims: int,
    max_pick: int,
    output_format: str,
    explain_details: bool,
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
        headers = ["team", "final_wins_mean", "expected_pick"]
        if explain_details:
            headers.extend(
                ["final_wins_p10", "final_wins_p90", "lottery_prob", "avg_slot", "p_slot_1", "p_slot_1_4"]
            )
        headers.extend([f"p_pick_{pick}" for pick in range(1, max_pick + 1)])
        writer.writerow(headers)
        for team in sorted(report):
            expected = report[team]["expected_pick"]
            final_wins_mean = report[team].get("final_wins_mean")
            row = [
                team,
                "" if final_wins_mean is None else f"{float(final_wins_mean):.4f}",
                "" if expected is None else f"{expected:.4f}",
            ]
            if explain_details:
                row.extend(
                    [
                        "" if report[team].get("final_wins_p10") is None else f"{float(report[team]['final_wins_p10']):.4f}",
                        "" if report[team].get("final_wins_p90") is None else f"{float(report[team]['final_wins_p90']):.4f}",
                        "" if report[team].get("lottery_prob") is None else f"{float(report[team]['lottery_prob']):.6f}",
                        "" if report[team].get("avg_slot") is None else f"{float(report[team]['avg_slot']):.4f}",
                        "" if report[team].get("p_slot_1") is None else f"{float(report[team]['p_slot_1']):.6f}",
                        "" if report[team].get("p_slot_1_4") is None else f"{float(report[team]['p_slot_1_4']):.6f}",
                    ]
                )
            for pick in range(1, max_pick + 1):
                value = report[team][f"p_pick_{pick}"] or 0.0
                row.append(f"{float(value):.6f}")
            writer.writerow(row)
        return

    print(f"Simulations: {n_sims}")
    print("Columns show probability of landing each pick after season + lottery simulation.")
    print()
    columns = ["Team", "FinalW Mean", "ExpPick"]
    widths = [24, 11, 8]
    if explain_details:
        columns.extend(["P10-P90", "Lot%", "AvgSlot", "Slot1%", "Slot1-4%"])
        widths.extend([9, 6, 7, 7, 8])
    columns.extend([f"P{p}" for p in range(1, max_pick + 1)])
    widths.extend([6] * max_pick)
    header = " ".join(f"{col:<{w}}" for col, w in zip(columns, widths))
    print(header)
    print("-" * len(header))

    def sort_key(team_name: str) -> tuple[float, str]:
        expected_pick = report[team_name]["expected_pick"]
        rank = float(expected_pick) if expected_pick is not None else 99.0
        return (rank, team_name)

    for team in sorted(report, key=sort_key):
        expected = report[team]["expected_pick"]
        final_wins_mean = report[team].get("final_wins_mean")
        row_values = [
            team,
            "-" if final_wins_mean is None else f"{float(final_wins_mean):.2f}",
            "-" if expected is None else f"{float(expected):.2f}",
        ]
        if explain_details:
            p10 = report[team].get("final_wins_p10")
            p90 = report[team].get("final_wins_p90")
            lottery_prob = report[team].get("lottery_prob")
            avg_slot = report[team].get("avg_slot")
            p_slot_1 = report[team].get("p_slot_1")
            p_slot_1_4 = report[team].get("p_slot_1_4")
            row_values.extend(
                [
                    "-" if p10 is None or p90 is None else f"{float(p10):.0f}-{float(p90):.0f}",
                    "-" if lottery_prob is None else f"{100.0 * float(lottery_prob):5.2f}%",
                    "-" if avg_slot is None else f"{float(avg_slot):.2f}",
                    "-" if p_slot_1 is None else f"{100.0 * float(p_slot_1):5.2f}%",
                    "-" if p_slot_1_4 is None else f"{100.0 * float(p_slot_1_4):5.2f}%",
                ]
            )
        for pick in range(1, max_pick + 1):
            row_values.append(f"{100.0 * float(report[team][f'p_pick_{pick}'] or 0.0):5.2f}%")
        print(" ".join(f"{val:<{w}}" for val, w in zip(row_values, widths)))


def print_lottery_top4_summary_modular(
    teams: Sequence[TeamState],
    report: Mapping[str, Mapping[str, float | None]],
    n_sims: int,
    season: str,
    output_format: str,
    explain_details: bool,
) -> None:
    lottery_teams = sorted(
        report.keys(),
        key=lambda t: sum(float(report[t].get(f"p_pick_{p}") or 0.0) for p in range(1, 15)),
        reverse=True,
    )[:LOTTERY_TEAMS]
    lottery_teams.sort(key=lambda t: float(report[t]["expected_pick"] or 99.0))

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
        headers = ["team", "final_wins_mean", "p_pick_1", "p_pick_2", "p_pick_3", "p_pick_4", "p_top_4", "expected_pick"]
        if explain_details:
            headers.extend(["final_wins_p10", "final_wins_p90", "lottery_prob", "avg_slot", "p_slot_1", "p_slot_1_4"])
        writer.writerow(headers)
        for team in lottery_teams:
            row = [
                team,
                "" if report[team].get("final_wins_mean") is None else f"{float(report[team]['final_wins_mean']):.4f}",
                f"{float(report[team]['p_pick_1'] or 0.0):.6f}",
                f"{float(report[team]['p_pick_2'] or 0.0):.6f}",
                f"{float(report[team]['p_pick_3'] or 0.0):.6f}",
                f"{float(report[team]['p_pick_4'] or 0.0):.6f}",
                f"{float(report[team]['p_top_4'] or 0.0):.6f}",
                "" if report[team]["expected_pick"] is None else f"{float(report[team]['expected_pick']):.4f}",
            ]
            if explain_details:
                row.extend(
                    [
                        "" if report[team].get("final_wins_p10") is None else f"{float(report[team]['final_wins_p10']):.4f}",
                        "" if report[team].get("final_wins_p90") is None else f"{float(report[team]['final_wins_p90']):.4f}",
                        "" if report[team].get("lottery_prob") is None else f"{float(report[team]['lottery_prob']):.6f}",
                        "" if report[team].get("avg_slot") is None else f"{float(report[team]['avg_slot']):.4f}",
                        "" if report[team].get("p_slot_1") is None else f"{float(report[team]['p_slot_1']):.6f}",
                        "" if report[team].get("p_slot_1_4") is None else f"{float(report[team]['p_slot_1_4']):.6f}",
                    ]
                )
            writer.writerow(row)
        return

    print(f"Season: {season}")
    print(f"Generated (UTC): {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Simulations: {n_sims}")
    print("Model: net-rating margin Monte Carlo + play-in + lottery draw")
    print()
    print("Simulated lottery teams: odds of landing a top-4 pick")
    print()

    team_lookup = {team.team: team for team in teams}
    columns = ["Team", "Now", "FinalW Mean"]
    widths = [24, 9, 11]
    if explain_details:
        columns.extend(["P10-P90", "Lot%", "AvgSlot", "Slot1%", "Slot1-4%"])
        widths.extend([9, 6, 7, 7, 8])
    columns.extend(["P1", "P2", "P3", "P4", "Top4", "ExpPick"])
    widths.extend([6, 6, 6, 6, 6, 7])
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
        final_wins_mean = report[team].get("final_wins_mean")
        row = [
            team,
            f"{state.wins}-{state.losses}",
            "-" if final_wins_mean is None else f"{float(final_wins_mean):.2f}",
        ]
        if explain_details:
            p10 = report[team].get("final_wins_p10")
            p90 = report[team].get("final_wins_p90")
            lottery_prob = report[team].get("lottery_prob")
            avg_slot = report[team].get("avg_slot")
            p_slot_1 = report[team].get("p_slot_1")
            p_slot_1_4 = report[team].get("p_slot_1_4")
            row.extend(
                [
                    "-" if p10 is None or p90 is None else f"{float(p10):.0f}-{float(p90):.0f}",
                    "-" if lottery_prob is None else f"{100.0 * float(lottery_prob):5.2f}%",
                    "-" if avg_slot is None else f"{float(avg_slot):.2f}",
                    "-" if p_slot_1 is None else f"{100.0 * float(p_slot_1):5.2f}%",
                    "-" if p_slot_1_4 is None else f"{100.0 * float(p_slot_1_4):5.2f}%",
                ]
            )
        row.extend(
            [
            f"{p1:5.2f}%",
            f"{p2:5.2f}%",
            f"{p3:5.2f}%",
            f"{p4:5.2f}%",
            f"{top4:5.2f}%",
            "-" if expected is None else f"{float(expected):.2f}",
            ]
        )
        print(" ".join(f"{val:<{w}}" for val, w in zip(row, widths)))
    if explain_details:
        print()
        print("Legend: Slot* metrics are pre-lottery slot outcomes; P1-P4/Top4 are post-draw pick outcomes.")


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
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sigma-margin", type=float, default=12.0)
    parser.add_argument("--hca-points", type=float, default=2.0)
    parser.add_argument("--poss-per-game", type=float, default=100.0)
    parser.add_argument("--top-k", type=int, default=4, help="Top-k probability for JSON reports")
    parser.add_argument("--max-pick", type=int, default=14, help="Max pick column to print")
    parser.add_argument(
        "--output-format",
        choices=["table", "json", "csv"],
        default="table",
        help="Report rendering format",
    )
    parser.add_argument(
        "--explain-details",
        action="store_true",
        help="Show expanded explanation metrics (slot/final-win diagnostics).",
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


def load_teams(args: argparse.Namespace) -> list[TeamState]:
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

    result = run_modular_simulations(
        teams,
        source=args.source,
        season=args.season,
        n_sims=args.n_sims,
        seed=args.seed,
        poss_per_game=args.poss_per_game,
        hca_points=args.hca_points,
        sigma_margin=args.sigma_margin,
        top_k=args.top_k,
        explain_details=args.explain_details,
        http_timeout=args.http_timeout,
        http_retries=args.http_retries,
        http_backoff_seconds=args.http_backoff_seconds,
        schedule_csv_path=args.schedule_csv_path,
        csv_path=args.csv_path,
    )
    if result.schedule_games == 0 and args.source == "live":
        print(
            "Warning: remaining schedule unavailable/empty; using current records only "
            "(play-in + lottery dynamics still applied).",
            file=sys.stderr,
        )
    if args.report == "all-picks":
        print_all_pick_results_modular(
            report=result.report,
            n_sims=result.n_sims,
            max_pick=args.max_pick,
            output_format=args.output_format,
            explain_details=args.explain_details,
        )
    else:
        print_lottery_top4_summary_modular(
            teams=teams,
            report=result.report,
            n_sims=result.n_sims,
            season=result.season,
            output_format=args.output_format,
            explain_details=args.explain_details,
        )


if __name__ == "__main__":
    main()
