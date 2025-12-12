# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
import os
import zipfile
import pytz
import logging
from typing import Tuple
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from autobackup.models import BackupJob, BackupRun
from autobackup.config import settings

logger = logging.getLogger(__name__)


def build_backup_filename(job_id: int, destination_path: str) -> Path:
    """
    Build a unique backup filename based on job id and current UTC time.
    """
    dest_dir = Path(destination_path)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"job_{job_id}_{timestamp}.zip"
    return dest_dir / filename


def create_zip_backup(
    source_path: str,
    destination_path: str,
    output_file: Path,
) -> Tuple[bool, str]:
    """
    Create a zip backup of source_path into output_file.

    Returns:
        (success, message)
    """
    src = Path(source_path)
    dest = output_file

    if not src.exists():
        return False, f"Source path does not exist: {src}"

    if not src.is_dir():
        return False, f"Source path is not a directory: {src}"

    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(dest, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(src):
                root_path = Path(root)
                for name in files:
                    file_path = root_path / name
                    # relative path inside zip
                    arcname = file_path.relative_to(src)
                    zf.write(file_path, arcname=arcname)

        return True, f"Backup created: {dest}"

    except Exception as exc:  # noqa: BLE001
        if dest.exists():
            dest.unlink(missing_ok=True)
        return False, f"Error while creating backup: {exc}"


def _enforce_retention_for_job(db: Session, job_id: int) -> None:
    """
    Enforce retention policy for a given job:
    keep only the N most recent successful backups and delete older ones.
    """
    max_runs = settings.max_backups_per_job
    if max_runs <= 0:
        return

    runs = (
        db.query(BackupRun)
        .filter(BackupRun.job_id == job_id, BackupRun.status == "success")
        .order_by(BackupRun.start_time.desc())
        .all()
    )

    if len(runs) <= max_runs:
        return

    to_delete = runs[max_runs:]

    for run in to_delete:
        try:
            if run.output_file:
                path = Path(run.output_file)
                if path.exists():
                    path.unlink()
                    logger.info(
                        "Retention: deleted old backup file %s for job %s",
                        path,
                        job_id,
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Retention: could not delete file %s for job %s: %s",
                run.output_file,
                job_id,
                exc,
            )

        db.delete(run)

    db.commit()
    logger.info(
        "Retention: kept last %s backups for job %s (deleted %s old runs)",
        max_runs,
        job_id,
        len(to_delete),
    )


def run_backup_for_job(db: Session, job: BackupJob) -> BackupRun:
    """
    Run a backup for the given job and persist a BackupRun record.
    """
    run = BackupRun(
        job_id=job.id,
        status="running",
        start_time=datetime.now(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    output_file_path = build_backup_filename(job.id, job.destination_path)

    success, message = create_zip_backup(
        source_path=job.source_path,
        destination_path=job.destination_path,
        output_file=output_file_path,
    )

    LOCAL_TZ = pytz.timezone("Europe/Luxembourg")
    run.end_time = datetime.now(LOCAL_TZ)
    run.message = message

    if success:
        run.status = "success"
        run.output_file = str(output_file_path)
    else:
        run.status = "error"
        run.output_file = None

    db.add(run)
    db.commit()
    db.refresh(run)

    # Só aplica retenção se o backup deu certo
    if success:
        _enforce_retention_for_job(db, job.id)

    return run

