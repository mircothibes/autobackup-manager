from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from autobackup.db import SessionLocal
from autobackup.models import BackupJob
from autobackup.backup_engine import run_backup_for_job


class BackupScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

    def load_jobs_from_db(self):
        """Load active BackupJob entries and schedule them."""
        db = SessionLocal()
        try:
            jobs = db.query(BackupJob).filter(BackupJob.active == True).all()

            for job in jobs:
                self._schedule_job(job)
        finally:
            db.close()

    def _schedule_job(self, job: BackupJob):
        """Schedule a single backup job according to its schedule_type."""
        if job.schedule_type == "interval":
            if not job.interval_minutes:
                return

            trigger = IntervalTrigger(minutes=job.interval_minutes)

        elif job.schedule_type == "daily":
            # Example: run every day at 02:00
            trigger = CronTrigger(hour=2, minute=0)

        else:
            # schedule_type = "manual"
            return

        self.scheduler.add_job(
            func=self._execute_job,
            trigger=trigger,
            args=[job.id],
            id=f"job_{job.id}",
            replace_existing=True,
        )

    def _execute_job(self, job_id: int):
        """Execute backup for the given job_id."""
        db = SessionLocal()
        try:
            job = db.query(BackupJob).filter_by(id=job_id).first()
            if not job:
                return
            run_backup_for_job(db, job)
        finally:
            db.close()

    def reload(self):
        """Remove all jobs and reload from DB."""
        self.scheduler.remove_all_jobs()
        self.load_jobs_from_db()

