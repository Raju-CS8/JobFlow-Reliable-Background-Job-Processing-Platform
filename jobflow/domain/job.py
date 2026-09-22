"""Job domain entity and enums."""

from enum import Enum
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4


class JobStatus(str, Enum):
    """Job lifecycle states."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class Priority(str, Enum):
    """Job priority levels."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


class Job:
    """
    Domain entity representing a background job.
    
    Enforces valid state transitions and business rules.
    """
    
    def __init__(
        self,
        id: UUID,
        job_type: str,
        status: JobStatus,
        priority: Priority,
        payload: dict[str, Any],
        attempt_count: int = 0,
        max_attempts: int = 3,
        result: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
        claimed_by: Optional[str] = None,
        next_attempt_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ):
        self.id = id
        self.job_type = job_type
        self.status = status
        self.priority = priority
        self.payload = payload
        self.attempt_count = attempt_count
        self.max_attempts = max_attempts
        self.result = result
        self.error = error
        self.claimed_by = claimed_by
        self.next_attempt_at = next_attempt_at
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.started_at = started_at
        self.completed_at = completed_at
    
    @staticmethod
    def create(
        job_type: str,
        payload: dict[str, Any],
        priority: Priority = Priority.NORMAL,
        max_attempts: int = 3,
    ) -> "Job":
        """Create a new job in PENDING status."""
        return Job(
            id=uuid4(),
            job_type=job_type,
            status=JobStatus.PENDING,
            priority=priority,
            payload=payload,
            max_attempts=max_attempts,
        )
    
    def transition_to_running(self, worker_id: str, now: datetime) -> None:
        """
        Transition PENDING job to RUNNING.
        Enforced: only PENDING → RUNNING is allowed.
        """
        if self.status != JobStatus.PENDING:
            raise ValueError(
                f"Cannot transition {self.status} to RUNNING; "
                f"only PENDING can become RUNNING."
            )
        self.status = JobStatus.RUNNING
        self.claimed_by = worker_id
        self.started_at = now
        self.updated_at = now
    
    def transition_to_completed(
        self,
        result: dict[str, Any],
        now: datetime,
    ) -> None:
        """
        Transition RUNNING job to COMPLETED.
        Enforced: only RUNNING → COMPLETED.
        """
        if self.status != JobStatus.RUNNING:
            raise ValueError(
                f"Cannot transition {self.status} to COMPLETED; "
                f"only RUNNING can become COMPLETED."
            )
        self.status = JobStatus.COMPLETED
        self.result = result
        self.completed_at = now
        self.updated_at = now
    
    def transition_to_failed(
        self,
        error: str,
        now: datetime,
    ) -> None:
        """
        Transition RUNNING job to FAILED (terminal).
        Enforced: only RUNNING → FAILED.
        """
        if self.status != JobStatus.RUNNING:
            raise ValueError(
                f"Cannot transition {self.status} to FAILED; "
                f"only RUNNING can become FAILED."
            )
        self.status = JobStatus.FAILED
        self.error = error
        self.completed_at = now
        self.updated_at = now
    
    def transition_to_retrying(
        self,
        error: str,
        next_attempt_at: datetime,
        now: datetime,
    ) -> None:
        """
        Transition RUNNING job to RETRYING.
        Enforced: only RUNNING → RETRYING.
        """
        if self.status != JobStatus.RUNNING:
            raise ValueError(
                f"Cannot transition {self.status} to RETRYING; "
                f"only RUNNING can become RETRYING."
            )
        self.status = JobStatus.RETRYING
        self.error = error
        self.next_attempt_at = next_attempt_at
        self.updated_at = now
    
    def transition_from_retrying_to_pending(self, now: datetime) -> None:
        """
        Transition RETRYING job back to PENDING when retry time is reached.
        Enforced: only RETRYING → PENDING.
        """
        if self.status != JobStatus.RETRYING:
            raise ValueError(
                f"Cannot transition {self.status} to PENDING; "
                f"only RETRYING can become PENDING."
            )
        self.status = JobStatus.PENDING
        self.attempt_count += 1
        self.updated_at = now