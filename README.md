# JobFlow 🚀

### Reliable Concurrent Background Job Processing Platform

JobFlow is a PostgreSQL-backed background job processing platform built with FastAPI, Python, React, and concurrent workers.

It demonstrates reliable job processing with priority scheduling, safe concurrent job claiming, retries with exponential backoff, persistent execution history, validation, stuck-job recovery, and automated CI testing.

> **Engineering focus:** concurrency, database transactions, reliability, fault handling, idempotent processing, and observability.

---

## ✨ Core Features

- 🔒 **Safe concurrent processing** using PostgreSQL `FOR UPDATE SKIP LOCKED`
- 🚦 **Priority-based execution** — `HIGH → NORMAL → LOW`
- 🔁 **Automatic retries** with exponential backoff
- 🧾 **Persistent execution attempts** and error history
- 🛡️ **Input validation** with clear failure handling
- ♻️ **Stuck-job recovery** for jobs left in `RUNNING`
- 📦 **Batch job submission**
- 📊 **React monitoring dashboard** for job status and statistics
- 🧪 **Automated tests** covering API, domain, processors, workers, and concurrency
- ⚙️ **GitHub Actions CI** with PostgreSQL, migrations, and automated tests

---

## 🏗️ Architecture

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
                    │  Jobs / Attempts / Errors /      │
                    │       Persistent State           │
                    └───────────────┬──────────────────┘
                                    │
                         FOR UPDATE SKIP LOCKED
                                    │
             ┌──────────────────────┼──────────────────────┐
             ▼                      ▼                      ▼
      ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
      │   Worker 1  │       │   Worker 2  │       │   Worker N  │
      │ Poll / Claim│       │ Poll / Claim│       │ Poll / Claim│
      └──────┬──────┘       └──────┬──────┘       └──────┬──────┘
             │                     │                     │
             └─────────────────────┼─────────────────────┘
                                   ▼
                        ┌─────────────────────┐
                        │    Job Executor      │
                        │ Validation / Retry  │
                        │ Success / Failure    │
                        └─────────────────────┘
```

### Job lifecycle

```text
PENDING
   │
   ▼
RUNNING
   │
   ├──────────────► COMPLETED
   │
   ├──────────────► FAILED
   │
   └──────────────► RETRYING
                         │
                         ▼
                      PENDING
```

### Concurrency strategy

Workers safely claim jobs using PostgreSQL row-level locking:

```sql
SELECT *
FROM jobs
WHERE status = 'PENDING'
ORDER BY priority DESC, created_at ASC
FOR UPDATE SKIP LOCKED
LIMIT 1;
```

This allows multiple workers to compete for work while skipping rows already claimed by another worker.

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| Validation | Pydantic |
| ORM / Database Access | SQLAlchemy |
| Database | PostgreSQL |
| Migrations | Alembic |
| Worker System | Python concurrent workers |
| Frontend | React + Vite |
| API Documentation | Swagger / OpenAPI |
| Testing | Pytest + pytest-asyncio |
| CI | GitHub Actions |

---

## 📊 Performance Benchmark

A benchmark using **200 jobs** demonstrated concurrent throughput scaling:

| Workers | Jobs | Duration | Throughput | Speedup |
|---:|---:|---:|---:|---:|
| 1 | 200 | 103.69s | 1.93 jobs/s | 1.00× |
| 3 | 200 | 23.93s | **8.36 jobs/s** | **4.33×** |

> Results depend on hardware, database configuration, workload, and environment.

---

## 🧪 Testing & CI

The test suite covers:

- Domain state transitions
- API endpoints
- Job validation
- Order reconciliation
- Retry behavior
- Job claiming
- Priority ordering
- FIFO ordering within the same priority
- Attempt tracking
- Concurrent workers
- Race-condition prevention

Run locally:

```bash
pytest -v
```

### Current local result

```text
48 passed
```

### GitHub Actions

Every push and pull request to `main`/`master` triggers CI.

The workflow:

1. Starts PostgreSQL
2. Sets up Python 3.10
3. Installs dependencies
4. Runs Alembic migrations
5. Executes the full Pytest suite

**CI status: ✅ Passing**

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL
- Node.js / npm
- Git

### 1. Clone

```bash
git clone https://github.com/Raju-CS8/JobFlow-Reliable-Background-Job-Processing-Platform.git
cd JobFlow-Reliable-Background-Job-Processing-Platform
```

### 2. Create the Python environment

#### Windows

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

#### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install backend dependencies

```bash
pip install fastapi==0.104.1 uvicorn==0.24.0 pydantic==2.5.0
pip install sqlalchemy==2.0.23 alembic==1.13.0
pip install psycopg2-binary==2.9.9 httpx==0.25.2
pip install pytest==7.4.3 pytest-asyncio==0.21.1
```

### 4. Configure PostgreSQL

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

> For production, use environment variables or a secret manager instead of committing credentials.

### 5. Run migrations

```bash
alembic upgrade head
```

### 6. Run tests

```bash
pytest -v
```

### 7. Start the FastAPI backend

```bash
uvicorn jobflow.app:app --reload --host 127.0.0.1 --port 8000
```

Backend: `http://127.0.0.1:8000`

Swagger UI: `http://127.0.0.1:8000/docs`

### 8. Start a worker

In another terminal:

```bash
python -m jobflow.worker.worker
```

For concurrent processing, run additional workers in separate terminals.

### 9. Start the React dashboard

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

---

## 📡 API

### Submit a job

```http
POST /jobs
Content-Type: application/json
```

Example:

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

### Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/jobs` | Submit a job |
| `GET` | `/jobs` | List jobs |
| `GET` | `/jobs/{job_id}` | Get job details |
| `GET` | `/stats` | Get job statistics |
| `GET` | `/health` | Health check |

Interactive documentation:

```text
http://127.0.0.1:8000/docs
```

---

## 🔁 Retry & Failure Handling

JobFlow distinguishes between transient and permanent failures.

### Retryable failures

Transient failures can move a job into `RETRYING` and use exponential backoff:

```text
Attempt 1 → wait 1s
Attempt 2 → wait 2s
Attempt 3 → wait 4s
```

### Permanent failures

Validation and unsupported job errors can be marked as `FAILED` without repeatedly retrying an invalid job.

### Persistent attempt history

Each execution attempt records information such as:

- Attempt number
- Worker information
- Execution state
- Errors
- Timing information

---

## ♻️ Stuck Job Recovery

If a worker fails after a job enters `RUNNING`, recovery logic can detect jobs that remain running beyond the configured threshold.

```text
Worker starts job
      │
      ▼
   RUNNING
      │
 Worker crashes
      │
      ▼
Stuck-job detection
      │
      ▼
   RETRYING
      │
      ▼
Another worker
reclaims the job
```

JobFlow uses **at-least-once processing semantics**. Idempotent processing helps make safe re-execution possible during retries and recovery.

---

## 📁 Project Structure

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

## 🧠 Engineering Concepts Demonstrated

### Database-backed queue

PostgreSQL provides durable job state instead of relying on an in-memory queue.

### Transactional job claiming

`FOR UPDATE SKIP LOCKED` prevents multiple workers from claiming the same pending job.

### Priority scheduling

Jobs are selected by priority first, then creation time.

### State machine

```text
PENDING
   ↓
RUNNING
   ├──→ COMPLETED
   ├──→ FAILED
   └──→ RETRYING → PENDING
```

### Idempotent processing

Job processors are designed so safe re-execution is possible when retries or recovery occur.

---

## 🔐 Reliability Model

JobFlow intentionally uses **at-least-once processing semantics** rather than claiming exactly-once execution.

A worker can fail after performing work but before recording the final state. Recovery can therefore execute a job again.

The system addresses this with:

- Persistent job state
- Persistent attempt history
- Stuck-job recovery
- Idempotent processing
- Separation of retryable and permanent failures

---

## ⚙️ Configuration

Important worker settings include:

```text
Poll interval:          1 second
Stuck-job threshold:    5 minutes
Retry backoff:          1s, 2s, 4s
```

For production deployments, credentials should be supplied through environment variables or a secret manager.

---

## 🗺️ Roadmap

Potential future improvements:

- [ ] WebSocket-based live job updates
- [ ] Scheduled / cron-style jobs
- [ ] Dead-letter queue
- [ ] Prometheus metrics
- [ ] Advanced retry policies with jitter
- [ ] Distributed deployment
- [ ] Kubernetes deployment configuration
- [ ] Additional job processor types

---

## 👨‍💻 Author

**Raju CS**  
MCA Student — CHRIST (Deemed to be University), Bengaluru

---

## 🔗 Links

**Repository:**  
https://github.com/Raju-CS8/JobFlow-Reliable-Background-Job-Processing-Platform

**Swagger API:**  
http://127.0.0.1:8000/docs

**Frontend:**  
http://localhost:5173

---

## 📄 License

Add a license file before claiming a specific open-source license for the repository.

---

### Built to demonstrate reliable background processing, concurrency, database transactions, fault handling, and production-oriented engineering.
