"""Tests for domain objects."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from jobflow.domain.job import Job, JobStatus, Priority
from jobflow.domain.exceptions import RetryableError, PermanentError


class TestJobCreation:
    """Test Job creation."""
    
    def test_create_job(self):
        """Test creating a new job."""
        payload = {"orders": []}
        job = Job.create(
            job_type="order_reconciliation",
            payload=payload,
            priority=Priority.NORMAL,
        )
        
        assert job.job_type == "order_reconciliation"
        assert job.status == JobStatus.PENDING
        assert job.priority == Priority.NORMAL
        assert job.payload == payload
        assert job.attempt_count == 0
        assert job.max_attempts == 3
        assert job.result is None
        assert job.error is None


class TestJobStateTransitions:
    """Test Job state machine enforcement."""
    
    def test_pending_to_running(self):
        """Test PENDING → RUNNING transition."""
        job = Job.create(
            job_type="order_reconciliation",
            payload={},
        )
        now = datetime.utcnow()
        
        job.transition_to_running("worker-1", now)
        
        assert job.status == JobStatus.RUNNING
        assert job.claimed_by == "worker-1"
        assert job.started_at == now
    
    def test_running_to_completed(self):
        """Test RUNNING → COMPLETED transition."""
        job = Job.create(job_type="order_reconciliation", payload={})
        now = datetime.utcnow()
        job.transition_to_running("worker-1", now)
        
        result = {"valid_count": 1, "invalid_count": 0}
        job.transition_to_completed(result, now)
        
        assert job.status == JobStatus.COMPLETED
        assert job.result == result
        assert job.completed_at == now
    
    def test_running_to_failed(self):
        """Test RUNNING → FAILED transition."""
        job = Job.create(job_type="order_reconciliation", payload={})
        now = datetime.utcnow()
        job.transition_to_running("worker-1", now)
        
        error_msg = "Duplicate order IDs detected"
        job.transition_to_failed(error_msg, now)
        
        assert job.status == JobStatus.FAILED
        assert job.error == error_msg
        assert job.completed_at == now
    
    def test_running_to_retrying(self):
        """Test RUNNING → RETRYING transition."""
        job = Job.create(job_type="order_reconciliation", payload={})
        now = datetime.utcnow()
        job.transition_to_running("worker-1", now)
        
        next_attempt = now + timedelta(seconds=2)
        error_msg = "Transient network error"
        job.transition_to_retrying(error_msg, next_attempt, now)
        
        assert job.status == JobStatus.RETRYING
        assert job.error == error_msg
        assert job.next_attempt_at == next_attempt
    
    def test_retrying_to_pending(self):
        """Test RETRYING → PENDING transition."""
        job = Job.create(job_type="order_reconciliation", payload={})
        now = datetime.utcnow()
        job.transition_to_running("worker-1", now)
        job.attempt_count = 1
        
        next_attempt = now + timedelta(seconds=2)
        job.transition_to_retrying("Error", next_attempt, now)
        
        job.transition_from_retrying_to_pending(now)
        
        assert job.status == JobStatus.PENDING
        assert job.attempt_count == 2
    
    def test_invalid_transition_raises_error(self):
        """Test that invalid transitions raise ValueError."""
        job = Job.create(job_type="order_reconciliation", payload={})
        now = datetime.utcnow()
        
        # Cannot go PENDING → COMPLETED directly
        with pytest.raises(ValueError):
            job.transition_to_completed({"result": "data"}, now)
        
        # Cannot go PENDING → FAILED directly
        with pytest.raises(ValueError):
            job.transition_to_failed("error", now)
    
    def test_cannot_transition_from_completed(self):
        """Test that COMPLETED is terminal."""
        job = Job.create(job_type="order_reconciliation", payload={})
        now = datetime.utcnow()
        job.transition_to_running("worker-1", now)
        job.transition_to_completed({"result": "data"}, now)
        
        # Cannot transition from COMPLETED
        with pytest.raises(ValueError):
            job.transition_to_failed("error", now)
    
    def test_cannot_transition_from_failed(self):
        """Test that FAILED is terminal."""
        job = Job.create(job_type="order_reconciliation", payload={})
        now = datetime.utcnow()
        job.transition_to_running("worker-1", now)
        job.transition_to_failed("error", now)
        
        # Cannot transition from FAILED
        with pytest.raises(ValueError):
            job.transition_to_completed({"result": "data"}, now)