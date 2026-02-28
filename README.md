# NBA Season + Lottery Simulator

This project simulates NBA lottery outcomes with a Monte Carlo pipeline:

- Game outcomes come from a net-rating margin model.
- Conference seeds use approximate tiebreak logic.
- Play-in brackets are simulated in both conferences.
- Lottery draws for picks 1-4 use NBA lottery weights.
- Pick probabilities and expected pick are aggregated over many runs.

Legacy Pythagorean mode is still available via `--mode legacy`.

## Data Sources

`--source live` fetches current team stats from `stats.nba.com` (`leaguedashteamstats`), including:

- W/L and GP
- Team points per game (`PTS`)
- Opponent points per game (`OPP_PTS`)

No external Python package is required.

## Local Run

```bash
cd /home/ubuntu/nba-season-sim
python3 nba_sim.py --source sample --n-sims 20000 --report lottery-top4
```

Run smoke tests:

```bash
python3 -m unittest discover -s tests -v
```

Useful options:

```bash
python3 nba_sim.py --source live --season 2025-26 --n-sims 100000 --report lottery-top4
python3 nba_sim.py --source live --report all-picks --max-pick 14 --output-format table
python3 nba_sim.py --source sample --report all-picks --output-format json
python3 nba_sim.py --source csv --csv-path teams.csv --report lottery-top4
python3 nba_sim.py --source csv --csv-path teams.csv --schedule-csv-path remaining_schedule.csv
python3 nba_sim.py --mode legacy --source sample --simulations 20000 --report lottery-top4
```

## Output Mode You Asked For

`--report lottery-top4` prints, for the simulated lottery teams:

- Current record
- Pick-by-pick odds for picks 1-4
- Total `Top4` odds (chance of landing any pick 1-4)
- Expected pick (conditional on being in the lottery)

## Container

Build image:

```bash
cd /home/ubuntu/nba-season-sim
docker build -t nba-sim .
```

Run once and exit:

```bash
docker run --rm \
  -e RUN_MODE=once \
  -e SOURCE=live \
  -e N_SIMS=100000 \
  nba-sim
```

Run once per day (default behavior):

```bash
docker run -d --name nba-sim-daily \
  -e SOURCE=live \
  -e N_SIMS=100000 \
  -e RUN_INTERVAL_SECONDS=86400 \
  nba-sim
```

Tail logs:

```bash
docker logs -f nba-sim-daily
```

## Environment Variables (Container)

- `RUN_MODE`: `daily` (default) or `once`
- `RUN_INTERVAL_SECONDS`: default `86400`
- `SOURCE`: `live` (recommended), `sample`, or `csv`
- `CSV_PATH`: team-stats CSV path when `SOURCE=csv`
- `SCHEDULE_CSV_PATH`: optional remaining-schedule CSV path
- `SEASON`: defaults to current season (UTC date based)
- `MODE_ENGINE`: `modular` (default) or `legacy`
- `N_SIMS`: default `100000` (`SIMULATIONS` is still accepted as a compatibility alias)
- `SIGMA_MARGIN`: default `12.0`
- `HCA_POINTS`: default `2.0`
- `POSS_PER_GAME`: default `100.0`
- `TOP_K`: default `4`
- `EXPONENT`: default `14.0`
- `SEED`: default `42`
- `REPORT`: `lottery-top4` (default) or `all-picks`
- `OUTPUT_FORMAT`: `table` (default), `json`, or `csv`
- `EXTRA_ARGS`: optional extra CLI flags, e.g. `"--max-pick 10"`

## Notes / Simplifications

- Schedule loading order in modular mode:
  - use `--schedule-csv-path` if provided
  - else use live schedule feed when `--source live`
  - else no schedule (current records only)
- If schedule loading fails, the run falls back to current records and emits a warning to stderr.
- Pick ownership/protection and traded picks are not modeled yet.
