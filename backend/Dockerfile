# Multi-stage production Dockerfile for Document Copilot FastAPI backend
FROM python:3.12-slim-bookworm

# Install uv for fast, deterministic dependency management
COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /uvx /bin/

# Environment configurations
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PORT=8000 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Cache layer for dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code and Alembic migrations
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# Expose default port (Railway injects dynamic PORT at runtime)
EXPOSE 8000

# Run Alembic migrations synchronously before launching uvicorn
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
