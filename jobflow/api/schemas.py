"""API request/response schemas."""
from typing import List
from typing import Any, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

from jobflow.domain.job import JobStatus, Priority


class JobSubmitRequest(BaseModel):
    """Request schema for submitting a new job."""
    
    job_type: str = Field(..., min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: Priority = Field(default=Priority.NORMAL)
    max_attempts: int = Field(default=3, ge=1, le=10)


class JobAttempt(BaseModel):
    """Schema for a single job attempt."""
    
    attempt_number: int
    worker_id: Optional[str]
    status: str
    error: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]


class JobResponse(BaseModel):
    """Response schema for job details."""
    
    id: UUID
    job_type: str
    status: JobStatus
    priority: Priority
    payload: dict[str, Any]
    result: Optional[dict[str, Any]]
    error: Optional[str]
    attempt_count: int
    max_attempts: int
    claimed_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    next_attempt_at: Optional[datetime]


class JobSubmitResponse(BaseModel):
    """Response schema for job submission."""
    
    id: UUID
    status: JobStatus
    message: str = "Job submitted successfully"
    

class JobListResponse(BaseModel):
    """Response schema for paginated job list."""
    
    jobs: list[JobResponse]
    total_count: int
    limit: int
    offset: int