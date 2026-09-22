"""Submit a batch of 10 jobs with different priorities and validation scenarios."""

import requests
import json

API_BASE = "http://localhost:8000"

JOBS = [
    # HIGH Priority - Mix valid/invalid
    {
        "order_id": "HIGH-VALID-1",
        "amount": 100,
        "currency": "INR",
        "status": "Paid",
        "priority": "HIGH",
        "expected": "COMPLETED",
    },
    {
        "order_id": "HIGH-INVALID",
        "amount": -50,
        "currency": "INR",
        "status": "Paid",
        "priority": "HIGH",
        "expected": "FAILED (negative amount)",
    },
    {
        "order_id": "HIGH-VALID-2",
        "amount": 200,
        "currency": "USD",
        "status": "Paid",
        "priority": "HIGH",
        "expected": "COMPLETED",
    },
    # NORMAL Priority - Mix valid/invalid
    {
        "order_id": "NORMAL-1",
        "amount": 75,
        "currency": "EUR",
        "status": "Paid",
        "priority": "NORMAL",
        "expected": "COMPLETED",
    },
    {
        "order_id": "NORMAL-BAD",
        "amount": -10,
        "currency": "GBP",
        "status": "Paid",
        "priority": "NORMAL",
        "expected": "FAILED (negative amount)",
    },
    {
        "order_id": "NORMAL-2",
        "amount": 150,
        "currency": "INR",
        "status": "Paid",
        "priority": "NORMAL",
        "expected": "COMPLETED",
    },
    {
        "order_id": "NORMAL-3",
        "amount": 300,
        "currency": "USD",
        "status": "Paid",
        "priority": "NORMAL",
        "expected": "COMPLETED",
    },
    # LOW Priority - All valid
    {
        "order_id": "LOW-1",
        "amount": 25,
        "currency": "EUR",
        "status": "Paid",
        "priority": "LOW",
        "expected": "COMPLETED",
    },
    {
        "order_id": "LOW-2",
        "amount": 50,
        "currency": "INR",
        "status": "Paid",
        "priority": "LOW",
        "expected": "COMPLETED",
    },
    {
        "order_id": "LOW-3",
        "amount": 80,
        "currency": "GBP",
        "status": "Paid",
        "priority": "LOW",
        "expected": "COMPLETED",
    },
]


def submit_batch():
    """Submit all jobs at once."""
    print("\n" + "="*70)
    print("SUBMITTING BATCH OF 10 JOBS")
    print("="*70 + "\n")
    
    submitted_ids = []
    
    for i, job_spec in enumerate(JOBS, 1):
        payload = {
            "job_type": "order_reconciliation",
            "payload": {
                "orders": [
                    {
                        "order_id": job_spec["order_id"],
                        "amount": job_spec["amount"],
                        "currency": job_spec["currency"],
                        "status": job_spec["status"],
                    }
                ]
            },
            "priority": job_spec["priority"],
            "max_attempts": 3,
        }
        
        try:
            response = requests.post(f"{API_BASE}/jobs", json=payload)
            if response.status_code == 201:
                job_id = response.json()["id"]
                submitted_ids.append(job_id)
                print(
                    f"Job {i:2d}: ✓ {job_spec['priority']:6s} | "
                    f"{job_spec['order_id']:15s} | "
                    f"${job_spec['amount']:7.2f} | "
                    f"Expected: {job_spec['expected']}"
                )
            else:
                print(f"Job {i:2d}: ✗ Failed to submit: {response.status_code}")
        except Exception as e:
            print(f"Job {i:2d}: ✗ Error: {e}")
    
    print("\n" + "="*70)
    print(f"SUBMITTED: {len(submitted_ids)}/10 jobs")
    print("="*70)
    print("\nNow watch the sidebar update in real-time:")
    print("  - HIGH priority jobs process FIRST")
    print("  - NORMAL priority jobs process NEXT")
    print("  - LOW priority jobs process LAST")
    print("  - 2 jobs should FAIL (negative amounts)")
    print("  - 8 jobs should COMPLETE (valid)")
    print("\n")


if __name__ == "__main__":
    submit_batch()