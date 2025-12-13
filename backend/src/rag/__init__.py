"""RAG (Retrieval-Augmented Generation) pipeline module.

Handles document ingestion, embedding generation, and semantic search.
"""

from src.rag.embeddings import generate_embeddings, generate_single_embedding
from src.rag.ingestion import process_document
from src.rag.retrieval import get_context_for_query, search_similar_chunks

__all__ = [
    "generate_embeddings",
    "generate_single_embedding",
    "process_document",
    "get_context_for_query",
    "search_similar_chunks",
]
