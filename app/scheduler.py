"""Background scheduler that fires a job once per day at a fixed UTC hour."""
from __future__ import annotations

import logging
import os
import threading
from datetime import UTC, datetime
from typing import Callable

logger = logging.getLogger(__name__)

_DEFAULT_UTC_HOUR = 8  # 08:00 UTC by default


class DailyScheduler:
    """Fires *job_fn* once per calendar day at the configured UTC hour.

    The scheduler runs in a daemon thread and uses a threading.Lock to prevent
    overlapping executions if the job runs longer than the check interval.

    Parameters
    ----------
    job_fn:
        Zero-argument callable executed once per day. Exceptions are logged
        and swallowed so the scheduler keeps running.
    utc_hour:
        UTC hour (0–23) at which to fire the job. Defaults to the
        ``SCHEDULE_UTC_HOUR`` environment variable if set, otherwise 8.
    check_interval_seconds:
        How often the background thread wakes up to check whether it's time
        to run. Defaults to 60 s (1 minute). Set lower in tests.
    """

    def __init__(
        self,
        job_fn: Callable[[], None],
        utc_hour: int | None = None,
        *,
        check_interval_seconds: float = 60.0,
        is_today_done: Callable[[], bool] | None = None,
    ) -> None:
        if utc_hour is None:
            utc_hour = int(os.environ.get("SCHEDULE_UTC_HOUR", str(_DEFAULT_UTC_HOUR)))
        if not 0 <= utc_hour <= 23:
            raise ValueError(f"utc_hour must be 0–23, got {utc_hour}")

        self._job_fn = job_fn
        self._utc_hour = utc_hour
        self._check_interval = check_interval_seconds
        self._is_today_done = is_today_done
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, *, skip_if_ran_today: Callable[[], bool] | None = None) -> None:
        """Start the background thread.

        Parameters
        ----------
        skip_if_ran_today:
            Optional callable returning True if the job has already run today.
            Checked once on startup; if True the first run is skipped to the
            next scheduled slot.
        """
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()

        already_ran = skip_if_ran_today() if skip_if_ran_today is not None else False

        self._thread = threading.Thread(
            target=self._run_loop,
            args=(already_ran,),
            daemon=True,
            name="DailyScheduler",
        )
        self._thread.start()
        logger.info(
            "Scheduler started (UTC hour=%d, already_ran_today=%s)",
            self._utc_hour,
            already_ran,
        )

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the scheduler to stop and wait for the thread to exit."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def trigger_now(self) -> bool:
        """Run the job immediately in a background thread, outside the normal schedule.

        Returns True if the job was launched, False if a run is already in flight.
        Uses the same lock as the scheduler loop so the two can never overlap.
        """
        if not self._lock.acquire(blocking=False):
            return False

        def _run() -> None:
            try:
                logger.info("Manual trigger: firing job")
                self._job_fn()
                logger.info("Manual trigger: job completed")
            except Exception:
                logger.exception("Manual trigger: job raised an exception")
            finally:
                self._lock.release()

        threading.Thread(target=_run, daemon=True, name="DailyScheduler-trigger").start()
        return True

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_loop(self, already_ran_today: bool) -> None:
        last_run_date: str | None = (
            datetime.now(UTC).date().isoformat() if already_ran_today else None
        )

        while not self._stop_event.is_set():
            now = datetime.now(UTC)
            today = now.date().isoformat()

            if now.hour == self._utc_hour and last_run_date != today:
                if self._is_today_done is not None and self._is_today_done():
                    # A manual trigger already ran today — mark done and skip.
                    last_run_date = today
                elif self._lock.acquire(blocking=False):
                    try:
                        last_run_date = today
                        logger.info("Scheduler firing job at %s", now.isoformat())
                        self._job_fn()
                        logger.info("Scheduler job completed")
                    except Exception:
                        logger.exception("Scheduler job raised an exception")
                    finally:
                        self._lock.release()
                else:
                    logger.warning("Scheduler job already in flight; skipping slot")

            self._stop_event.wait(timeout=self._check_interval)
