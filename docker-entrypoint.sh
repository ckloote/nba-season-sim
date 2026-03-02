#!/usr/bin/env sh
# Docker entrypoint for the NBA sim container.
#
# APP_MODE=service (default)
#   Starts the Flask web server (serve.py).
#   All configuration is read from environment variables — see README.
#
# APP_MODE=cli
#   Runs a single simulation via the CLI and exits.
#   Useful for one-shot runs, cron jobs, or local testing without a server.

set -eu

MODE="${APP_MODE:-service}"

if [ "$MODE" = "cli" ]; then
  exec python nba_sim.py \
    --source "${SIM_SOURCE:-live}" \
    --n-sims "${SIM_N_SIMS:-20000}" \
    --seed "${SIM_SEED:-42}" \
    --season "${SEASON:-}" \
    --report "${REPORT:-lottery-top4}" \
    --output-format "${OUTPUT_FORMAT:-table}" \
    ${CSV_PATH:+--csv-path "$CSV_PATH"} \
    ${SCHEDULE_CSV_PATH:+--schedule-csv-path "$SCHEDULE_CSV_PATH"} \
    ${EXTRA_ARGS:-}
fi

exec gunicorn \
  --workers 1 \
  --bind "0.0.0.0:${PORT:-5000}" \
  "app.web:create_app()"
