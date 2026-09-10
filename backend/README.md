# Document Copilot — Backend Service

This is the FastAPI backend service for **Document Copilot**, powering SEC filing ingestion, hybrid retrieval (pgvector + full-text search), citation validation, and PydanticAI streaming orchestration.

---

## 🚀 Quickstart

### 1. Prerequisites
- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) package manager
- Hosted Supabase project (Auth + Postgres + pgvector)

### 2. Environment Setup
Copy the example environment file and configure your credentials:

```bash
cd backend
cp .env.example .env
```

Ensure your `.env` contains:
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `DATABASE_URL`: Direct/session database connection (host: `db.<ref>.supabase.co:5432`). **Do not use the transaction pooler for Alembic migrations.**
- `GEMINI_API_KEY` (or `OPENAI_API_KEY`)
- `ALLOWED_ORIGINS` (default: `http://localhost:5173`)

### 3. Install Dependencies
Install exact locked dependencies into the virtual environment:

```bash
uv sync
```

---

## 🏃 Running the Application

### Development Server (with auto-reload)
```bash
uv run uvicorn app.main:app --reload --port 8000
```

Or run directly via Python:
```bash
uv run python app/main.py
```

The API will be available at:
- **Root**: [http://localhost:8000/](http://localhost:8000/)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Interactive OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🗄️ Database Migrations (Alembic)

Alembic manages schema migrations against Supabase Postgres.

### Apply Migrations
```bash
uv run alembic upgrade head
```

### Create a New Migration (after modifying `app/database/models.py`)
```bash
uv run alembic revision --autogenerate -m "describe your changes"
```

> **Important**: Always review generated migration scripts in `alembic/versions/` to verify explicit operations for Postgres/Supabase features (e.g. `pgvector` extension, generated `tsvector` columns, HNSW/GIN indexes, and RLS policies).

---

## 📦 Managing Dependencies with `uv`

- **Add a runtime package**:
  ```bash
  uv add <package-name>
  ```
- **Add a development package**:
  ```bash
  uv add --dev <package-name>
  ```
- **Lock and sync**:
  ```bash
  uv lock
  uv sync
  ```

---

## 🧪 Testing and Quality Checks

- **Run unit tests**:
  ```bash
  uv run pytest
  ```
- **Lint and format checks**:
  ```bash
  uv run ruff check .
  ```
- **Auto-fix lint issues**:
  ```bash
  uv run ruff check --fix .
  ```

---

## 📁 Project Structure

```text
backend/
├── alembic/              # Database migration scripts & env.py
├── alembic.ini           # Alembic configuration
├── app/
│   ├── api/              # FastAPI routers (chat, threads, ingest)
│   ├── assistant/        # PydanticAI agent, dependencies & citation models
│   ├── auth/             # Supabase JWT auth verification & dependencies
│   ├── chat/             # Orchestration, streaming & AI SDK message formats
│   ├── database/         # SQLAlchemy models & Supabase DB helpers
│   ├── grounding/        # Citation & answer grounding validators
│   ├── retrieval/        # pgvector, full-text search & RRF ranking
│   ├── config.py         # Pydantic Settings (single source of truth for env)
│   └── main.py           # FastAPI application entrypoint
├── ingest/               # SEC filing parsers, chunkers & embedding scripts
├── tests/                # Unit and integration test suite
├── pyproject.toml        # Dependencies and project metadata
└── README.md             # This guide
```
