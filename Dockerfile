FROM python:3.12-slim

WORKDIR /app

COPY nba_sim.py ./
COPY sim ./sim
COPY run_daily.sh ./

ENTRYPOINT ["/app/run_daily.sh"]
