from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "backend.startup",
        environment=settings.environment,
        allowed_origins=settings.cors_origins,
    )
    yield
    logger.info("backend.shutdown")


app = FastAPI(
    title="Document Copilot API",
    description="Internal research assistant API for grounded SEC filing analysis",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for React SPA
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "Document Copilot API", "status": "running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
