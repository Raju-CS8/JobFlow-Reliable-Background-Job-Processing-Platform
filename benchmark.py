"""Performance benchmark for JobFlow."""

import asyncio
import time
import httpx


async def submit_job(client, order_id, amount):
    """Submit a single job to the API."""
    payload = {
        "job_type": "order_reconciliation",
        "payload": {
            "orders": [
                {
                    "order_id": order_id,
                    "amount": amount,
                    "currency": "INR",
                    "status": "PAID",
                }
            ]
        },
        "priority": "NORMAL",
    }
    
    try:
        response = await client.post(
            "http://localhost:8000/jobs",
            json=payload,
            timeout=30.0,
        )
        if response.status_code == 201:
            data = response.json()
            return data["id"]
        else:
            print(f"Error submitting {order_id}: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"Error submitting {order_id}: {type(e).__name__}: {e}")
        return None


async def submit_jobs_batch(num_jobs, batch_size=10):
    """Submit jobs in batches to avoid overwhelming the API."""
    job_ids = []
    
    for batch_start in range(0, num_jobs, batch_size):
        batch_end = min(batch_start + batch_size, num_jobs)
        batch_size_actual = batch_end - batch_start
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            for i in range(batch_start, batch_end):
                order_id = f"ORD-{i+1}"
                amount = 49.99 + (i * 0.01)
                tasks.append(submit_job(client, order_id, amount))
            
            results = await asyncio.gather(*tasks)
            job_ids.extend([r for r in results if r is not None])
        
        print(f"  Batch {batch_start//batch_size + 1}: submitted {batch_size_actual} jobs")
        await asyncio.sleep(0.5)  # Small delay between batches
    
    return job_ids


def wait_for_completion(job_ids, timeout_seconds=600):
    """Wait for all jobs to complete."""
    start_time = time.time()
    remaining_jobs = set(job_ids)
    
    while remaining_jobs:
        if time.time() - start_time > timeout_seconds:
            print(f"Timeout! Only {len(job_ids) - len(remaining_jobs)}/{len(job_ids)} jobs completed")
            return len(job_ids) - len(remaining_jobs)
        
        try:
            with httpx.Client(timeout=10.0) as client:
                jobs_to_check = list(remaining_jobs)
                for job_id in jobs_to_check:
                    try:
                        response = client.get(f"http://localhost:8000/jobs/{job_id}")
                        if response.status_code == 200:
                            job = response.json()
                            if job["status"] in ["COMPLETED", "FAILED"]:
                                remaining_jobs.discard(job_id)
                    except Exception:
                        pass
        except Exception:
            pass
        
        time.sleep(2.0)
    
    return len(job_ids)


def run_benchmark(num_jobs=200):
    """Run the complete benchmark."""
    print(f"\n{'='*60}")
    print(f"JobFlow Benchmark - {num_jobs} jobs")
    print(f"{'='*60}\n")
    
    # Submit jobs
    print(f"Submitting {num_jobs} jobs (in batches of 10)...")
    start_submit = time.time()
    
    job_ids = asyncio.run(submit_jobs_batch(num_jobs, batch_size=10))
    
    submit_time = time.time() - start_submit
    print(f"\n✓ Successfully submitted {len(job_ids)} jobs in {submit_time:.2f}s\n")
    
    if len(job_ids) == 0:
        print("ERROR: No jobs were submitted!")
        return
    
    # Wait for completion
    print("Waiting for jobs to complete...")
    start_process = time.time()
    
    completed = wait_for_completion(job_ids)
    
    process_time = time.time() - start_process
    
    print(f"\n✓ {completed} jobs completed in {process_time:.2f}s\n")
    
    # Calculate metrics
    jobs_per_second = completed / process_time if process_time > 0 else 0
    
    print(f"{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Total Jobs Submitted: {len(job_ids)}")
    print(f"Total Completed:      {completed}")
    print(f"Total Time:           {process_time:.2f} seconds")
    print(f"Jobs/Second:          {jobs_per_second:.2f}")
    if completed > 0:
        print(f"Avg Time/Job:         {(process_time/completed*1000):.2f}ms")
    print(f"{'='*60}\n")
    
    return {
        "jobs": completed,
        "time_seconds": process_time,
        "jobs_per_second": jobs_per_second,
    }


if __name__ == "__main__":
    run_benchmark(num_jobs=200)