"""SQLAlchemy ORM models for JobFlow."""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import uuid

Base = declarative_base()


class Job(Base):
    """ORM model for the jobs table."""
    
    __tablename__ = "jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="PENDING")
    priority = Column(String(10), nullable=False, default="NORMAL")
    payload = Column(JSON, nullable=False, default={})
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    claimed_by = Column(String(255), nullable=True)
    next_attempt_at = Column(DateTime(timezone=False), nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=False), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime(timezone=False), nullable=True)
    completed_at = Column(DateTime(timezone=False), nullable=True)
    
    # Relationships
    attempts = relationship("JobAttempt", back_populates="job", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        Index("ix_jobs_status_priority_created_at", "status", "priority", "created_at"),
        Index("ix_jobs_status_next_attempt_at", "status", "next_attempt_at"),
        CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'RETRYING')",
            name="ck_jobs_status",
        ),
        CheckConstraint(
            "priority IN ('LOW', 'NORMAL', 'HIGH')",
            name="ck_jobs_priority",
        ),
    )
    
    def __repr__(self) -> str:
        return f"<Job(id={self.id}, job_type={self.job_type}, status={self.status})>"


class JobAttempt(Base):
    """ORM model for the job_attempts table."""
    
    __tablename__ = "job_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    worker_id = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=False), nullable=True)
    finished_at = Column(DateTime(timezone=False), nullable=True)
    
    # Relationships
    job = relationship("Job", back_populates="attempts")
    
    # Constraints
    __table_args__ = (
        Index("ix_job_attempts_job_id", "job_id"),
        CheckConstraint(
            "status IN ('RUNNING', 'COMPLETED', 'FAILED', 'RETRYING')",
            name="ck_job_attempts_status",
        ),
    )
    
    def __repr__(self) -> str:
        return f"<JobAttempt(id={self.id}, job_id={self.job_id}, attempt_number={self.attempt_number})>"