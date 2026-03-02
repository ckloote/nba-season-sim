#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
APP_DIR="${APP_DIR:-$SCRIPT_DIR}"

run_once() {
  echo "============================================================"
  echo "Run timestamp (UTC): $(date -u '+%Y-%m-%d %H:%M:%S')"
  python3 "$APP_DIR/nba_sim.py" \
    --source "${SOURCE:-live}" \
    --csv-path "${CSV_PATH:-}" \
    --schedule-csv-path "${SCHEDULE_CSV_PATH:-}" \
    --season "${SEASON:-$(python3 - <<'PY'
from datetime import datetime, UTC
now = datetime.now(UTC)
start = now.year if now.month >= 10 else now.year - 1
print(f"{start}-{str(start+1)[-2:]}")
PY
)}" \
    --n-sims "${N_SIMS:-${SIMULATIONS:-100000}}" \
    --sigma-margin "${SIGMA_MARGIN:-12.0}" \
    --hca-points "${HCA_POINTS:-2.0}" \
    --poss-per-game "${POSS_PER_GAME:-100.0}" \
    --top-k "${TOP_K:-4}" \
    --seed "${SEED:-42}" \
    --report "${REPORT:-lottery-top4}" \
    --output-format "${OUTPUT_FORMAT:-table}" \
    ${EXTRA_ARGS:-}
}

MODE="${RUN_MODE:-daily}"
INTERVAL="${RUN_INTERVAL_SECONDS:-86400}"

if [ "$MODE" = "once" ]; then
  run_once
  exit 0
fi

while true; do
  run_once || echo "Run failed; retrying in ${INTERVAL}s"
  sleep "$INTERVAL"
done
