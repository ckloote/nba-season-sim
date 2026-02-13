# NBA Season + Lottery Simulator (Naive)

This project simulates the remainder of the current NBA regular season with a naive model:

- Compute each team's Pythagorean expectation from points for/against.
- Use that expectation as each team's win probability in every remaining game.
- Simulate remainder-of-season wins with a binomial draw.
- Simulate lottery draws for picks 1-4 using NBA lottery weights.
- Estimate each team's draft outcomes over many Monte Carlo runs.

## Data Sources

`--source live` fetches current team stats from `stats.nba.com` (`leaguedashteamstats`), including:

- W/L and GP
- Team points per game (`PTS`)
- Opponent points per game (`OPP_PTS`)

No external Python package is required.

## Local Run

```bash
cd /home/ubuntu/nba-season-sim
python3 nba_sim.py --source sample --simulations 20000 --report lottery-top4
```

Run smoke tests:

```bash
python3 -m unittest discover -s tests -v
```

Useful options:

```bash
python3 nba_sim.py --source live --season 2025-26 --simulations 100000 --report lottery-top4
python3 nba_sim.py --source live --report all-picks --max-pick 14
python3 nba_sim.py --source csv --csv-path teams.csv --report lottery-top4
```

## Output Mode You Asked For

`--report lottery-top4` prints, for the simulated lottery teams (bottom 14 by projected final wins):

- Current record
- Pythagorean expected win rate (`Pyth%`)
- Projected final record
- Pick-by-pick odds for picks 1-4
- Total `Top4` odds (chance of landing any pick 1-4)

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
  -e SIMULATIONS=100000 \
  nba-sim
```

Run once per day (default behavior):

```bash
docker run -d --name nba-sim-daily \
  -e SOURCE=live \
  -e SIMULATIONS=100000 \
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
- `SEASON`: defaults to current season (UTC date based)
- `SIMULATIONS`: default `100000`
- `EXPONENT`: default `14.0`
- `SEED`: default `42`
- `REPORT`: `lottery-top4` (default) or `all-picks`
- `EXTRA_ARGS`: optional extra CLI flags, e.g. `"--max-pick 10"`

## Notes / Simplifications

- This is intentionally naive and not schedule-aware.
- Team win totals are simulated independently, so league-wide totals are not constrained.
- Pick ownership/protection and traded picks are not modeled yet.
