"""Vector similarity search for RAG retrieval.

Implements semantic search using pgvector's cosine similarity.
"""

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.rag.embeddings import generate_single_embedding
from src.schemas.documents import ChunkResponse

logger = structlog.get_logger()


async def search_similar_chunks(
    db: AsyncSession,
    query: str,
    top_k: int = 5,
    threshold: float = 0.7,
) -> list[ChunkResponse]:
    """Search for document chunks similar to query.

    Uses pgvector's cosine similarity to find the most relevant
    document chunks for the given query.

    Args:
        db: Database session
        query: Search query text
        top_k: Maximum number of results
        threshold: Minimum similarity score (0-1)

    Returns:
        List of matching chunks with similarity scores
    """
    # Generate query embedding
    query_embedding = await generate_single_embedding(query)

    # Convert to string for SQL
    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    # Execute vector search using pgvector
    # Note: Using CAST() instead of :: to avoid asyncpg parameter parsing issues
    sql = text("""
        SELECT
            dc.id,
            dc.document_id,
            dc.chunk_index,
            dc.content,
            dc.token_count,
            1 - (dc.embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM document_chunks dc
        WHERE dc.embedding IS NOT NULL
          AND 1 - (dc.embedding <=> CAST(:embedding AS vector)) > :threshold
        ORDER BY dc.embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """)

    result = await db.execute(
        sql,
        {
            "embedding": embedding_str,
            "threshold": threshold,
            "top_k": top_k,
        },
    )

    rows = result.fetchall()

    logger.info(
        "Vector search completed",
        query_length=len(query),
        results_found=len(rows),
    )

    return [
        ChunkResponse(
            id=row.id,
            document_id=row.document_id,
            chunk_index=row.chunk_index,
            content=row.content,
            token_count=row.token_count,
            similarity=float(row.similarity),
        )
        for row in rows
    ]


async def get_context_for_query(
    db: AsyncSession,
    query: str,
    max_tokens: int = 2000,
    top_k: int = 5,
    threshold: float = 0.7,
) -> str:
    """Get formatted context string for RAG augmentation.

    Retrieves relevant chunks and formats them as context
    for inclusion in the LLM prompt.

    Args:
        db: Database session
        query: User query
        max_tokens: Maximum approximate tokens for context
        top_k: Maximum chunks to retrieve
        threshold: Minimum similarity threshold

    Returns:
        Formatted context string with source references
    """
    chunks = await search_similar_chunks(
        db=db,
        query=query,
        top_k=top_k,
        threshold=threshold,
    )

    if not chunks:
        return ""

    context_parts: list[str] = []
    total_tokens = 0

    for i, chunk in enumerate(chunks, 1):
        chunk_tokens = chunk.token_count or len(chunk.content.split())

        if total_tokens + chunk_tokens > max_tokens:
            break

        context_parts.append(
            f"[Source {i}] (similarity: {chunk.similarity:.2f})\n{chunk.content}"
        )
        total_tokens += chunk_tokens

    if not context_parts:
        return ""

    return (
        "=== Relevant Context from Knowledge Base ===\n\n"
        + "\n\n---\n\n".join(context_parts)
        + "\n\n=== End of Context ==="
    )
