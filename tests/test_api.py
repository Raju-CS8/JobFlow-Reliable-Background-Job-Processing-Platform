"""Tests for FastAPI API endpoints."""

import pytest
from pytest_asyncio import fixture
from httpx import AsyncClient
from uuid import UUID

from jobflow.app import create_app
from jobflow.domain.job import JobStatus, Priority


@fixture
async def client():
    """Create a test client for async tests."""
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestJobSubmission:
    """Test job submission endpoint."""
    
    @pytest.mark.asyncio
    async def test_submit_job_minimal(self, client):
        """Test submitting a job with minimal payload."""
        response = await client.post(
            "/jobs",
            json={
                "job_type": "order_reconciliation",
                "payload": {},
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == JobStatus.PENDING
        assert data["message"] == "Job submitted successfully"
        
        # Verify we can parse the ID as UUID
        job_id = UUID(data["id"])
        assert job_id is not None
    
    @pytest.mark.asyncio
    async def test_submit_job_with_priority(self, client):
        """Test submitting a job with explicit priority."""
        response = await client.post(
            "/jobs",
            json={
                "job_type": "order_reconciliation",
                "payload": {"orders": []},
                "priority": "HIGH",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == JobStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_submit_job_with_max_attempts(self, client):
        """Test submitting a job with custom max_attempts."""
        response = await client.post(
            "/jobs",
            json={
                "job_type": "order_reconciliation",
                "payload": {},
                "max_attempts": 5,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == JobStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_submit_job_invalid_job_type(self, client):
        """Test that submitting with empty job_type fails."""
        response = await client.post(
            "/jobs",
            json={
                "job_type": "",
                "payload": {},
            },
        )
        
        assert response.status_code == 422  # Validation error


class TestJobRetrieval:
    """Test job retrieval endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_job(self, client):
        """Test retrieving a job after submission."""
        # Submit a job
        submit_response = await client.post(
            "/jobs",
            json={
                "job_type": "order_reconciliation",
                "payload": {"orders": [{"order_id": "ORD-1", "amount": 49.99}]},
                "priority": "NORMAL",
            },
        )
        
        assert submit_response.status_code == 201
        job_id = submit_response.json()["id"]
        
        # Retrieve it
        get_response = await client.get(f"/jobs/{job_id}")
        
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == job_id
        assert data["job_type"] == "order_reconciliation"
        assert data["status"] == JobStatus.PENDING
        assert data["priority"] == Priority.NORMAL
        assert data["attempt_count"] == 0
        assert data["max_attempts"] == 3
        assert data["result"] is None
        assert data["error"] is None
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self, client):
        """Test retrieving a job that doesn't exist."""
        from uuid import uuid4
        
        job_id = uuid4()
        response = await client.get(f"/jobs/{job_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


class TestHealthCheck:
    """Test health check endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"