# NBA Sim — Railway Deployment Guide

Railway is the recommended platform for hobby/personal deployments. It handles HTTPS, auto-deploys on push, and supports persistent volumes — no VPC, load balancer, or IAM configuration required.

---

## 1. Create the project

1. Go to [railway.app](https://railway.app) and create a new project.
2. Choose **Deploy from GitHub repo** and connect your fork/clone of this repository.
3. Railway detects the `Dockerfile` automatically via `railway.toml`.

---

## 2. Set environment variables

In the Railway dashboard → your service → **Variables**, add:

| Variable | Value | Notes |
|---|---|---|
| `SIM_SOURCE` | `live` | Use `sample` for testing without NBA API calls |
| `SIM_N_SIMS` | `20000` | Increase for production accuracy |
| `SCHEDULE_UTC_HOUR` | `8` | UTC hour for the daily simulation run (0–23) |
| `DB_PATH` | `/data/nba_sim.db` | Must match the volume mount path below |

Optional:
| Variable | Value | Notes |
|---|---|---|
| `SIM_SEED` | *(leave empty)* | Leave unset for non-deterministic runs |
| `HTTP_TIMEOUT` | `60` | Seconds per live API attempt |
| `HTTP_RETRIES` | `4` | Retry attempts for live NBA API |

`PORT` is set automatically by Railway — do not set it manually.

---

## 3. Create a persistent volume

Without a volume the SQLite database resets on every deploy. To persist data:

1. In your Railway project, click **+ New** → **Volume**.
2. Name it `nba-sim-data` (or anything you like).
3. Set **Mount Path** to `/data`.
4. Attach it to your service.
5. Confirm `DB_PATH=/data/nba_sim.db` is set (step 2).

The schema is created automatically on first start — no manual migration needed.

---

## 4. Confirm the health check

Railway uses `GET /healthz` as the health check (configured in `railway.toml`). After deploy:

```bash
curl https://<your-app>.railway.app/healthz
# → {"status":"ok"}
```

If the health check fails, check logs (see step 6) for startup errors.

---

## 5. Trigger a manual run

The daily scheduler fires automatically at `SCHEDULE_UTC_HOUR`. To run immediately without waiting:

```bash
curl -X POST https://<your-app>.railway.app/admin/rerun
# → 202 Accepted (run started)
# → 409 Conflict (already running)
```

Or use the **Run Now** button on the homepage.

---

## 6. View logs

In the Railway dashboard → your service → **Logs** tab. Look for:

```
[scheduler] daily job started
[scheduler] daily job finished in X.Xs
```

To stream logs via CLI:

```bash
railway logs --follow
```

---

## 7. Update procedure

Push to the connected branch — Railway auto-deploys. The volume persists across deploys, so historical run data is preserved.

To redeploy without a code change (e.g., to pick up a new `SIM_N_SIMS` value):

Railway dashboard → your service → **Deploy** → **Redeploy**.

---

## Notes

- The container uses **gunicorn with 1 worker** (not the Flask dev server). One worker is intentional — the `DailyScheduler` runs as an in-process thread, and multiple workers would spawn duplicate schedulers writing to the same SQLite file.
- SQLite with WAL mode is safe for this single-writer setup. No Postgres migration is needed.
- The daily job is idempotent — even if the container restarts mid-day it will not double-run.
