"""Job execution logic for workers."""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from jobflow.domain.job import Job, JobStatus
from jobflow.domain.exceptions import RetryableError, PermanentError
from jobflow.processors.order_reconciliation import ValidationError
from jobflow.repository.postgres_repo import PostgresJobRepository
from jobflow.processors.order_reconciliation import OrderReconciliationProcessor

logger = logging.getLogger(__name__)


class JobExecutor:
    """
    Executes a claimed job and handles outcomes.
    
    - Success → COMPLETED
    - Permanent error → FAILED
    - Retryable error → RETRYING (with exponential backoff)
    """
    
    # Base backoff in seconds for exponential retry
    BACKOFF_BASE_SECONDS = 1
    
    def __init__(self, repo: PostgresJobRepository):
        """
        Initialize executor.
        
        Args:
            repo: Job repository for persistence.
        """
        self.repo = repo
    
    def execute(self, job: Job, worker_id: str) -> None:
        """
        Execute a claimed job.
        
        Handles success, permanent errors, and retryable errors.
        Updates job state and attempt history.
        
        Args:
            job: The claimed job (should be in RUNNING state).
            worker_id: The worker process ID.
        """
        if job.status != JobStatus.RUNNING:
            raise ValueError(f"Job must be RUNNING, got {job.status}")
        
        now = datetime.utcnow()
        attempt_number = job.attempt_count + 1
        
        # Record attempt start
        try:
            self.repo.record_attempt_start(
                job_id=job.id,
                attempt_number=attempt_number,
                worker_id=worker_id,
                started_at=now,
            )
        except Exception as e:
            logger.error(f"Failed to record attempt start for job {job.id}: {e}")
            return
        
        # Execute the job
        try:
            result = self._execute_job(job)
            
            # Success
            self.repo.mark_completed(
                job_id=job.id,
                result=result,
                now=datetime.utcnow(),
            )
            
            self.repo.record_attempt_finish(
                job_id=job.id,
                attempt_number=attempt_number,
                status=JobStatus.COMPLETED.value,
                error=None,
                finished_at=datetime.utcnow(),
            )
            
            logger.info(
                f"Job {job.id} completed successfully. "
                f"Attempt {attempt_number}/{job.max_attempts}"
            )
        
        except ValidationError as e:
            # Validation errors are PERMANENT - don't retry
            # MUST BE FIRST in the exception chain
            error_msg = str(e)
            
            self.repo.mark_failed(
                job_id=job.id,
                error=error_msg,
                now=datetime.utcnow(),
            )
            
            self.repo.record_attempt_finish(
                job_id=job.id,
                attempt_number=attempt_number,
                status=JobStatus.FAILED.value,
                error=error_msg,
                finished_at=datetime.utcnow(),
            )
            
            logger.warning(
                f"Job {job.id} validation failed: {error_msg}. "
                f"Not retrying."
            )
        
        except PermanentError as e:
            # Permanent error: mark FAILED, no retry
            error_msg = str(e)
            
            self.repo.mark_failed(
                job_id=job.id,
                error=error_msg,
                now=datetime.utcnow(),
            )
            
            self.repo.record_attempt_finish(
                job_id=job.id,
                attempt_number=attempt_number,
                status=JobStatus.FAILED.value,
                error=error_msg,
                finished_at=datetime.utcnow(),
            )
            
            logger.warning(
                f"Job {job.id} failed permanently: {error_msg}. "
                f"Not retrying."
            )
        
        except RetryableError as e:
            # Retryable error: check if we can retry
            error_msg = str(e)
            
            if attempt_number >= job.max_attempts:
                # Exhausted retries: mark FAILED
                self.repo.mark_failed(
                    job_id=job.id,
                    error=f"Retryable error after {attempt_number} attempts: {error_msg}",
                    now=datetime.utcnow(),
                )
                
                self.repo.record_attempt_finish(
                    job_id=job.id,
                    attempt_number=attempt_number,
                    status=JobStatus.FAILED.value,
                    error=error_msg,
                    finished_at=datetime.utcnow(),
                )
                
                logger.error(
                    f"Job {job.id} exhausted retries ({attempt_number}/{job.max_attempts}). "
                    f"Marking FAILED."
                )
            else:
                # Retry eligible: schedule next attempt with exponential backoff
                next_attempt_at = self._calculate_next_attempt(attempt_number)
                
                self.repo.mark_retrying(
                    job_id=job.id,
                    error=error_msg,
                    next_attempt_at=next_attempt_at,
                    now=datetime.utcnow(),
                )
                
                self.repo.record_attempt_finish(
                    job_id=job.id,
                    attempt_number=attempt_number,
                    status=JobStatus.RETRYING.value,
                    error=error_msg,
                    finished_at=datetime.utcnow(),
                )
                
                delay_seconds = (next_attempt_at - datetime.utcnow()).total_seconds()
                logger.info(
                    f"Job {job.id} retryable error: {error_msg}. "
                    f"Scheduled for retry at {next_attempt_at.isoformat()} "
                    f"({delay_seconds:.1f}s from now). "
                    f"Attempt {attempt_number}/{job.max_attempts}"
                )
        
        except Exception as e:
            # Unexpected error: treat as retryable
            # THIS MUST BE LAST - catches everything else
            error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
            
            if attempt_number >= job.max_attempts:
                self.repo.mark_failed(
                    job_id=job.id,
                    error=error_msg,
                    now=datetime.utcnow(),
                )
                
                self.repo.record_attempt_finish(
                    job_id=job.id,
                    attempt_number=attempt_number,
                    status=JobStatus.FAILED.value,
                    error=error_msg,
                    finished_at=datetime.utcnow(),
                )
                
                logger.error(
                    f"Job {job.id} failed with unexpected error after {attempt_number} attempts: {error_msg}"
                )
            else:
                next_attempt_at = self._calculate_next_attempt(attempt_number)
                
                self.repo.mark_retrying(
                    job_id=job.id,
                    error=error_msg,
                    next_attempt_at=next_attempt_at,
                    now=datetime.utcnow(),
                )
                
                self.repo.record_attempt_finish(
                    job_id=job.id,
                    attempt_number=attempt_number,
                    status=JobStatus.RETRYING.value,
                    error=error_msg,
                    finished_at=datetime.utcnow(),
                )
                
                logger.warning(
                    f"Job {job.id} unexpected error, retrying: {error_msg}. "
                    f"Attempt {attempt_number}/{job.max_attempts}"
                )
    
    def _execute_job(self, job: Job) -> dict:
        """
        Execute the actual job logic based on job_type.
        
        Currently supports: order_reconciliation
        
        Args:
            job: The job to execute.
        
        Returns:
            Result dictionary.
        
        Raises:
            PermanentError: For invalid input.
            RetryableError: For transient failures.
        """
        if job.job_type == "order_reconciliation":
            return OrderReconciliationProcessor.process(job.payload)
        else:
            raise PermanentError(f"Unknown job type: {job.job_type}")
    
    @staticmethod
    def _calculate_next_attempt(attempt_number: int) -> datetime:
        """
        Calculate next attempt time using exponential backoff.
        
        Base: 1 second
        Sequence: 1s, 2s, 4s, 8s, ...
        
        Args:
            attempt_number: The current attempt number (1-indexed).
        
        Returns:
            Datetime of next eligible attempt.
        """
        backoff_seconds = JobExecutor.BACKOFF_BASE_SECONDS * (2 ** (attempt_number - 1))
        return datetime.utcnow() + timedelta(seconds=backoff_seconds)