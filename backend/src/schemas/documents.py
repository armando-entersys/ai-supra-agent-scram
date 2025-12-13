"""Pydantic schemas for document endpoints."""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    ERROR = "error"


class DocumentUploadResponse(BaseModel):
    """Response schema for document upload."""

    id: UUID
    filename: str
    original_name: str
    mime_type: str
    file_size: int
    status: DocumentStatus
    message: str

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    """Response schema for document details."""

    id: UUID
    filename: str
    original_name: str
    mime_type: str
    file_size: int
    status: DocumentStatus
    chunk_count: int
    created_at: datetime
    updated_at: datetime
    metadata: Annotated[dict[str, Any], Field(default_factory=dict)]

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Response schema for document list."""

    documents: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class ChunkResponse(BaseModel):
    """Response schema for document chunk."""

    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    token_count: int | None
    similarity: Annotated[float | None, Field(default=None)]

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    """Request schema for semantic search."""

    query: Annotated[
        str,
        Field(min_length=1, max_length=1000, description="Search query"),
    ]
    top_k: Annotated[
        int,
        Field(default=5, ge=1, le=20, description="Number of results"),
    ]
    threshold: Annotated[
        float,
        Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold"),
    ]

    model_config = {"strict": True}


class SearchResponse(BaseModel):
    """Response schema for semantic search."""

    query: str
    results: list[ChunkResponse]
    total_results: int
