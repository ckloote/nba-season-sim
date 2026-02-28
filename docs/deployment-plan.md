# Persistent Daily Odds Service (AWS-first, Single Container, SQLite + Web UI)

## Summary
Build a production-oriented containerized web service that:
1. Runs NBA lottery simulation once daily at a fixed UTC hour.
2. Persists daily results and metadata in SQLite.
3. Serves a simple public single-page UI with latest odds.
4. Keeps trends for current season and auto-archives prior seasons at rollover.
5. Exposes basic operational endpoints (health + run status) and a protected manual rerun endpoint.

This plan targets AWS-first deployment (ECS/Fargate + ALB + persistent volume) with lightweight scripts/runbook (not full Terraform).

## Chosen Product/Infra Decisions
- Cloud target: AWS-first.
- Runtime model: single container process.
- Storage: SQLite on persistent volume.
- Daily schedule: fixed UTC hour.
- UI scope: simple single page + latest table.
- Infra output: ECS/ALB/volume deploy docs + scripts.
- Manual rerun: protected endpoint.
- Monitoring: basic health + run status + structured logs.
- Retention: current season active; prior season auto-archived at rollover.

## Architecture
- **App process**: one Python web server process that hosts API + HTML and runs an internal scheduler thread.
- **Scheduler**:
  - Computes next run at configured UTC hour.
  - Executes simulation job once/day.
  - Writes atomic snapshot + run metadata to SQLite.
- **Data model**:
  - `runs` table: run id, season, started_at, finished_at, status, error, params, source mode.
  - `team_odds` table: run id, team, current record, final_wins_mean, pick probabilities, detailed diagnostics fields.
  - `season_archive` (or archived rows by season): previous seasons retained for historical access.
  - `app_state` table: last_successful_run_id, schema version, scheduler config.
- **Web serving**:
  - `/` renders clean single-page table from latest successful run.
  - Optional compact trend hint for season-to-date deltas from stored snapshots (no charts in v1).
- **Operational endpoints**:
  - `GET /healthz` (liveness/readiness basics).
  - `GET /status` (last run timestamp/status/duration/source).
  - `POST /admin/rerun` protected by bearer token.
- **Cloud deployment**:
  - ECS service behind ALB.
  - Persistent volume mounted at app data path for SQLite durability.
  - CloudWatch logs.
  - Env-driven config for schedule, sim params, auth token, DB path.

## Implementation Breakdown

### Phase 1: App Refactor for Service Mode
1. Split simulation execution from CLI print path into reusable service function returning structured payload.
2. Add storage module (`sim/storage.py` or `app/storage.py`) with:
   - schema init/migrations
   - insert run, insert team odds rows, fetch latest run, fetch season snapshots
   - transaction boundaries
3. Add scheduler module:
   - fixed UTC hour scheduling logic
   - startup immediate-run option flag (disabled by default)
   - safe lock to avoid concurrent overlapping runs

### Phase 2: Web/API Layer
1. Add lightweight web framework (Flask or FastAPI; Flask preferred for simplicity in v1).
2. Endpoints:
   - `GET /api/latest` latest run payload (JSON)
   - `GET /api/latest/table` normalized row format for UI
   - `GET /status`
   - `GET /healthz`
   - `POST /admin/rerun` with token auth + rate limit guard (single in-flight lock)
3. HTML page:
   - server-rendered or minimal JS fetch from `/api/latest`
   - columns: `Team`, `Now`, `FinalW Mean`, `P1..P4`, `Top4`, `ExpPick`
   - “Last updated (UTC)” and run metadata banner

### Phase 3: Seasonal Retention / Archiving
1. Determine current season via existing season helper.
2. On first run of a new season:
   - archive prior season snapshots (by season field) automatically
   - current-season queries only use active season
3. Add `GET /api/season/{season}` to inspect archived seasons (optional but low effort).

### Phase 4: Container + Runtime
1. Update Docker image:
   - include web dependencies
   - entrypoint runs web service (not shell loop)
2. Env vars:
   - `APP_MODE=service|cli` (default `service`)
   - `SCHEDULE_UTC_HOUR` (int 0-23)
   - `DB_PATH` (mounted volume path)
   - existing sim settings (`SOURCE`, `N_SIMS`, `SEED`, etc.)
   - `ADMIN_TOKEN`
3. Keep CLI mode for manual/local runs and back-compat.

### Phase 5: AWS Deployment Artifacts
1. Add `deploy/` scripts/runbook:
   - ECS task definition template
   - ALB target group/health check path (`/healthz`)
   - environment variable matrix
   - EFS/EBS-backed mount guidance for SQLite path
2. Operational runbook:
   - first deploy
   - rotate admin token
   - check last run status
   - force rerun procedure

## Public Interfaces / Types to Add
- REST:
  - `GET /healthz`
  - `GET /status`
  - `GET /api/latest`
  - `POST /admin/rerun` (token required)
- Persistent schema:
  - `runs`, `team_odds`, `app_state` (+ archive approach)
- Config env:
  - `SCHEDULE_UTC_HOUR`, `DB_PATH`, `ADMIN_TOKEN`, `APP_MODE`

## Failure Modes and Handling
- Live data fetch fails:
  - run marked failed in `runs`
  - if fallback path enabled, store run as success-with-warning and annotate status
- Scheduler overlap:
  - mutex prevents concurrent runs
- SQLite lock/contention:
  - single writer pattern with short transactions; retry once on lock
- App restart:
  - scheduler recomputes next run; no duplicate same-day run if run record exists for date/season (idempotency check)

## Test Plan

### Unit Tests
- Scheduler next-run time calculation at UTC boundaries.
- Season rollover detection and archive behavior.
- Auth guard for `/admin/rerun`.
- Storage transactional writes/reads and schema bootstrap.

### Integration Tests
- Service startup initializes DB.
- Trigger one run and verify:
  - run row written
  - team_odds rows count expected
  - `/api/latest` returns latest snapshot
- Duplicate-run protection for same day/hour.
- Rerun endpoint token validation and in-flight lock behavior.

### Smoke / E2E
- Container local run with mounted volume:
  - web page loads
  - status endpoint updates after scheduled or manual rerun
- Existing CLI smoke tests remain functional in CLI mode.

## Acceptance Criteria
- Public URL serves latest odds page and shows last successful UTC timestamp.
- Service automatically refreshes once daily at configured UTC hour.
- Results persist across container restarts.
- `/status` and `/healthz` provide operational visibility.
- Manual rerun works only with valid token.
- Prior season data is automatically archived at season rollover; current season view starts clean.

## Assumptions and Defaults
- Web framework: Flask for lowest complexity.
- Default scheduler hour: `09:00 UTC` unless overridden.
- Default simulation seed remains fixed (42) for day-over-day comparability.
- Archive strategy keeps old season data queryable but excluded from default/latest endpoints.
- Initial UI prioritizes clarity over rich interactivity; iterative visual improvements follow after deployment stability.
