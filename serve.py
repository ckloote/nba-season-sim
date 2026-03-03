#!/usr/bin/env python3
"""Entry point: start the NBA sim web service.

Usage:
    .venv/bin/python serve.py

Environment variables (all optional):
    PORT                 HTTP port to bind          (default: 5000)
    DB_PATH              SQLite file path           (default: nba_sim.db)
    SIM_SOURCE           live | sample              (default: live)
    SIM_N_SIMS           Monte Carlo iterations     (default: 20000)
    SIM_SEED             RNG seed, empty = random   (default: empty)
    SCHEDULE_UTC_HOUR    Hour to auto-run (UTC)     (default: 8)
    HTTP_TIMEOUT         Seconds per HTTP attempt   (default: 60)
    HTTP_RETRIES         Live API retry count       (default: 4)
    HTTP_BACKOFF_SECONDS Backoff base in seconds    (default: 2.0)
"""
from __future__ import annotations

import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

from app.web import create_app  # noqa: E402 — after logging config

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", "5000"))
    # use_reloader=False keeps a single scheduler thread; reloader forks the process.
    app.run(host="0.0.0.0", port=port, use_reloader=False)
