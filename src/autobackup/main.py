from sqlalchemy.orm import Session

from autobackup.db import Base, engine, SessionLocal
from autobackup.models import BackupJob
from autobackup.backup_engine import run_backup_for_job


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def create_sample_job(db: Session) -> BackupJob:
    job = BackupJob(
        name="Test job",
        source_path="/tmp/source_test",
        destination_path="/tmp/backups_test",
        schedule_type="manual",
        active=True,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def main() -> None:
    init_db()

    db = SessionLocal()
    try:
        job = create_sample_job(db)
        run = run_backup_for_job(db, job)
        print("Backup run status:", run.status)
        print("Message:", run.message)
        print("Output file:", run.output_file)
    finally:
        db.close()


if __name__ == "__main__":
    main()

