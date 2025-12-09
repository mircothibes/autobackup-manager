from __future__ import annotations

import logging
import traceback
from pathlib import Path

from autobackup.db import Base, engine
from autobackup.scheduler import BackupScheduler
from autobackup.gui import run_app


def configure_logging() -> None:
    """Configure logging for the whole application (console + file)."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Avoid adding handlers twice if configure_logging() is called again
    if root_logger.handlers:
        return

    # main.py -> src/autobackup/main.py  -> go up 3 levels to project root
    project_root = Path(__file__).resolve().parents[2]
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "autobackup.log"

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def main() -> None:
    """Application entry point: init DB, start scheduler, launch GUI."""
    configure_logging()

    logging.info("Creating database tables if not exist...")
    Base.metadata.create_all(bind=engine)

    scheduler = BackupScheduler()

    logging.info("Starting BackupScheduler...")
    scheduler.start()
    logging.info("BackupScheduler started (non-blocking).")

    try:
        logging.info("Starting AutoBackup GUI...")
        run_app(scheduler)
        logging.info("GUI closed.")
    except Exception as exc:  # noqa: BLE001
        logging.exception("Error while running GUI: %s", exc)
        print("\nERROR while running GUI:", exc)
        traceback.print_exc()
    finally:
        logging.info("Shutting down scheduler...")
        try:
            scheduler.stop()
        except Exception as exc:  # noqa: BLE001
            logging.warning("Error while stopping scheduler: %s", exc)
        logging.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
