FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so this layer is cached when only source changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source.
COPY nba_sim.py ./
COPY sim ./sim
COPY app ./app
COPY serve.py ./
COPY docker-entrypoint.sh ./

RUN chmod +x docker-entrypoint.sh

# Service mode binds on this port.
EXPOSE 5000

# APP_MODE=service  → starts the Flask web server (default)
# APP_MODE=cli      → runs a single simulation and exits
ENV APP_MODE=service
# Force Python stdout/stderr to be unbuffered so output appears immediately
# in Docker logs and `docker run` output rather than being held in the I/O
# buffer until process exit.
ENV PYTHONUNBUFFERED=1

# ALB / Docker health check target.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz')" \
  || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
