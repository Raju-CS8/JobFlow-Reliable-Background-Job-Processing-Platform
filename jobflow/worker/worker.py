"""Worker process for JobFlow."""

import logging
import signal
import time
from datetime import datetime, timedelta
import os

from jobflow.db.database import get_session, get_engine
from jobflow.repository.postgres_repo import PostgresJobRepository
from jobflow.worker.job_executor import JobExecutor
from jobflow.config import get_config

logger = logging.getLogger(__name__)


class Worker:
    """
    Independent worker process that claims and executes jobs.
    
    Loop:
    1. Recover any stuck jobs (heuristic)
    2. Claim next eligible job from PostgreSQL
    3. Execute the job
    4. Persist result/error/retry
    5. Sleep if no work available
    """
    
    def __init__(self, worker_id: str = None):
        """
        Initialize worker.
        
        Args:
            worker_id: Unique worker identifier. If None, generates from hostname + PID.
        """
        if worker_id is None:
            hostname = os.uname().nodename if hasattr(os, 'uname') else os.environ.get('COMPUTERNAME', 'unknown')
            pid = os.getpid()
            worker_id = f"{hostname}-{pid}"
        
        self.worker_id = worker_id
        self.running = True
        self.config = get_config()
        
        logger.info(f"Worker initialized: {self.worker_id}")
    
    def run(self, poll_interval: float = 1.0) -> None:
        """
        Run the worker loop continuously.
        
        Args:
            poll_interval: Seconds to sleep when no work is available.
        """
        logger.info(f"Worker {self.worker_id} starting main loop (poll_interval={poll_interval}s)")
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        try:
            while self.running:
                try:
                    self._iteration(poll_interval)
                except Exception as e:
                    logger.error(f"Worker {self.worker_id} iteration failed: {e}", exc_info=True)
                    # Sleep briefly before retry to avoid tight loop on persistent errors
                    time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info(f"Worker {self.worker_id} interrupted")
        finally:
            logger.info(f"Worker {self.worker_id} stopped")
    
    def _iteration(self, poll_interval: float) -> None:
        """
        One iteration of the worker loop.
        
        Args:
            poll_interval: Seconds to sleep if no work found.
        """
        session = get_session()
        
        try:
            repo = PostgresJobRepository(session)
            now = datetime.utcnow()
            
            # Step 1: Recover stuck jobs (heuristic)
            self._recover_stuck_jobs(repo, now)
            
            # Step 2: Promote RETRYING jobs to PENDING if retry time has arrived
            self._promote_eligible_retries(repo, now)
            
            # Step 3: Claim next eligible job
            job = repo.claim_next_job(self.worker_id, now)
            
            if job is None:
                # No work available: sleep and continue
                logger.debug(f"Worker {self.worker_id}: no jobs available, sleeping {poll_interval}s")
                time.sleep(poll_interval)
                return
            
            logger.info(f"Worker {self.worker_id} claimed job {job.id} (type={job.job_type}, attempt {job.attempt_count + 1}/{job.max_attempts})")
            
            # Step 4: Execute the job
            executor = JobExecutor(repo)
            executor.execute(job, self.worker_id)
        
        finally:
            session.close()
    
    def _recover_stuck_jobs(self, repo: PostgresJobRepository, now: datetime) -> None:
        """
        Recover RUNNING jobs that have been stuck longer than the threshold.
        
        This is a heuristic: a genuinely slow job can be mistaken for stuck.
        The deterministic/idempotent workload makes re-execution safe from
        correctness perspective, though potentially wasteful.
        
        Args:
            repo: Job repository.
            now: Current datetime.
        """
        stuck_jobs = repo.get_stuck_jobs(
            stuck_threshold_seconds=self.config.stuck_job_threshold_seconds,
            now=now,
        )
        
        if not stuck_jobs:
            return
        
        logger.warning(
            f"Worker {self.worker_id} found {len(stuck_jobs)} stuck jobs "
            f"(threshold={self.config.stuck_job_threshold_seconds}s)"
        )
        
        for stuck_job in stuck_jobs:
            logger.warning(
                f"Recovering stuck job {stuck_job.id} "
                f"(started {(now - stuck_job.started_at).total_seconds():.0f}s ago)"
            )
            # Transition back to PENDING for retry
            repo.promote_retrying_to_pending(stuck_job.id, now)
    
    def _promote_eligible_retries(self, repo: PostgresJobRepository, now: datetime) -> None:
        """
        Check for RETRYING jobs whose next_attempt_at has arrived.
        Promote them back to PENDING so they can be claimed.
        
        Note: This is a simplified version. In production, this would be
        done via a background task or query for efficiency.
        
        Args:
            repo: Job repository.
            now: Current datetime.
        """
        # For now, this is a no-op at the worker level.
        # A separate background process or scheduled task should handle this.
        # Alternatively, we could query for eligible retries here.
        pass
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Worker {self.worker_id} received shutdown signal")
        self.running = False


def main():
    """Entry point for running a worker process."""
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Get worker ID from command line or generate default
    worker_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Create and run worker
    worker = Worker(worker_id=worker_id)
    worker.run()


if __name__ == "__main__":
    main()