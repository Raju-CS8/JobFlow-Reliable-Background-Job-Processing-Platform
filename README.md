# JobFlow 🚀

### Reliable Concurrent Background Job Processing Platform

JobFlow is a PostgreSQL-backed background job processing platform built with **Python, FastAPI, PostgreSQL, React, and concurrent workers**.

The system demonstrates production-oriented backend engineering concepts including **priority-based scheduling, transactional job claiming, concurrent processing, automatic retries, failure recovery, persistent execution tracking, input validation, idempotent processing, automated testing, and CI/CD**.

> **Engineering focus:** concurrency, database transactions, reliability, fault handling, background processing, testing, and observability.

---

## ✨ Key Features

- 🔒 **Safe concurrent processing** using PostgreSQL `FOR UPDATE SKIP LOCKED`
- 🚦 **Priority-based scheduling** — `HIGH → NORMAL → LOW`
- 🔁 **Automatic retries** with exponential backoff
- 🧾 **Persistent execution attempts** and error history
- 🛡️ **Input validation** with explicit failure handling
- ♻️ **Stuck-job recovery** for jobs left in `RUNNING`
- 📦 **Batch job submission**
- 📊 **React monitoring dashboard**
- 🧪 **Automated test suite** covering API, domain, processors, workers, and concurrency
- ⚙️ **GitHub Actions CI** with PostgreSQL, database migrations, and automated testing
- 📈 **Performance benchmarking** across multiple concurrent workers

---

# 🏗️ Architecture

```text
                         ┌──────────────────────────┐
                         │      React Dashboard     │
                         │       Vite Frontend      │
                         └────────────┬─────────────┘
                                      │ HTTP
                                      ▼
                         ┌──────────────────────────┐
                         │       FastAPI API        │
                         │  Submit / Query / Stats  │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │           PostgreSQL              │
                    │                                  │
                    │  Jobs / Attempts / Errors /      │
                    │       Persistent State            │
                    └───────────────┬──────────────────┘
                                    │
                         FOR UPDATE SKIP LOCKED
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
       │   Worker 1  │       │   Worker 2  │       │   Worker N  │
       │ Poll / Claim│       │ Poll / Claim│       │ Poll / Claim│
       └──────┬──────┘       └──────┬──────┘       └──────┬──────┘
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    ▼
                         ┌─────────────────────┐
                         │    Job Executor     │
                         │ Validation / Retry  │
                         │ Success / Failure   │
                         └─────────────────────┘
```

---

# 🔄 Job Lifecycle

```text
                    ┌──────────────┐
                    │    PENDING   │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │    RUNNING   │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌───────────┐ ┌──────────┐ ┌───────────┐
        │ COMPLETED │ │  FAILED  │ │ RETRYING  │
        └───────────┘ └──────────┘ └─────┬─────┘
                                         │
                                         ▼
                                    ┌──────────┐
                                    │ PENDING  │
                                    └──────────┘
```

A job can move through the following states:

```text
PENDING
   ↓
RUNNING
   ├──→ COMPLETED
   ├──→ FAILED
   └──→ RETRYING → PENDING
```

---

# 🔒 Concurrency Strategy

JobFlow uses PostgreSQL row-level locking to safely coordinate multiple workers.

The worker claims the next available job using:

```sql
SELECT *
FROM jobs
WHERE status = 'PENDING'
ORDER BY priority DESC, created_at ASC
FOR UPDATE SKIP LOCKED
LIMIT 1;
```

### Why `FOR UPDATE SKIP LOCKED`?

When multiple workers request work simultaneously:

1. A worker locks a pending job.
2. Other workers skip the locked row.
3. Each worker can claim a different job.
4. The database becomes the coordination mechanism.
5. Multiple workers can process jobs concurrently without claiming the same pending row.

This provides a database-backed concurrency model without requiring an external message broker.

---

# 🚦 Priority Scheduling

Jobs are processed according to priority:

```text
HIGH
  ↓
NORMAL
  ↓
LOW
```

Within the same priority level, jobs are ordered by creation time.

This provides:

- Priority-aware scheduling
- FIFO ordering within the same priority
- Deterministic job selection
- Database-backed scheduling

---

# 🔁 Retry & Failure Handling

JobFlow distinguishes between **retryable** and **permanent** failures.

## Retryable Failures

Transient failures can move a job into `RETRYING`.

The system uses exponential backoff:

```text
Attempt 1 → wait 1s
Attempt 2 → wait 2s
Attempt 3 → wait 4s
```

The retry mechanism prevents immediate repeated execution of transiently failing jobs.

## Permanent Failures

Validation errors and unsupported job types are treated as permanent failures and are not repeatedly retried.

```text
Invalid Input
     │
     ▼
  FAILED
```

This prevents invalid jobs from consuming worker capacity through unnecessary retries.

---

# 🧾 Persistent Execution Tracking

JobFlow persists execution attempts in PostgreSQL.

Each execution attempt can track information including:

- Attempt number
- Worker information
- Execution state
- Error information
- Execution timing
- Job association

This allows the system to retain execution history rather than relying only on the current job status.

---

# ♻️ Failure Recovery

JobFlow includes recovery handling for jobs that remain in `RUNNING`.

A simplified recovery flow:

```text
Worker starts job
       │
       ▼
    RUNNING
       │
       │ Worker failure
       ▼
Stuck-job detection
       │
       ▼
   RETRYING
       │
       ▼
    PENDING
       │
       ▼
Another worker
reclaims job
```

The system uses **at-least-once processing semantics**.

A worker can fail after performing work but before successfully recording the final state. Recovery can therefore cause a job to execute again.

For this reason, processors are designed with **idempotent processing** where safe re-execution is required.

---

# 📊 Performance Benchmark

A local benchmark was executed using the same **200-job workload** with different numbers of concurrent workers.

### Observed Results

| Workers | Jobs | Processing Time | Throughput | Relative Throughput |
|---:|---:|---:|---:|---:|
| 1 | 200 | 60.43s | 3.31 jobs/s | 1.00× |
| 2 | 200 | 49.12s | 4.07 jobs/s | 1.23× |
| 3 | 200 | **30.83s** | **6.49 jobs/s** | **1.96×** |
| 4 | 200 | 34.40s | 5.81 jobs/s | 1.76× |

### Key Observation

The strongest observed result in this local benchmark was:

> **6.49 jobs/sec while processing 200 jobs with 3 concurrent workers.**

The benchmark demonstrates that increasing worker concurrency can improve throughput, while also showing that scaling is workload- and environment-dependent rather than automatically linear.

> **Note:** Benchmark results depend on hardware, PostgreSQL configuration, workload characteristics, application overhead, and runtime environment. These measurements are intended as local engineering benchmarks rather than universal performance guarantees.

---

# 🧪 Testing

JobFlow includes an automated test suite covering core application and concurrency behavior.

### Test Coverage

- Domain state transitions
- API endpoints
- Job creation
- Input validation
- Order reconciliation
- Retry behavior
- Permanent failures
- Job claiming
- Priority ordering
- FIFO ordering within the same priority
- Attempt tracking
- Worker execution
- Concurrent workers
- Race-condition prevention
- Failure handling
- Processor validation

### Current Test Result

```text
48 passed
```

The current local test suite contains **48 passing tests**.

---

# ⚙️ GitHub Actions CI

JobFlow includes a GitHub Actions CI workflow.

Every push and pull request targeting `main` or `master` runs the automated pipeline.

### CI Pipeline

```text
GitHub Push / Pull Request
            │
            ▼
      Checkout Repository
            │
            ▼
       Setup Python 3.10
            │
            ▼
      Start PostgreSQL
            │
            ▼
     Install Dependencies
            │
            ▼
      Run Alembic Migrations
            │
            ▼
        Run Pytest
            │
            ▼
       CI Result
```

The CI workflow verifies:

- Python environment setup
- PostgreSQL availability
- Database migrations
- Automated test execution

### CI Status

```text
GitHub Actions CI: ✅ Passing
Test Suite:        ✅ 48 passed
```

---

# 🧰 Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| API | REST APIs |
| Validation | Pydantic |
| ORM / Database Access | SQLAlchemy |
| Database | PostgreSQL |
| Migrations | Alembic |
| Worker System | Python concurrent workers |
| Frontend | React, Vite |
| API Documentation | Swagger / OpenAPI |
| Testing | Pytest, pytest-asyncio |
| CI/CD | GitHub Actions |
| Version Control | Git, GitHub |

---

# 📁 Project Structure

```text
JobFlow/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── alembic/
│   ├── env.py
│   └── versions/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── styles/
│   │   ├── App.jsx
│   │   └── api.js
│   ├── package.json
│   └── vite.config.js
│
├── jobflow/
│   ├── api/
│   ├── db/
│   ├── domain/
│   ├── processors/
│   ├── repository/
│   └── worker/
│
├── tests/
│   ├── test_api.py
│   ├── test_concurrent_workers.py
│   ├── test_domain.py
│   ├── test_processors.py
│   └── test_worker.py
│
├── benchmark.py
├── demo_batch.py
├── alembic.ini
├── pyproject.toml
├── pytest.ini
└── README.md
```

---

# 🚀 Quick Start

## Prerequisites

Install:

- Python 3.10+
- PostgreSQL
- Node.js / npm
- Git

---

## 1. Clone the Repository

```bash
git clone https://github.com/Raju-CS8/JobFlow-Reliable-Background-Job-Processing-Platform.git
cd JobFlow-Reliable-Background-Job-Processing-Platform
```

---

## 2. Create the Python Environment

### Windows

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Backend Dependencies

```bash
pip install fastapi==0.104.1 uvicorn==0.24.0 pydantic==2.5.0
pip install sqlalchemy==2.0.23 alembic==1.13.0
pip install psycopg2-binary==2.9.9 httpx==0.25.2
pip install pytest==7.4.3 pytest-asyncio==0.21.1
```

---

## 4. Configure PostgreSQL

Create the database and application user:

```sql
CREATE DATABASE jobflow;

CREATE USER jobflow WITH PASSWORD 'jobflow';

GRANT ALL PRIVILEGES ON DATABASE jobflow TO jobflow;
```

Default local connection:

```text
postgresql://jobflow:jobflow@127.0.0.1:5432/jobflow
```

> For production environments, credentials should be supplied through environment variables or a secret manager rather than stored directly in source code.

---

## 5. Run Database Migrations

```bash
alembic upgrade head
```

---

## 6. Run Tests

```bash
pytest -v
```

Expected current result:

```text
48 passed
```

---

## 7. Start the FastAPI Backend

```bash
uvicorn jobflow.app:app --reload --host 127.0.0.1 --port 8000
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

---

## 8. Start a Worker

Open another terminal:

```bash
python -m jobflow.worker.worker
```

For concurrent processing, start additional worker processes in separate terminals.

For example:

```text
Terminal 1 → Worker 1
Terminal 2 → Worker 2
Terminal 3 → Worker 3
```

All workers coordinate through PostgreSQL.

---

## 9. Start the React Dashboard

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

# 📡 API

## Submit a Job

```http
POST /jobs
Content-Type: application/json
```

### Example Request

```json
{
  "job_type": "order_reconciliation",
  "priority": "HIGH",
  "payload": {
    "orders": [
      {
        "order_id": "ORD-001",
        "amount": 1500.50,
        "currency": "INR",
        "status": "PAID"
      },
      {
        "order_id": "ORD-002",
        "amount": 750.00,
        "currency": "INR",
        "status": "PENDING"
      }
    ]
  },
  "max_attempts": 3
}
```

---

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/jobs` | Submit a job |
| `GET` | `/jobs` | List jobs |
| `GET` | `/jobs/{job_id}` | Get job details |
| `GET` | `/stats` | Get job statistics |
| `GET` | `/health` | Health check |

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

---

# 📦 Batch Processing

JobFlow supports submitting multiple jobs for background processing.

A batch can contain multiple independent jobs that are persisted in PostgreSQL and subsequently claimed by available workers.

Example workflow:

```text
Batch Submission
       │
       ▼
   PostgreSQL
       │
       ├──────────────┐
       ▼              ▼
   Worker 1       Worker 2
       │              │
       └──────┬───────┘
              ▼
        Job Execution
```

---

# 🧠 Engineering Concepts Demonstrated

## 1. Database-Backed Job Queue

PostgreSQL provides durable job state instead of relying on an in-memory queue.

This allows job information to survive application restarts and provides a persistent source of truth for workers.

---

## 2. Transactional Job Claiming

`FOR UPDATE SKIP LOCKED` provides safe concurrent job claiming.

```sql
FOR UPDATE SKIP LOCKED
```

This allows multiple workers to compete for available jobs while avoiding rows that are already locked by another worker.

---

## 3. Priority Scheduling

Jobs are selected according to:

```text
Priority
   ↓
Creation Time
```

This provides priority-aware scheduling while maintaining FIFO ordering among jobs with the same priority.

---

## 4. Concurrent Processing

Multiple worker processes can consume jobs concurrently:

```text
             PostgreSQL
             /   |   \
            /    |    \
           ▼     ▼     ▼
       Worker  Worker  Worker
          1       2       3
```

The database coordinates access to the pending job queue.

---

## 5. Retry Mechanisms

Transient failures can be retried using exponential backoff:

```text
1s → 2s → 4s
```

This separates temporary execution failures from permanent validation failures.

---

## 6. Persistent Execution History

Execution attempts are stored persistently, allowing the system to retain information about previous attempts and failures.

---

## 7. Failure Recovery

Jobs that remain in `RUNNING` can be detected as stuck and moved through the recovery process.

This supports continued processing when a worker terminates unexpectedly.

---

## 8. Idempotent Processing

Idempotent processing is important because JobFlow uses at-least-once processing semantics.

A job may execute again during retry or recovery, so safe re-execution is an important reliability consideration.

---

## 9. Automated Testing

The project uses Pytest to verify:

- Core domain behavior
- API behavior
- Validation
- Worker execution
- Retry behavior
- Priority scheduling
- Concurrent processing
- Race-condition prevention

---

## 10. Continuous Integration

GitHub Actions automatically runs the test suite against PostgreSQL.

This provides a repeatable validation process for repository changes.

---

# 🔐 Reliability Model

JobFlow intentionally uses **at-least-once processing semantics** rather than claiming exactly-once execution.

A worker can fail after performing work but before recording the final job state.

Therefore, the same job may be executed again during recovery or retry.

The system addresses this using:

- Persistent job state
- Persistent attempt history
- Stuck-job recovery
- Idempotent processing
- Retryable vs permanent failure classification
- Transactional job claiming

```text
                 Job
                  │
                  ▼
              Processing
                  │
          ┌───────┴────────┐
          │                │
       Success           Failure
          │                │
          ▼                ▼
      COMPLETED       Retry / Recovery
                           │
                           ▼
                       Processing
```

---

# ⚙️ Current Configuration

Important worker configuration includes:

```text
Poll interval:          1 second
Stuck-job threshold:    5 minutes
Retry backoff:          1s, 2s, 4s
```

These values are intended for the current application configuration.

For production deployment, credentials and environment-specific configuration should be provided through environment variables or a secret-management system.

---

# 🧪 Benchmarking the System

The repository includes:

```text
benchmark.py
```

Run:

```bash
python benchmark.py
```

The benchmark submits jobs through the API and measures the time required for the workers to process them.

To evaluate concurrent processing, run multiple worker processes simultaneously.

Example:

```text
FastAPI
   │
   ▼
PostgreSQL
   │
   ├── Worker 1
   ├── Worker 2
   └── Worker 3
```

The current observed local benchmark reached:

```text
200 jobs
3 workers
6.49 jobs/sec
30.83 seconds processing time
```

Benchmark results will vary depending on the execution environment.

---

# 📈 Engineering Takeaways

JobFlow demonstrates several backend and distributed-systems concepts without relying on an external message broker:

### Concurrency

Multiple workers safely consume a shared PostgreSQL-backed queue.

### Transactions

Database transactions coordinate job ownership and state changes.

### Locking

`FOR UPDATE SKIP LOCKED` prevents workers from unnecessarily waiting on already-claimed jobs.

### Reliability

Retries, persistent state, recovery, and attempt tracking provide resilience against transient failures and worker interruptions.

### Scheduling

Priority and FIFO ordering determine which pending job is selected next.

### Observability

Persistent job status, attempt history, errors, and dashboard statistics make job execution inspectable.

### Quality Engineering

Automated tests and GitHub Actions CI provide repeatable verification of the system.

---

# 👨‍💻 Author

**Raju CS**

Software Engineering / Full-Stack Developer

---

# 🔗 Repository

**GitHub:**

https://github.com/Raju-CS8/JobFlow-Reliable-Background-Job-Processing-Platform

**API Documentation:**

http://127.0.0.1:8000/docs

**Frontend:**

http://localhost:5173

---

# 📄 License

No open-source license is currently declared for this repository.

---

### Built to demonstrate reliable background processing, concurrent worker execution, PostgreSQL transactions, failure recovery, automated testing, and production-oriented backend engineering.
