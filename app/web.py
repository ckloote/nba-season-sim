"""Flask application factory for the NBA sim service."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Flask, jsonify, render_template

from nba_sim import (
    SAMPLE_TEAMS,
    current_nba_season,
    load_live_teams,
    run_modular_simulations,
)
from app.scheduler import DailyScheduler
from app.storage import fetch_latest_run, has_run_today, init_db, insert_run, insert_team_odds

logger = logging.getLogger(__name__)

_LOTTERY_TEAMS = 14


def _make_job(conn, source, season, n_sims, seed, http_timeout, http_retries, http_backoff):
    """Return a zero-argument callable that runs one simulation and persists it."""

    def _job() -> None:
        logger.info(
            "Simulation job starting (source=%s, season=%s, n_sims=%d)", source, season, n_sims
        )
        if source == "live":
            teams = load_live_teams(
                season,
                timeout_seconds=http_timeout,
                retries=http_retries,
                backoff_seconds=http_backoff,
            )
        else:
            teams = SAMPLE_TEAMS

        result = run_modular_simulations(
            teams,
            source=source,
            season=season,
            n_sims=n_sims,
            seed=seed,
            poss_per_game=100.0,
            hca_points=2.0,
            sigma_margin=12.0,
            top_k=4,
            explain_details=True,
            http_timeout=http_timeout,
            http_retries=http_retries,
            http_backoff_seconds=http_backoff,
        )
        run_id = insert_run(conn, result)
        insert_team_odds(conn, run_id, result.report)
        logger.info(
            "Simulation job stored (run_id=%d, schedule_games=%d)", run_id, result.schedule_games
        )

    return _job


def create_app() -> Flask:
    """Create and configure the Flask application.

    All configuration is read from environment variables:

    DB_PATH              Path to SQLite file          (default: nba_sim.db)
    SIM_SOURCE           live | sample                (default: live)
    SIM_N_SIMS           Monte Carlo iterations       (default: 20000)
    SIM_SEED             RNG seed, empty = random     (default: empty)
    SCHEDULE_UTC_HOUR    Hour to fire daily job (UTC) (default: 8)
    HTTP_TIMEOUT         Seconds per HTTP attempt     (default: 60)
    HTTP_RETRIES         Retry attempts for live API  (default: 4)
    HTTP_BACKOFF_SECONDS Base backoff between retries (default: 2.0)
    """
    db_path = os.environ.get("DB_PATH", "nba_sim.db")
    source = os.environ.get("SIM_SOURCE", "live")
    n_sims = int(os.environ.get("SIM_N_SIMS", "20000"))
    seed_env = os.environ.get("SIM_SEED", "").strip()
    seed = int(seed_env) if seed_env else None
    http_timeout = float(os.environ.get("HTTP_TIMEOUT", "60"))
    http_retries = int(os.environ.get("HTTP_RETRIES", "4"))
    http_backoff = float(os.environ.get("HTTP_BACKOFF_SECONDS", "2.0"))

    conn = init_db(db_path)
    season = current_nba_season()

    job = _make_job(conn, source, season, n_sims, seed, http_timeout, http_retries, http_backoff)
    scheduler = DailyScheduler(
        job,
        is_today_done=lambda: has_run_today(conn, season),
    )
    scheduler.start(skip_if_ran_today=lambda: has_run_today(conn, season))

    # Flask looks for templates relative to this file's directory.
    template_dir = Path(__file__).parent / "templates"
    app = Flask(__name__, template_folder=str(template_dir))

    # Store shared state on the app object for access inside route handlers.
    app.extensions["conn"] = conn
    app.extensions["scheduler"] = scheduler
    app.extensions["season"] = season

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @app.get("/healthz")
    def healthz():
        return jsonify({"status": "ok"}), 200

    @app.get("/status")
    def status():
        run = fetch_latest_run(conn)
        last = None
        if run:
            last = {
                "run_id": run["run_id"],
                "finished_at": run["finished_at"],
                "n_sims": run["n_sims"],
                "source": run["source"],
                "schedule_games": run["schedule_games"],
            }
        return jsonify({"season": season, "last_run": last}), 200

    @app.get("/api/latest")
    def api_latest():
        run = fetch_latest_run(conn)
        if run is None:
            return jsonify({"error": "no simulation data available yet"}), 404
        return jsonify(run), 200

    @app.post("/admin/rerun")
    def admin_rerun():
        if not scheduler.trigger_now():
            return jsonify({"error": "simulation already in flight"}), 409
        return jsonify({"status": "accepted"}), 202

    @app.get("/")
    def index():
        run = fetch_latest_run(conn)
        lottery_teams: list[tuple[str, dict]] = []
        if run:
            report = run["report"]
            ranked = sorted(
                report.items(),
                key=lambda kv: sum(kv[1].get(f"p_pick_{p}") or 0.0 for p in range(1, 15)),
                reverse=True,
            )[:_LOTTERY_TEAMS]
            ranked.sort(key=lambda kv: float(kv[1].get("expected_pick") or 99.0))
            lottery_teams = ranked
        return render_template("index.html", season=season, run=run, lottery_teams=lottery_teams)

    return app
