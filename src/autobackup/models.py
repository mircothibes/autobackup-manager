from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from autobackup.db import Base


class BackupJob(Base):
    __tablename__ = "backup_jobs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    source_path = Column(String(500), nullable=False)
    destination_path = Column(String(500), nullable=False)

    schedule_type = Column(String(50), nullable=False, default="manual")
    interval_minutes = Column(Integer, nullable=True)
    active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    runs = relationship(
        "BackupRun",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class BackupRun(Base):
    __tablename__ = "backup_runs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("backup_jobs.id"), nullable=False)

    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)

    status = Column(String(50), nullable=False, default="pending")
    message = Column(String(1000), nullable=True)
    output_file = Column(String(500), nullable=True)

    job = relationship("BackupJob", back_populates="runs")

