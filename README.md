# NBA Season + Lottery Simulator

Monte Carlo simulator for NBA end-of-season lottery odds. Given current team standings, it simulates the remaining schedule, play-in tournament, and NBA lottery draw thousands of times to produce pick probability distributions for every team.

**Model pipeline:**
- Remaining games simulated using a net-rating margin model (points differential → win probability)
- Conference seeds determined with head-to-head, conference record, and point-differential tiebreakers
- Play-in brackets simulated in both conferences
- Lottery draws for picks 1–4 use official NBA weighted odds
- Pick probabilities and expected pick aggregated across all runs

Can run as a **one-shot CLI** or as a **persistent web service** that automatically runs daily and serves results over HTTP.

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## CLI Mode

Run a simulation and print results to stdout:

```bash
# Sample data (no network required)
python3 nba_sim.py --source sample --n-sims 20000 --report lottery-top4

# Live data from stats.nba.com
python3 nba_sim.py --source live --n-sims 100000 --report lottery-top4

# All 30 teams, JSON output
python3 nba_sim.py --source live --report all-picks --output-format json

# CSV output with expanded diagnostics
python3 nba_sim.py --source sample --report lottery-top4 --output-format csv --explain-details

# Custom team data from CSV
python3 nba_sim.py --source csv --csv-path teams.csv --report lottery-top4

# Custom team + schedule CSVs
python3 nba_sim.py --source csv --csv-path teams.csv --schedule-csv-path remaining_schedule.csv
```

### CLI Options

| Flag | Default | Description |
|---|---|---|
| `--source` | `sample` | `live`, `sample`, or `csv` |
| `--csv-path` | — | Team stats CSV (required when `--source csv`) |
| `--schedule-csv-path` | — | Remaining schedule CSV (optional) |
| `--season` | current season | Season string e.g. `2025-26` |
| `--n-sims` | `20000` | Monte Carlo iterations |
| `--seed` | `42` | RNG seed |
| `--report` | `lottery-top4` | `lottery-top4` or `all-picks` |
| `--output-format` | `table` | `table`, `json`, or `csv` |
| `--max-pick` | `14` | Max pick column for `all-picks` table |
| `--explain-details` | off | Show slot/win-distribution diagnostics |
| `--sigma-margin` | `12.0` | Score margin std deviation |
| `--hca-points` | `2.0` | Home court advantage (points) |
| `--poss-per-game` | `100.0` | Possessions per game |
| `--top-k` | `4` | Top-k probability included in JSON report |
| `--http-timeout` | `60.0` | HTTP timeout for live data fetches (seconds) |
| `--http-retries` | `4` | Retry attempts for live API calls |
| `--http-backoff-seconds` | `2.0` | Base backoff between retries |

### Run Tests

```bash
python3 -m unittest discover -s tests -v
```

---

## Service Mode

Runs a Flask web server that automatically executes a simulation once per day at a configured UTC hour and serves the results over HTTP.

```bash
# Sample data (no network required, good for testing)
SIM_SOURCE=sample SIM_N_SIMS=500 .venv/bin/python serve.py

# Live data (default setup)
SIM_SOURCE=live .venv/bin/python serve.py
```

Then open `http://localhost:5000` in a browser. If no data has run yet, click **Run Now** on the page or call `POST /admin/rerun`.

### Service Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `5000` | HTTP port to bind |
| `DB_PATH` | `nba_sim.db` | SQLite database file path |
| `SIM_SOURCE` | `live` | `live` or `sample` |
| `SIM_N_SIMS` | `20000` | Monte Carlo iterations per run |
| `SIM_SEED` | *(random)* | RNG seed; leave empty for non-deterministic runs |
| `SCHEDULE_UTC_HOUR` | `8` | UTC hour at which the daily job fires (0–23) |
| `HTTP_TIMEOUT` | `60` | Seconds per HTTP attempt for live data |
| `HTTP_RETRIES` | `4` | Retry attempts for live API calls |
| `HTTP_BACKOFF_SECONDS` | `2.0` | Base backoff between retries (seconds) |
| `ADMIN_TOKEN` | *(unset)* | When set, `POST /admin/rerun` requires `Authorization: Bearer <token>`; the Run Now button is hidden from the UI |

### API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Browser-friendly lottery odds table (current season) |
| `GET` | `/healthz` | Health check — returns `{"status":"ok"}` |
| `GET` | `/status` | Current season, last run metadata, and list of all seasons in the DB |
| `GET` | `/api/latest` | Full simulation report for the current season (JSON) |
| `GET` | `/api/season/<season>` | Full report for a historical season e.g. `/api/season/2024-25` |
| `POST` | `/admin/rerun` | Trigger an immediate simulation run; `202` if started, `409` if already running |

#### Example `/api/latest` response shape

```json
{
  "run_id": 7,
  "season": "2025-26",
  "started_at": "2026-03-01T08:00:12.345Z",
  "finished_at": "2026-03-01T08:02:47.891Z",
  "n_sims": 20000,
  "source": "live",
  "schedule_games": 312,
  "report": {
    "Jazz": {
      "final_wins_mean": 22.4,
      "p_pick_1": 0.1401,
      "p_pick_2": 0.1347,
      "p_top_4": 0.4012,
      "expected_pick": 4.21,
      ...
    },
    ...
  }
}
```

---

## Container

Build the image:

```bash
docker build -t nba-sim .
```

### Service mode (default)

Runs the web server via **gunicorn** (not the Flask dev server). `--workers 1` is intentional: the `DailyScheduler` is an in-process thread, and multiple workers would spawn duplicate schedulers writing to the same SQLite file. For this single-writer hobby app one worker is all that's needed.

Mount a volume so the SQLite database survives container restarts.

```bash
docker run -d --name nba-sim \
  -p 5000:5000 \
  -v $(pwd)/data:/data \
  -e DB_PATH=/data/nba_sim.db \
  -e SIM_SOURCE=live \
  -e SIM_N_SIMS=20000 \
  -e SCHEDULE_UTC_HOUR=8 \
  nba-sim
```

Then open `http://localhost:5000`.

### CLI mode

Runs a single simulation, prints to stdout, and exits. Useful for one-shot runs or cron jobs.

```bash
docker run --rm \
  -e APP_MODE=cli \
  -e SIM_SOURCE=live \
  -e SIM_N_SIMS=100000 \
  -e REPORT=lottery-top4 \
  nba-sim
```

### Container environment variables

| Variable | Default | Description |
|---|---|---|
| `APP_MODE` | `service` | `service` (web server) or `cli` (one-shot and exit) |
| All [service env vars](#service-environment-variables) | — | Used when `APP_MODE=service` |
| `REPORT` | `lottery-top4` | CLI only: `lottery-top4` or `all-picks` |
| `OUTPUT_FORMAT` | `table` | CLI only: `table`, `json`, or `csv` |
| `SEASON` | *(auto)* | CLI only: override season e.g. `2025-26` |
| `CSV_PATH` | — | CLI only: path to team stats CSV |
| `SCHEDULE_CSV_PATH` | — | CLI only: path to remaining schedule CSV |
| `EXTRA_ARGS` | — | CLI only: additional raw flags passed to `nba_sim.py` |

---

## Data Sources

**Live team stats** — fetched from `stats.nba.com/stats/leaguedashteamstats` (W, L, GP, PTS, OPP_PTS).

**Live remaining schedule** — fetched from `cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json`.

If schedule loading fails the simulation falls back to current records only (no remaining games simulated). The `schedule_games` field in the response will be `0` in that case.

**CSV input** — team stats and remaining schedule can both be supplied as CSVs. See column requirements below.

### Team stats CSV columns

Required: `team`, `wins`, `losses`, `games_played`, `points_for`, `points_against`
Optional: `conference` (overrides built-in conference lookup)

### Schedule CSV columns

Required: one of `home_team`/`home_team_id`/`home`, one of `away_team`/`away_team_id`/`away`
Optional: `date`, `game_id`, `is_completed`/`status` (completed games are skipped)

Team names accept full names (`Los Angeles Lakers`), short names (`Lakers`), or tricodes (`LAL`).

---

## Deployment

### Railway (recommended for hobby use)

Push the repo, set a few env vars, mount a volume — Railway handles HTTPS, auto-deploys, and health checks automatically. See [`docs/railway.md`](docs/railway.md) for the full guide.

### AWS (enterprise / self-managed)

See [`docs/runbook.md`](docs/runbook.md) for the full ECS + ALB + EFS deployment guide, including IAM roles, task definition registration, and update procedures. The task definition template is at [`deploy/task-definition.json`](deploy/task-definition.json).

---

## Notes

- Pick ownership, protections, and traded picks are not modeled.
- Play-in seeding uses win percentage; exact NBA tiebreaker rules are approximated.
- The service uses SQLite with WAL mode — safe for a single-writer setup. Not intended for concurrent writers.
- The daily scheduler fires at most once per calendar day (UTC). A manual `/admin/rerun` also counts as that day's run.
- Historical seasons are retained in the database and queryable via `/api/season/<season>`.
