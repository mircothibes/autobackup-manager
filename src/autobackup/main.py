from __future__ import annotations

import logging
import traceback

from autobackup.db import Base, engine
from autobackup.scheduler import BackupScheduler
from autobackup.gui import run_app


def configure_logging() -> None:
    """Configure basic logging for the whole application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


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
    except Exception as exc:
        logging.exception("Error while running GUI: %s", exc)
        print("\nERROR while running GUI:", exc)
        traceback.print_exc()
    finally:
        logging.info("Shutting down scheduler...")
        scheduler.stop()
        logging.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
