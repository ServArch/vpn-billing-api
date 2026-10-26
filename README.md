# vpn-billing-api

Asynchronous backend microservice managing VPN user lifecycles, subscription billing, and a two-stage RAG engine for technical support automation.

## Architecture

The system is structured into three primary functional domains:

1. **Billing & Access Core (`app/api/endpoints/`)**
   - User profile and Telegram ID identity mapping.
   - Tariff catalog and flexible subscription lifecycle management with automatic expiry calculations.
   - VPN credential generation (UUID access keys for VLESS Reality protocol).
   - Fully asynchronous ORM interaction using SQLAlchemy 2.0 with declarative 2.0 mappings and connection pooling.

2. **Two-Stage RAG Support Engine (`app/rag/`)**
   - `chunker.py`: Header-aware Markdown parser that chunks documentation while preserving complete breadcrumb hierarchy (H1 > H2 > H3) and metadata across nested subsections.
   - `retriever.py`: Two-stage search pipeline. Stage 1 executes fast bi-encoder candidate retrieval via cosine similarity. Stage 2 runs cross-encoder reranking (`cross-encoder/ms-marco-MiniLM-L-6-v2`) to score query-chunk pairs with cross-attention and filter low-confidence context.
   - `llm_client.py`: Asynchronous HTTP client communicating with OpenAI-compatible or Ollama endpoints, strictly validating structured JSON responses against Pydantic v2 schemas.

3. **ETL & Object Storage Pipeline (`app/etl/`)**
   - `s3_sync.py`: Background batch extraction worker reading historical transactions and subscriber metrics from PostgreSQL with offset/cursor pagination.
   - Compresses payloads with Gzip and uploads archives to S3/MinIO with exponential backoff and jitter for transient connection errors.

## Tech Stack

- **Runtime & Environment**: Python 3.12, `uv` package manager
- **Framework**: FastAPI, Pydantic v2, Pydantic Settings
- **Database & Migrations**: PostgreSQL 16, asyncpg, SQLAlchemy 2.0, Alembic
- **Information Retrieval & ML**: sentence-transformers, CrossEncoder, NumPy
- **Storage & Networking**: aioboto3 (MinIO/S3), httpx
- **Containerization**: Docker, Docker Compose

## Quickstart

### 1. Local Environment Setup

Install dependencies using `uv`:

```bash
# Install dependencies into virtual environment
uv sync

# Copy example environment configuration
cp .env.example .env
```

### 2. Infrastructure via Docker Compose

Spin up PostgreSQL and MinIO services:

```bash
docker compose up -d postgres minio
```

Apply database migrations:

```bash
alembic upgrade head
```

Run application server:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Full Containerized Run

```bash
docker compose up -d --build
```

The API documentation will be accessible at `http://localhost:8000/docs`. MinIO Console is exposed at `http://localhost:9001` (user: `minioadmin`, pass: `minioadminpassword`).

## Key Endpoints

- `POST /users/` - Register or link Telegram user
- `GET /billing/tariffs` - List active subscription plans
- `POST /billing/subscribe` - Activate or extend subscription
- `GET /billing/status/{telegram_id}` - Query active subscription and configuration state
- `POST /configs/` - Generate unique VLESS client configuration
- `POST /support/ask` - Query automated RAG support engine
