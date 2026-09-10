"""Gemini text-embedding-004 client for dense vector generation.

Generates 768-dimensional float embeddings in batches with retry and exponential backoff.
"""

from __future__ import annotations

import time

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiEmbedder:
    """Generates dense vector embeddings using Google's text-embedding-004 model."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        dimensions: int | None = None,
        batch_size: int = 50,
    ):
        self.api_key = api_key or settings.gemini_api_key
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required to generate embeddings.")

        self.model_name = model_name or settings.embedding_model
        self.dimensions = dimensions or settings.embedding_dimensions
        self.batch_size = batch_size

    def embed_text(self, text: str) -> list[float]:
        """Generate a single 768-dimensional embedding vector for input text."""
        vectors = self.embed_batch([text])
        return vectors[0] if vectors else []

    def embed_batch(
        self,
        texts: list[str],
        max_retries: int = 4,
    ) -> list[list[float]]:
        """Generate vector embeddings for a list of texts in batches.

        Returns a list of float arrays, each of length `self.dimensions` (768).
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        total_chunks = len(texts)

        for i in range(0, total_chunks, self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total_chunks + self.batch_size - 1) // self.batch_size

            logger.info(
                "embedder.batch_start",
                batch=batch_num,
                total_batches=total_batches,
                batch_size=len(batch),
            )

            embeddings = self._embed_batch_with_retry(batch, max_retries=max_retries)
            all_embeddings.extend(embeddings)

            # Polite rate limiting between batches
            if i + self.batch_size < total_chunks:
                time.sleep(0.5)

        return all_embeddings

    def _embed_batch_with_retry(
        self,
        batch_texts: list[str],
        max_retries: int = 4,
    ) -> list[list[float]]:
        """Post a single batch of texts to Gemini batchEmbedContents with exponential backoff."""
        url = f"{GEMINI_API_URL}/models/{self.model_name}:batchEmbedContents?key={self.api_key}"

        # Truncate texts if exceptionally long to respect model limits
        requests_payload = [
            {
                "model": f"models/{self.model_name}",
                "content": {"parts": [{"text": text[:8000]}]},
                "outputDimensionality": self.dimensions,
            }
            for text in batch_texts
        ]

        payload = {"requests": requests_payload}

        for attempt in range(1, max_retries + 1):
            try:
                with httpx.Client(timeout=60.0) as client:
                    response = client.post(url, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    raw_embeddings = data.get("embeddings", [])
                    return [item.get("values", []) for item in raw_embeddings]

                elif response.status_code == 429:
                    wait_time = 2 ** attempt
                    logger.warning(
                        "embedder.rate_limited",
                        status_code=429,
                        retry_in=wait_time,
                        attempt=attempt,
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        "embedder.api_error",
                        status_code=response.status_code,
                        response_text=response.text[:200],
                        attempt=attempt,
                    )
                    if attempt == max_retries:
                        raise RuntimeError(
                            f"Gemini embedding API returned {response.status_code}: {response.text}"
                        )
                    time.sleep(2 ** attempt)

            except httpx.RequestError as exc:
                logger.warning(
                    "embedder.request_error",
                    error=str(exc),
                    attempt=attempt,
                )
                if attempt == max_retries:
                    raise
                time.sleep(2 ** attempt)

        raise RuntimeError("Failed to generate embeddings after maximum retries.")
