"""Integration test: multiple workers competing for jobs concurrently."""

import pytest
import multiprocessing
import time
from datetime import datetime
from sqlalchemy.orm import Session

from jobflow.domain.job import Job, JobStatus, Priority
from jobflow.repository.postgres_repo import PostgresJobRepository
from jobflow.worker.job_executor import JobExecutor
from jobflow.db.database import SessionLocal
from sqlalchemy import delete, func
from jobflow.db.models import JobAttempt, Job as JobModel


@pytest.fixture(scope="session")
def setup_db():
    """Initialize database for concurrent tests."""
    from jobflow.db.database import init_db
    init_db()
    yield


@pytest.fixture
def clean_db():
    """Clean database before and after test."""
    session = SessionLocal()
    session.execute(delete(JobAttempt))
    session.execute(delete(JobModel))
    session.commit()
    session.close()
    
    yield
    
    session = SessionLocal()
    session.execute(delete(JobAttempt))
    session.execute(delete(JobModel))
    session.commit()
    session.close()


def worker_process(worker_id: str, num_jobs_to_process: int) -> dict:
    """
    Worker subprocess that claims and processes jobs.
    
    Returns a dict with statistics.
    """
    processed_count = 0
    
    for _ in range(num_jobs_to_process * 2):  # Try multiple times to claim
        session = SessionLocal()
        try:
            repo = PostgresJobRepository(session)
            job = repo.claim_next_job(worker_id, datetime.utcnow())
            
            if job is None:
                # No work, sleep briefly
                time.sleep(0.1)
                continue
            
            # Execute the job
            executor = JobExecutor(repo)
            executor.execute(job, worker_id)
            
            processed_count += 1
            
            if processed_count >= num_jobs_to_process:
                break
        
        finally:
            session.close()
    
    return {
        "worker_id": worker_id,
        "processed": processed_count,
    }


class TestConcurrentWorkers:
    """Test multiple workers claiming and executing jobs concurrently."""
    
    def test_multiple_workers_no_race_condition(self, setup_db, clean_db):
        """
        Critical concurrency test:
        - Create 20 jobs
        - Run 4 workers concurrently
        - Verify each job is processed exactly once (no simultaneous claims)
        """
        num_jobs = 20
        num_workers = 4
        
        # Create jobs
        session = SessionLocal()
        try:
            repo = PostgresJobRepository(session)
            
            for i in range(num_jobs):
                job = Job.create(
                    job_type="order_reconciliation",
                    payload={
                        "orders": [
                            {
                                "order_id": f"ORD-{i}",
                                "amount": 49.99 + i,
                                "currency": "INR",
                                "status": "PAID",
                            }
                        ]
                    },
                    priority=Priority.NORMAL,
                )
                repo.save(job)
        
        finally:
            session.close()
        
        # Run workers concurrently
        with multiprocessing.Pool(num_workers) as pool:
            results = []
            for w in range(num_workers):
                result = pool.apply_async(
                    worker_process,
                    args=(f"worker-{w}", num_jobs // num_workers),
                )
                results.append(result)
            
            # Wait for all workers to complete
            worker_stats = [r.get(timeout=30) for r in results]
        
        # Verify results
        session = SessionLocal()
        try:
            # Count completed jobs
            completed_count = session.query(func.count(JobModel.id)).filter(
                JobModel.status == JobStatus.COMPLETED.value
            ).scalar()
            
            # Each job should be processed exactly once
            # (may not all be completed in this short test, but none should be double-claimed)
            assert completed_count > 0, "At least some jobs should be completed"
            
            # Verify no job is RUNNING (all should be in terminal state or PENDING)
            running_count = session.query(func.count(JobModel.id)).filter(
                JobModel.status == JobStatus.RUNNING.value
            ).scalar()
            assert running_count == 0, "No jobs should still be RUNNING"
            
            # Verify no job was double-claimed by checking attempt count
            # (Each completed job should have exactly 1 attempt)
            session.close()
            
            session = SessionLocal()
            for job in session.query(JobModel).filter(
                JobModel.status == JobStatus.COMPLETED.value
            ).all():
                attempt_count = session.query(func.count(JobAttempt.id)).filter(
                    JobAttempt.job_id == job.id
                ).scalar()
                # Should have exactly 1 attempt if claimed once
                assert attempt_count == 1, f"Job {job.id} has {attempt_count} attempts (should be 1)"
        
        finally:
            session.close()
        
        print(f"\nConcurrency test results:")
        print(f"  Jobs created: {num_jobs}")
        print(f"  Workers: {num_workers}")
        print(f"  Worker stats: {worker_stats}")
        print(f"  Completed: {completed_count}")
    
    def test_high_concurrency_stress(self, setup_db, clean_db):
        """
        Stress test with higher concurrency and job count.
        """
        num_jobs = 50
        num_workers = 8
        
        # Create jobs
        session = SessionLocal()
        try:
            repo = PostgresJobRepository(session)
            
            for i in range(num_jobs):
                job = Job.create(
                    job_type="order_reconciliation",
                    payload={
                        "orders": [
                            {
                                "order_id": f"STRESS-{i}",
                                "amount": 10.00 + i * 0.5,
                                "currency": "USD",
                                "status": "PAID",
                            }
                        ]
                    },
                    priority=Priority.NORMAL,
                )
                repo.save(job)
        
        finally:
            session.close()
        
        # Run workers concurrently
        with multiprocessing.Pool(num_workers) as pool:
            results = []
            for w in range(num_workers):
                result = pool.apply_async(
                    worker_process,
                    args=(f"stress-worker-{w}", num_jobs // num_workers),
                )
                results.append(result)
            
            # Wait for all workers to complete
            worker_stats = [r.get(timeout=60) for r in results]
        
        # Verify results
        session = SessionLocal()
        try:
            # Count completed jobs
            completed_count = session.query(func.count(JobModel.id)).filter(
                JobModel.status == JobStatus.COMPLETED.value
            ).scalar()
            
            # Should have completed most/all jobs
            assert completed_count >= num_jobs * 0.8, \
                f"Should complete at least 80% of jobs, got {completed_count}/{num_jobs}"
            
            # No jobs should be in RUNNING state (workers finished)
            running_count = session.query(func.count(JobModel.id)).filter(
                JobModel.status == JobStatus.RUNNING.value
            ).scalar()
            assert running_count == 0, "No jobs should still be RUNNING"
        
        finally:
            session.close()
        
        print(f"\nStress test results:")
        print(f"  Jobs created: {num_jobs}")
        print(f"  Workers: {num_workers}")
        print(f"  Completed: {completed_count}/{num_jobs}")
        print(f"  Worker stats: {worker_stats}")