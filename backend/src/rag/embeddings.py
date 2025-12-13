"""Embedding generation using Vertex AI.

Generates vector embeddings for text chunks using Google's
text-embedding-004 model via Vertex AI.
"""

import asyncio
from typing import Sequence

import structlog
from google.cloud import aiplatform
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Batch size for embedding requests
EMBEDDING_BATCH_SIZE = 5

# Initialize Vertex AI
_initialized = False


def _ensure_initialized() -> None:
    """Initialize Vertex AI client if not already done."""
    global _initialized
    if not _initialized:
        aiplatform.init(
            project=settings.gcp_project_id,
            location=settings.vertex_ai_location,
        )
        _initialized = True


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
async def _generate_embedding_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts.

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors
    """
    _ensure_initialized()

    # Use Vertex AI text embeddings
    from vertexai.language_models import TextEmbeddingModel

    model = TextEmbeddingModel.from_pretrained(settings.embedding_model)

    # Run in executor since the API is synchronous
    loop = asyncio.get_event_loop()
    embeddings = await loop.run_in_executor(
        None,
        lambda: model.get_embeddings(texts),
    )

    return [embedding.values for embedding in embeddings]


async def generate_embeddings(texts: Sequence[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts with batching.

    Splits input into batches to respect API limits and
    processes them with retry logic.

    Args:
        texts: Sequence of text strings to embed

    Returns:
        List of embedding vectors (768 dimensions each)
    """
    if not texts:
        return []

    all_embeddings: list[list[float]] = []

    # Process in batches
    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = list(texts[i : i + EMBEDDING_BATCH_SIZE])

        logger.debug(
            "Generating embedding batch",
            batch_start=i,
            batch_size=len(batch),
        )

        try:
            batch_embeddings = await _generate_embedding_batch(batch)
            all_embeddings.extend(batch_embeddings)
        except Exception as e:
            logger.error(
                "Embedding generation failed",
                batch_start=i,
                error=str(e),
                exc_info=True,
            )
            # Return zero vectors for failed batch
            zero_vector = [0.0] * 768
            all_embeddings.extend([zero_vector] * len(batch))

    return all_embeddings


async def generate_single_embedding(text: str) -> list[float]:
    """Generate embedding for a single text.

    Convenience wrapper for single text embedding generation.

    Args:
        text: Text to embed

    Returns:
        Embedding vector (768 dimensions)
    """
    embeddings = await generate_embeddings([text])
    return embeddings[0] if embeddings else [0.0] * 768
