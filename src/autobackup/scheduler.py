from __future__ import annotations

from datetime import datetime, time as dt_time
from typing import Optional
import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from autobackup.db import SessionLocal
from autobackup.models import BackupJob
from autobackup.backup_engine import run_backup_for_job

logger = logging.getLogger(__name__)


class BackupScheduler:
    """Background scheduler that runs backup jobs automatically.

    It reads active jobs from the database and schedules them according to
    their configuration (schedule_type + interval_minutes).
    """

    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler()
        self._lock = threading.Lock()
        self._started = False

    def start(self) -> None:
        """Start the underlying APScheduler instance."""
        with self._lock:
            if self._started:
                return

            # Mark as started BEFORE calling reload()
            self._started = True

            self._scheduler.start()
            
        self.reload()
        logger.info("BackupScheduler started")

    def stop(self) -> None:
        """Stop the scheduler and cancel all scheduled jobs."""
        with self._lock:
            if not self._started:
                return

            self._scheduler.shutdown(wait=False)
            self._started = False
            logger.info("BackupScheduler stopped")

    def reload(self) -> None:
        """Reload jobs from the database and reschedule them."""
        with self._lock:
            if not self._started:
                # Scheduler not started yet; nothing to do.
                logger.debug("reload() called while scheduler is not started")
                return

            self._scheduler.remove_all_jobs()

            db = SessionLocal()
            try:
                jobs = (
                    db.query(BackupJob)
                    .filter(BackupJob.active.is_(True))
                    .all()
                )

                for job in jobs:
                    self._schedule_job(
                        job.id,
                        job.schedule_type,
                        job.interval_minutes,
                    )
            finally:
                db.close()

            logger.info("BackupScheduler reloaded all jobs")

    def _schedule_job(
        self,
        job_id: int,
        schedule_type: str,
        interval_minutes: Optional[int],
    ) -> None:
        """Create an APScheduler job for a single BackupJob."""
        schedule_type = (schedule_type or "manual").lower()

        if schedule_type == "manual":
            # Manual jobs are not scheduled automatically.
            return

        if schedule_type == "interval":
            if interval_minutes is None or interval_minutes <= 0:
                logger.warning(
                    "Job %s has invalid interval_minutes=%s; skipping scheduling",
                    job_id,
                    interval_minutes,
                )
                return

            minutes = int(interval_minutes)
            trigger = IntervalTrigger(minutes=minutes)

        elif schedule_type == "daily":
            # Simple daily job at 02:00. You can make this configurable later.
            trigger = CronTrigger(hour=2, minute=0)
        else:
            logger.warning("Job %s has unknown schedule_type=%s", job_id, schedule_type)
            return

        self._scheduler.add_job(
            self._run_job,
            trigger=trigger,
            args=[job_id],
            id=f"job_{job_id}",
            replace_existing=True,
            max_instances=1,
        )
        logger.info(
            "Scheduled job %s with schedule_type=%s",
            job_id,
            schedule_type,
        )

    def _run_job(self, job_id: int) -> None:
        """Wrapper called by APScheduler to run a backup for a given job id."""
        db = SessionLocal()
        try:
            job = db.query(BackupJob).filter_by(id=job_id).first()
            if job is None:
                logger.warning("Job %s not found; skipping scheduled run", job_id)
                return

            logger.info(
                "Starting scheduled backup for job %s (%s)",
                job.id,
                job.name,
            )
            run = run_backup_for_job(db, job)
            logger.info(
                "Finished scheduled backup for job %s with status=%s, message=%s",
                job.id,
                run.status,
                run.message,
            )
        except Exception:
            logger.exception("Error while running scheduled backup for job %s", job_id)
        finally:
            db.close()


