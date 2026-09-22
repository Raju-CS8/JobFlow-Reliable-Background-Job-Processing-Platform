# JobFlow 🚀

**Reliable Concurrent Background Job Processing Platform**

A production-ready, scalable background job processor built with FastAPI, PostgreSQL, and React. JobFlow provides safe concurrent job execution with priority ordering, automatic retries, real-time monitoring, and comprehensive error handling.

[![GitHub](https://img.shields.io/badge/GitHub-JobFlow-blue?logo=github)](https://github.com/Raju-CS8/JobFlow)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13%2B-blue)](https://www.postgresql.org/)

---

## ✨ Features

### Core Capabilities
- **Safe Concurrent Processing** — `FOR UPDATE SKIP LOCKED` prevents race conditions across multiple workers
- **Priority-Based Execution** — HIGH → NORMAL → LOW job ordering
- **Automatic Retries** — Exponential backoff (1s, 2s, 4s) for transient failures
- **Batch Processing** — Submit 10+ jobs simultaneously via REST API
- **Real-Time Monitoring** — Live dashboard with job status, statistics, and progress
- **Production-Grade Validation** — Comprehensive input validation with detailed error messages
- **Persistent Logging** — All job execution attempts stored for audit trails

### Performance
- **4.33x Throughput Scaling** — 3 workers process 200 jobs in 23.93s (vs 103.69s with 1 worker)
- **Stuck Job Recovery** — Automatic detection and reprocessing after 5-minute threshold
- **Efficient Polling** — 1-second worker poll interval with zero busy-waiting

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     React Frontend                       │
│              (Real-time Job Monitoring)                  │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP/WebSocket
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI REST API                       │
│    (Job Submission, Status Queries, Statistics)          │
└────────────────────────┬────────────────────────────────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
       ┌────────────────────────────────────┐
       │      PostgreSQL Job Queue           │
       │  (Persistent State Machine)         │
       │  - Job metadata                     │
       │  - Execution attempts               │
       │  - Error logs                       │
       └────────────────────────────────────┘
            ▲            ▲            ▲
            │            │            │
       ┌────────────┬────────────┬────────────┐
       │  Worker 1  │  Worker 2  │  Worker N  │
       │ (Poller)   │ (Poller)   │ (Poller)   │
       └────────────┴────────────┴────────────┘
```

**Key Design Pattern:**
- **Safe Claiming:** Workers use `FOR UPDATE SKIP LOCKED` to atomically claim next job
- **State Machine:** Enforced job lifecycle (PENDING → RUNNING → COMPLETED/FAILED/RETRYING)
- **Idempotent Processing:** Jobs can be safely re-executed if a worker crashes

---

## 📋 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Vite, Tailwind CSS |
| **Backend** | FastAPI, Pydantic, SQLAlchemy |
| **Database** | PostgreSQL 13+ |
| **Migrations** | Alembic |
| **Testing** | Pytest, concurrent testing |
| **Deployment** | Python 3.9+, uvicorn |

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.9+**
- **PostgreSQL 13+** (running locally)
- **Node.js 16+** (for frontend)
- **Git**

### 1️⃣ Clone Repository
```bash
git clone https://github.com/Raju-CS8/JobFlow.git
cd JobFlow
```

### 2️⃣ Setup Backend

**Create Python Virtual Environment:**
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
```

**Install Dependencies:**
```bash
pip install fastapi uvicorn pydantic sqlalchemy alembic psycopg2-binary pytest pytest-asyncio requests
```

**Setup PostgreSQL Database:**
```bash
psql -U postgres
CREATE DATABASE jobflow;
CREATE USER jobflow WITH PASSWORD 'jobflow';
ALTER ROLE jobflow SET client_encoding TO 'utf8';
ALTER ROLE jobflow SET default_transaction_isolation TO 'read committed';
ALTER ROLE jobflow SET default_transaction_deferrable TO on;
GRANT ALL PRIVILEGES ON DATABASE jobflow TO jobflow;
\q
```

**Run Database Migrations:**
```bash
alembic upgrade head
```

**Verify Setup:**
```bash
pytest  # Run all tests
```

### 3️⃣ Setup Frontend
```bash
cd frontend
npm install
```

### 4️⃣ Run the Application

**Terminal 1 — Start React Frontend:**
```bash
cd frontend
npm run dev
```
Access: **http://localhost:5173**

**Terminal 2 — Start FastAPI Server:**
```bash
uvicorn jobflow.app:app --reload --host 127.0.0.1 --port 8000
```
API: **http://localhost:8000**
Docs: **http://localhost:8000/docs** (Swagger UI)

**Terminal 3+ — Start Worker(s):**
```bash
python -m jobflow.worker.worker
```
Start multiple workers for higher throughput:
```bash
# Terminal 3
python -m jobflow.worker.worker

# Terminal 4
python -m jobflow.worker.worker

# Terminal 5
python -m jobflow.worker.worker
```

### 5️⃣ Submit Demo Batch
```bash
python demo_batch.py
```
Submits 10 jobs (mix of HIGH/NORMAL/LOW priority, valid + invalid payloads) for concurrent processing.

---

## 📚 API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints

#### **Submit Job**
```http
POST /jobs
Content-Type: application/json

{
  "job_type": "order_reconciliation",
  "priority": "HIGH",
  "payload": {
    "orders": [
      {
        "order_id": "ORD001",
        "amount": 150.50,
        "currency": "USD",
        "status": "PENDING"
      }
    ]
  }
}
```

**Response (201 Created):**
```json
{
  "job_id": "uuid-here",
  "job_type": "order_reconciliation",
  "status": "PENDING",
  "priority": "HIGH",
  "created_at": "2026-09-06T10:30:00Z"
}
```

#### **List Jobs (Paginated)**
```http
GET /jobs?limit=50&offset=0
```

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "uuid",
      "job_type": "order_reconciliation",
      "status": "COMPLETED",
      "priority": "HIGH",
      "result": {
        "reconciled_orders": 1,
        "total_amount": 150.50
      },
      "created_at": "2026-09-06T10:30:00Z"
    }
  ],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

#### **Get Job Details**
```http
GET /jobs/{job_id}
```

**Response:**
```json
{
  "job_id": "uuid",
  "job_type": "order_reconciliation",
  "status": "COMPLETED",
  "priority": "HIGH",
  "payload": {...},
  "result": {...},
  "error": null,
  "attempts": 1,
  "created_at": "2026-09-06T10:30:00Z",
  "completed_at": "2026-09-06T10:30:15Z"
}
```

#### **Get System Statistics**
```http
GET /stats
```

**Response:**
```json
{
  "total_jobs": 1000,
  "pending": 50,
  "running": 10,
  "completed": 850,
  "failed": 90,
  "avg_execution_time": 15.3,
  "success_rate": 0.90
}
```

#### **Health Check**
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy"
}
```

---

## 🏃 Running Scenarios

### Scenario 1: Single Worker
```bash
# Terminal 2
uvicorn jobflow.app:app --reload

# Terminal 3
python -m jobflow.worker.worker

# Then submit batch
python demo_batch.py
# Result: ~1.9 jobs/sec throughput
```

### Scenario 2: Three Concurrent Workers (Recommended)
```bash
# Terminal 2
uvicorn jobflow.app:app --reload

# Terminal 3
python -m jobflow.worker.worker

# Terminal 4
python -m jobflow.worker.worker

# Terminal 5
python -m jobflow.worker.worker

# Then submit batch
python demo_batch.py
# Result: ~8.3 jobs/sec throughput (4.33x improvement!)
```

### Scenario 3: Clean Slate Before Demo
```bash
# Reset database
psql -U postgres -d jobflow -c "DELETE FROM jobs; DELETE FROM job_attempts;"

# Then run the application normally
```

---

## 📊 Performance Benchmarks

### Throughput Scaling

| Workers | Jobs | Duration | Throughput | Speedup |
|---------|------|----------|-----------|---------|
| 1       | 200  | 103.69s  | 1.93 j/s  | 1.0x    |
| 3       | 200  | 23.93s   | 8.36 j/s  | **4.33x** |

**Test Methodology:**
- Consistent job payload across runs
- Fresh database before each test
- 1-second worker poll interval
- Network latency included

### Scaling Insights
- **Linear scaling** up to 4 workers (PostgreSQL connection-bound)
- **Diminishing returns** beyond 4 workers
- **Network latency** becomes bottleneck at high worker counts

---

## 🏗️ Project Structure

```
JobFlow/
├── jobflow/
│   ├── __init__.py
│   ├── app.py                 # FastAPI application
│   ├── config.py              # Configuration
│   ├── cli.py                 # CLI commands
│   ├── domain/
│   │   ├── job.py             # Job domain model & state machine
│   │   └── exceptions.py       # Custom exceptions
│   ├── api/
│   │   ├── schemas.py         # Pydantic request/response schemas
│   │   └── routes.py          # FastAPI route handlers
│   ├── db/
│   │   ├── database.py        # PostgreSQL connection
│   │   └── models.py          # SQLAlchemy ORM models
│   ├── repository/
│   │   ├── base.py            # Base repository interface
│   │   └── postgres_repo.py   # PostgreSQL implementation
│   ├── processors/
│   │   └── order_reconciliation.py  # Job processing logic
│   └── worker/
│       ├── worker.py          # Worker main loop
│       └── job_executor.py    # Job execution engine
├── tests/
│   ├── test_domain.py         # Domain logic tests
│   ├── test_api.py            # API endpoint tests
│   ├── test_processors.py     # Processor tests
│   ├── test_worker.py         # Worker tests
│   └── test_concurrent_workers.py  # Concurrency tests
├── frontend/                  # React Vite application
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   ├── pages/
│   │   └── api.js
│   ├── index.html
│   └── package.json
├── alembic/                   # Database migrations
│   ├── env.py
│   ├── versions/
│   └── alembic.ini
├── demo_batch.py              # Batch submission demo script
├── benchmark.py               # Performance benchmarking
├── pytest.ini
├── pyproject.toml
└── README.md
```

---

## 🧪 Testing

### Run All Tests
```bash
pytest
```

### Run Specific Test Suite
```bash
pytest tests/test_domain.py -v              # Domain logic
pytest tests/test_api.py -v                 # API endpoints
pytest tests/test_concurrent_workers.py -v  # Concurrency (slow)
```

### Test Coverage
```bash
pytest --cov=jobflow tests/
```

**Current Coverage:**
- ✅ Domain state machine
- ✅ API endpoints
- ✅ Concurrent job claiming
- ✅ Retry mechanism
- ✅ Validation logic

---

## ⚙️ Configuration

### Worker Configuration
**File:** `jobflow/worker/worker.py`

```python
POLL_INTERVAL = 1  # seconds between job claims
STUCK_JOB_THRESHOLD = 300  # 5 minutes
RETRY_BACKOFF = [1, 2, 4]  # exponential backoff in seconds
```

### Database Configuration
**File:** `jobflow/config.py`

```python
DATABASE_URL = "postgresql://jobflow:jobflow@localhost:5432/jobflow"
```

### API Configuration
**File:** `jobflow/app.py`

```python
API_TITLE = "JobFlow API"
API_VERSION = "1.0.0"
PAGINATION_LIMIT = 50
```

---

## 📖 Key Concepts

### Safe Concurrent Claiming
JobFlow uses **`FOR UPDATE SKIP LOCKED`** to safely claim jobs:
```sql
SELECT * FROM jobs 
WHERE status = 'PENDING' 
ORDER BY priority DESC, created_at ASC
FOR UPDATE SKIP LOCKED
LIMIT 1;
```

This ensures:
- ✅ No race conditions
- ✅ No duplicate processing
- ✅ Workers automatically skip locked rows
- ✅ Higher-priority jobs are processed first

### State Machine
```
PENDING → RUNNING → COMPLETED
                 ↓
             FAILED (permanent)
                 ↓
           RETRYING → RUNNING (same flow)
```

### Idempotent Processing
If a worker crashes during execution:
1. Job remains in `RUNNING` state
2. Stuck job recovery detects it after 5 minutes
3. Job moves to `RETRYING` state
4. Another worker picks it up and re-executes
5. Safe because job processor is idempotent (no duplicate side effects)

---

## 🐛 Known Limitations

| Issue | Status | Impact |
|-------|--------|--------|
| Exactly-once semantics | ❌ Not guaranteed | At-least-once (OK for idempotent ops) |
| Stuck job recovery | Heuristic-based (5min) | Potential short delay in recovery |
| Single PostgreSQL | ✅ Sufficient | Multi-DB not required for this scale |
| No Redis/Kafka | ✅ By design | PostgreSQL sufficient; avoids complexity |

---

## 🤝 Contributing

### Development Setup
```bash
git clone https://github.com/Raju-CS8/JobFlow.git
cd JobFlow
python -m venv venv
.\venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

### Making Changes
1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and test: `pytest`
3. Commit: `git commit -m "Add feature description"`
4. Push: `git push origin feature/your-feature`
5. Open Pull Request

---

## 📝 License

This project is licensed under the **MIT License** — see LICENSE file for details.

---

## 👨‍💼 Author

**Raju CS** — MCA Student, CHRIST (Deemed to be University), Bengaluru

---

## 📞 Support & Questions

- 📧 Open an issue on GitHub
- 💬 Check existing issues for similar problems
- 📖 Read API documentation at `/docs` (Swagger UI)

---

## 🎯 Roadmap

### v1.1 (Planned)
- [ ] WebSocket real-time job updates
- [ ] Job scheduling (cron-like)
- [ ] Dead letter queue for permanent failures
- [ ] Prometheus metrics export

### v2.0 (Future)
- [ ] Multi-database support (MySQL, SQLite)
- [ ] Redis integration for distributed caching
- [ ] Kubernetes Helm charts
- [ ] Advanced retry policies (exponential jitter, max duration)

---

## 🚀 Quick Links

- **GitHub:** https://github.com/Raju-CS8/JobFlow
- **API Docs:** http://localhost:8000/docs (when running)
- **Frontend:** http://localhost:5173 (when running)

---

**Made with ❤️ for reliable background job processing**
