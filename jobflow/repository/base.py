"""Abstract repository interface for JobFlow."""

from abc import ABC, abstractmethod
from uuid import UUID
from datetime import datetime
from typing import Optional, List

from jobflow.domain.job import Job, JobStatus, Priority


class JobRepository(ABC):
    """
    Abstract repository for job persistence.
    
    Implementations handle all database operations and transactions.
    """
    
    @abstractmethod
    def save(self, job: Job) -> None:
        """
        Save a new job or update an existing one.
        
        For new jobs, generates ID if not present.
        For updates, ensures state transitions are valid.
        """
        pass
    
    @abstractmethod
    def get_by_id(self, job_id: UUID) -> Optional[Job]:
        """Retrieve a job by ID. Returns None if not found."""
        pass
    
    @abstractmethod
    def claim_next_job(self, worker_id: str, now: datetime) -> Optional[Job]:
        """
        Atomically claim the next eligible PENDING job for a worker.
        
        Uses database locking (FOR UPDATE SKIP LOCKED) to ensure
        safe concurrent claiming: two workers cannot simultaneously claim
        the same job.
        
        Returns the claimed job transitioned to RUNNING, or None if no
        eligible job exists.
        """
        pass
    
    @abstractmethod
    def mark_completed(
        self,
        job_id: UUID,
        result: dict,
        now: datetime,
    ) -> None:
        """Mark a job as COMPLETED with the result."""
        pass
    
    @abstractmethod
    def mark_failed(
        self,
        job_id: UUID,
        error: str,
        now: datetime,
    ) -> None:
        """Mark a job as FAILED with the error message."""
        pass
    
    @abstractmethod
    def mark_retrying(
        self,
        job_id: UUID,
        error: str,
        next_attempt_at: datetime,
        now: datetime,
    ) -> None:
        """Mark a job as RETRYING and schedule next attempt."""
        pass
    
    @abstractmethod
    def promote_retrying_to_pending(self, job_id: UUID, now: datetime) -> None:
        """
        Transition a RETRYING job back to PENDING when retry time arrives.
        
        Increments attempt_count.
        """
        pass
    
    @abstractmethod
    def get_stuck_jobs(
        self,
        stuck_threshold_seconds: int,
        now: datetime,
    ) -> List[Job]:
        """
        Retrieve RUNNING jobs stuck longer than the threshold.
        
        Used for crash recovery: returns jobs that started more than
        stuck_threshold_seconds ago and are still in RUNNING state.
        """
        pass
    
    @abstractmethod
    def record_attempt_start(
        self,
        job_id: UUID,
        attempt_number: int,
        worker_id: str,
        started_at: datetime,
    ) -> None:
        """Record that a worker started processing an attempt."""
        pass
    
    @abstractmethod
    def record_attempt_finish(
        self,
        job_id: UUID,
        attempt_number: int,
        status: str,
        error: Optional[str],
        finished_at: datetime,
    ) -> None:
        """Record that an attempt finished (completed, failed, or retrying)."""
        pass