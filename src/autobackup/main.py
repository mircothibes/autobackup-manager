from autobackup.db import Base, engine
from autobackup import models  # noqa: F401  # ensure models are imported


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def main() -> None:
    init_db()
    print("Database initialized successfully.")


if __name__ == "__main__":
    main()

