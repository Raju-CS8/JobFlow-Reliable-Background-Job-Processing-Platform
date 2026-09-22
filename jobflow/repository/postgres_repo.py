"""PostgreSQL repository implementation for JobFlow."""

from uuid import UUID
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text

from jobflow.domain.job import Job, JobStatus, Priority
from jobflow.repository.base import JobRepository
from jobflow.db.models import Job as JobModel, JobAttempt as JobAttemptModel


class PostgresJobRepository(JobRepository):
    """
    PostgreSQL implementation of the job repository.
    
    Handles all database operations and transactions, including safe
    concurrent job claiming using FOR UPDATE SKIP LOCKED.
    """
    
    def __init__(self, session: Session):
        """
        Initialize repository with a database session.
        
        Args:
            session: SQLAlchemy session for database operations.
        """
        self.session = session
    
    def save(self, job: Job) -> None:
        """
        Save a new job or update an existing one.
        
        For new jobs, persists to database with PENDING status.
        For updates, reflects domain state changes.
        """
        # Check if job exists
        db_job = self.session.query(JobModel).filter(JobModel.id == job.id).first()
        
        if db_job is None:
            # New job: insert
            db_job = JobModel(
                id=job.id,
                job_type=job.job_type,
                status=job.status.value,
                priority=job.priority.value,
                payload=job.payload,
                attempt_count=job.attempt_count,
                max_attempts=job.max_attempts,
                result=job.result,
                error=job.error,
                claimed_by=job.claimed_by,
                next_attempt_at=job.next_attempt_at,
                created_at=job.created_at,
                updated_at=job.updated_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
            )
            self.session.add(db_job)
        else:
            # Existing job: update fields from domain object
            db_job.status = job.status.value
            db_job.priority = job.priority.value
            db_job.payload = job.payload
            db_job.result = job.result
            db_job.error = job.error
            db_job.attempt_count = job.attempt_count
            db_job.max_attempts = job.max_attempts
            db_job.claimed_by = job.claimed_by
            db_job.next_attempt_at = job.next_attempt_at
            db_job.updated_at = job.updated_at
            db_job.started_at = job.started_at
            db_job.completed_at = job.completed_at
        
        self.session.commit()
    
    def get_by_id(self, job_id: UUID) -> Optional[Job]:
        """Retrieve a job by ID. Returns None if not found."""
        db_job = self.session.query(JobModel).filter(JobModel.id == job_id).first()
        
        if db_job is None:
            return None
        
        return self._model_to_domain(db_job)
    
    def claim_next_job(self, worker_id: str, now: datetime) -> Optional[Job]:
        """
        Atomically claim the next eligible PENDING job for a worker.
        
        Uses PostgreSQL FOR UPDATE SKIP LOCKED to ensure safe concurrent claiming:
        - FOR UPDATE locks the selected row so no other transaction can modify it
        - SKIP LOCKED lets other workers skip locked rows instead of blocking
        - Only one worker can transition a given job through the claim operation
        
        This guarantees safe concurrent claiming without exactly-once execution
        (worker crashes can cause re-execution).
        
        Returns the claimed job in RUNNING state, or None if no eligible job.
        """
        try:
            # Query for the next eligible PENDING job, ordered by priority and creation time
            db_job = self.session.query(JobModel).filter(
                JobModel.status == JobStatus.PENDING.value
            ).order_by(
                # Priority ordering: HIGH > NORMAL > LOW
                case_priority := text("CASE WHEN priority='HIGH' THEN 0 WHEN priority='NORMAL' THEN 1 ELSE 2 END"),
                JobModel.created_at,  # FIFO within priority tier
            ).with_for_update(skip_locked=True).limit(1).first()
            
            if db_job is None:
                self.session.commit()
                return None
            
            # Transition the job to RUNNING
            db_job.status = JobStatus.RUNNING.value
            db_job.claimed_by = worker_id
            db_job.started_at = now
            db_job.updated_at = now
            
            self.session.commit()
            
            return self._model_to_domain(db_job)
        
        except Exception:
            self.session.rollback()
            raise
    
    def mark_completed(
        self,
        job_id: UUID,
        result: dict,
        now: datetime,
    ) -> None:
        """Mark a job as COMPLETED with the result."""
        try:
            db_job = self.session.query(JobModel).filter(JobModel.id == job_id).first()
            
            if db_job is None:
                raise ValueError(f"Job {job_id} not found")
            
            # Verify state transition is valid
            if db_job.status != JobStatus.RUNNING.value:
                raise ValueError(
                    f"Cannot mark job as COMPLETED: current status is {db_job.status}"
                )
            
            db_job.status = JobStatus.COMPLETED.value
            db_job.result = result
            db_job.completed_at = now
            db_job.updated_at = now
            
            self.session.commit()
        
        except Exception:
            self.session.rollback()
            raise
    
    def mark_failed(
        self,
        job_id: UUID,
        error: str,
        now: datetime,
    ) -> None:
        """Mark a job as FAILED with the error message."""
        try:
            db_job = self.session.query(JobModel).filter(JobModel.id == job_id).first()
            
            if db_job is None:
                raise ValueError(f"Job {job_id} not found")
            
            # Verify state transition is valid
            if db_job.status != JobStatus.RUNNING.value:
                raise ValueError(
                    f"Cannot mark job as FAILED: current status is {db_job.status}"
                )
            
            db_job.status = JobStatus.FAILED.value
            db_job.error = error
            db_job.completed_at = now
            db_job.updated_at = now
            
            self.session.commit()
        
        except Exception:
            self.session.rollback()
            raise
    
    def mark_retrying(
        self,
        job_id: UUID,
        error: str,
        next_attempt_at: datetime,
        now: datetime,
    ) -> None:
        """Mark a job as RETRYING and schedule next attempt."""
        try:
            db_job = self.session.query(JobModel).filter(JobModel.id == job_id).first()
            
            if db_job is None:
                raise ValueError(f"Job {job_id} not found")
            
            # Verify state transition is valid
            if db_job.status != JobStatus.RUNNING.value:
                raise ValueError(
                    f"Cannot mark job as RETRYING: current status is {db_job.status}"
                )
            
            db_job.status = JobStatus.RETRYING.value
            db_job.error = error
            db_job.next_attempt_at = next_attempt_at
            db_job.updated_at = now
            
            self.session.commit()
        
        except Exception:
            self.session.rollback()
            raise
    
    def promote_retrying_to_pending(self, job_id: UUID, now: datetime) -> None:
        """
        Transition a RETRYING job back to PENDING when retry time arrives.
        
        Increments attempt_count.
        """
        try:
            db_job = self.session.query(JobModel).filter(JobModel.id == job_id).first()
            
            if db_job is None:
                raise ValueError(f"Job {job_id} not found")
            
            # Verify state transition is valid
            if db_job.status != JobStatus.RETRYING.value:
                raise ValueError(
                    f"Cannot promote job to PENDING: current status is {db_job.status}"
                )
            
            db_job.status = JobStatus.PENDING.value
            db_job.attempt_count += 1
            db_job.updated_at = now
            
            self.session.commit()
        
        except Exception:
            self.session.rollback()
            raise
    
    def get_stuck_jobs(
        self,
        stuck_threshold_seconds: int,
        now: datetime,
    ) -> List[Job]:
        """
        Retrieve RUNNING jobs stuck longer than the threshold.
        
        A job is considered stuck if it has been in RUNNING state for longer
        than stuck_threshold_seconds. This is a heuristic for crash recovery.
        
        Note: A legitimately slow job can be returned here. The deterministic,
        idempotent workload makes re-execution safe from a correctness
        perspective, though potentially wasteful.
        """
        threshold = now - __import__('datetime').timedelta(
            seconds=stuck_threshold_seconds
        )
        
        db_jobs = self.session.query(JobModel).filter(
            and_(
                JobModel.status == JobStatus.RUNNING.value,
                JobModel.started_at < threshold,
            )
        ).all()
        
        return [self._model_to_domain(db_job) for db_job in db_jobs]
    
    def record_attempt_start(
        self,
        job_id: UUID,
        attempt_number: int,
        worker_id: str,
        started_at: datetime,
    ) -> None:
        """Record that a worker started processing an attempt."""
        try:
            attempt = JobAttemptModel(
                job_id=job_id,
                attempt_number=attempt_number,
                worker_id=worker_id,
                status="RUNNING",
                started_at=started_at,
            )
            self.session.add(attempt)
            self.session.commit()
        
        except Exception:
            self.session.rollback()
            raise
    
    def record_attempt_finish(
        self,
        job_id: UUID,
        attempt_number: int,
        status: str,
        error: Optional[str],
        finished_at: datetime,
    ) -> None:
        """Record that an attempt finished (completed, failed, or retrying)."""
        try:
            attempt = self.session.query(JobAttemptModel).filter(
                and_(
                    JobAttemptModel.job_id == job_id,
                    JobAttemptModel.attempt_number == attempt_number,
                )
            ).first()
            
            if attempt is None:
                raise ValueError(
                    f"Attempt {attempt_number} for job {job_id} not found"
                )
            
            attempt.status = status
            attempt.error = error
            attempt.finished_at = finished_at
            
            self.session.commit()
        
        except Exception:
            self.session.rollback()
            raise
    
    def _model_to_domain(self, db_job: JobModel) -> Job:
        """Convert a SQLAlchemy model to a domain Job object."""
        return Job(
            id=db_job.id,
            job_type=db_job.job_type,
            status=JobStatus(db_job.status),
            priority=Priority(db_job.priority),
            payload=db_job.payload,
            attempt_count=db_job.attempt_count,
            max_attempts=db_job.max_attempts,
            result=db_job.result,
            error=db_job.error,
            claimed_by=db_job.claimed_by,
            next_attempt_at=db_job.next_attempt_at,
            created_at=db_job.created_at,
            updated_at=db_job.updated_at,
            started_at=db_job.started_at,
            completed_at=db_job.completed_at,
        )