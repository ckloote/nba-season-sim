"""SQLite persistence layer for simulation runs and team odds."""
from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime

from nba_sim import SimulationResult

SCHEMA_VERSION = 1

_CREATE_RUNS = """
CREATE TABLE IF NOT EXISTS runs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    season         TEXT    NOT NULL,
    started_at     TEXT    NOT NULL,
    finished_at    TEXT    NOT NULL,
    status         TEXT    NOT NULL,
    error          TEXT,
    n_sims         INTEGER NOT NULL,
    source         TEXT    NOT NULL,
    schedule_games INTEGER NOT NULL
)
"""

_CREATE_TEAM_ODDS = """
CREATE TABLE IF NOT EXISTS team_odds (
    run_id        INTEGER NOT NULL REFERENCES runs(id),
    team          TEXT    NOT NULL,
    final_wins_mean REAL,
    final_wins_p10  REAL,
    final_wins_p90  REAL,
    lottery_prob    REAL,
    avg_slot        REAL,
    p_slot_1        REAL,
    p_slot_1_4      REAL,
    p_pick_1  REAL, p_pick_2  REAL, p_pick_3  REAL, p_pick_4  REAL,
    p_pick_5  REAL, p_pick_6  REAL, p_pick_7  REAL, p_pick_8  REAL,
    p_pick_9  REAL, p_pick_10 REAL, p_pick_11 REAL, p_pick_12 REAL,
    p_pick_13 REAL, p_pick_14 REAL,
    p_top_4       REAL,
    expected_pick REAL,
    PRIMARY KEY (run_id, team)
)
"""

_CREATE_APP_STATE = """
CREATE TABLE IF NOT EXISTS app_state (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
"""


def init_db(path: str) -> sqlite3.Connection:
    """Open (or create) the SQLite database at *path* and bootstrap the schema."""
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(_CREATE_RUNS)
    conn.execute(_CREATE_TEAM_ODDS)
    conn.execute(_CREATE_APP_STATE)
    # Record schema version if not already set.
    conn.execute(
        "INSERT OR IGNORE INTO app_state (key, value) VALUES (?, ?)",
        ("schema_version", str(SCHEMA_VERSION)),
    )
    conn.commit()
    return conn


def insert_run(conn: sqlite3.Connection, result: SimulationResult) -> int:
    """Insert a completed run row; return the new run_id."""
    cur = conn.execute(
        """
        INSERT INTO runs (season, started_at, finished_at, status, error,
                          n_sims, source, schedule_games)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result.season,
            result.started_at.isoformat(),
            result.finished_at.isoformat(),
            "ok",
            None,
            result.n_sims,
            result.source,
            result.schedule_games,
        ),
    )
    conn.commit()
    run_id = cur.lastrowid
    assert run_id is not None
    return run_id


def insert_team_odds(
    conn: sqlite3.Connection,
    run_id: int,
    report: dict[str, dict[str, float | None]],
) -> None:
    """Insert one team_odds row per team in *report*."""
    rows = []
    for team, data in report.items():
        rows.append((
            run_id,
            team,
            data.get("final_wins_mean"),
            data.get("final_wins_p10"),
            data.get("final_wins_p90"),
            data.get("lottery_prob"),
            data.get("avg_slot"),
            data.get("p_slot_1"),
            data.get("p_slot_1_4"),
            data.get("p_pick_1"),
            data.get("p_pick_2"),
            data.get("p_pick_3"),
            data.get("p_pick_4"),
            data.get("p_pick_5"),
            data.get("p_pick_6"),
            data.get("p_pick_7"),
            data.get("p_pick_8"),
            data.get("p_pick_9"),
            data.get("p_pick_10"),
            data.get("p_pick_11"),
            data.get("p_pick_12"),
            data.get("p_pick_13"),
            data.get("p_pick_14"),
            data.get("p_top_4"),
            data.get("expected_pick"),
        ))
    conn.executemany(
        """
        INSERT INTO team_odds (
            run_id, team,
            final_wins_mean, final_wins_p10, final_wins_p90,
            lottery_prob, avg_slot, p_slot_1, p_slot_1_4,
            p_pick_1, p_pick_2, p_pick_3, p_pick_4,
            p_pick_5, p_pick_6, p_pick_7, p_pick_8,
            p_pick_9, p_pick_10, p_pick_11, p_pick_12,
            p_pick_13, p_pick_14,
            p_top_4, expected_pick
        ) VALUES (
            ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?,
            ?, ?
        )
        """,
        rows,
    )
    conn.commit()


def list_seasons(conn: sqlite3.Connection) -> list[str]:
    """Return distinct seasons that have at least one successful run, newest first."""
    rows = conn.execute(
        "SELECT DISTINCT season FROM runs WHERE status = 'ok' ORDER BY season DESC"
    ).fetchall()
    return [row[0] for row in rows]


def fetch_latest_run(conn: sqlite3.Connection, season: str | None = None) -> dict | None:
    """Return the most recent successful run with its team odds, or None.

    If *season* is provided only runs for that season are considered.
    """
    if season is not None:
        row = conn.execute(
            """
            SELECT id, season, started_at, finished_at, n_sims, source, schedule_games
            FROM runs
            WHERE status = 'ok' AND season = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (season,),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT id, season, started_at, finished_at, n_sims, source, schedule_games
            FROM runs
            WHERE status = 'ok'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None

    run_id, season, started_at, finished_at, n_sims, source, schedule_games = row
    team_rows = conn.execute(
        """
        SELECT team,
               final_wins_mean, final_wins_p10, final_wins_p90,
               lottery_prob, avg_slot, p_slot_1, p_slot_1_4,
               p_pick_1, p_pick_2, p_pick_3, p_pick_4,
               p_pick_5, p_pick_6, p_pick_7, p_pick_8,
               p_pick_9, p_pick_10, p_pick_11, p_pick_12,
               p_pick_13, p_pick_14,
               p_top_4, expected_pick
        FROM team_odds
        WHERE run_id = ?
        ORDER BY team
        """,
        (run_id,),
    ).fetchall()

    cols = [
        "final_wins_mean", "final_wins_p10", "final_wins_p90",
        "lottery_prob", "avg_slot", "p_slot_1", "p_slot_1_4",
        "p_pick_1", "p_pick_2", "p_pick_3", "p_pick_4",
        "p_pick_5", "p_pick_6", "p_pick_7", "p_pick_8",
        "p_pick_9", "p_pick_10", "p_pick_11", "p_pick_12",
        "p_pick_13", "p_pick_14",
        "p_top_4", "expected_pick",
    ]
    report = {}
    for team_row in team_rows:
        team = team_row[0]
        report[team] = dict(zip(cols, team_row[1:]))

    return {
        "run_id": run_id,
        "season": season,
        "started_at": started_at,
        "finished_at": finished_at,
        "n_sims": n_sims,
        "source": source,
        "schedule_games": schedule_games,
        "report": report,
    }


def has_run_today(conn: sqlite3.Connection, season: str) -> bool:
    """Return True if a successful run for *season* already exists for today (UTC)."""
    today = datetime.now(UTC).date().isoformat()
    row = conn.execute(
        """
        SELECT 1 FROM runs
        WHERE status = 'ok'
          AND season = ?
          AND date(finished_at) = ?
        LIMIT 1
        """,
        (season, today),
    ).fetchone()
    return row is not None
