# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
import logging
import os
import zipfile
import pytz
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


def cleanup_old_backups(job: BackupJob, max_backups: int) -> None:
    """
    Keep only the newest `max_backups` backup files for this job
    and delete older ones from the destination folder.
    """
    dest_dir = Path(job.destination_path)

    if not dest_dir.exists() or not dest_dir.is_dir():
        logger.info(
            "Destination directory does not exist or is not a directory for job %s: %s",
            job.id,
            dest_dir,
        )
        return

    pattern = f"job_{job.id}_*.zip"
    files = list(dest_dir.glob(pattern))

    if len(files) <= max_backups:
        return

    # Newest first
    files_sorted = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)

    # Delete everything after the N newest
    for old_file in files_sorted[max_backups:]:
        try:
            old_file.unlink()
            logger.info(
                "Deleted old backup file for job %s: %s",
                job.id,
                old_file,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Could not delete old backup file %s: %s",
                old_file,
                exc,
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

        # Apply retention policy for this job
        cleanup_old_backups(job, settings.max_backups_per_job)
    else:
        run.status = "error"
        run.output_file = None

    db.add(run)
    db.commit()
    db.refresh(run)

    return run
