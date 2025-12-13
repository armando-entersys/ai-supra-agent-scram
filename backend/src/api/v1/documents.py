"""Document management endpoints for RAG knowledge base.

Handles file uploads, processing status, and document lifecycle.
"""

import hashlib
import os
from pathlib import Path
from typing import Annotated
from uuid import UUID

import aiofiles
import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database.connection import get_db
from src.database.models import Document, DocumentChunk
from src.rag.ingestion import process_document
from src.schemas.documents import (
    DocumentListResponse,
    DocumentResponse,
    DocumentStatus,
    DocumentUploadResponse,
    SearchRequest,
    SearchResponse,
)

logger = structlog.get_logger()
settings = get_settings()

router = APIRouter(prefix="/documents", tags=["Documents"])

# Allowed MIME types for upload
ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
    "text/markdown": ".md",
}

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB as per MD070
UPLOAD_DIR = Path("/app/uploads")


def validate_file_magic(content: bytes, mime_type: str) -> bool:
    """Validate file content matches claimed MIME type using magic numbers.

    Args:
        content: File content bytes
        mime_type: Claimed MIME type

    Returns:
        True if magic numbers match expected type
    """
    magic_numbers = {
        "application/pdf": b"%PDF",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": b"PK\x03\x04",
    }

    if mime_type in magic_numbers:
        return content.startswith(magic_numbers[mime_type])

    # Text files don't have magic numbers
    if mime_type in ("text/plain", "text/markdown"):
        try:
            content[:1000].decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False

    return False


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(description="Document to upload")],
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload a document for RAG processing.

    Validates file type and size, stores the file, and queues
    background processing for text extraction and embedding.

    Args:
        background_tasks: FastAPI background task handler
        file: Uploaded file
        db: Database session

    Returns:
        Upload confirmation with document ID

    Raises:
        HTTPException: If file validation fails
    """
    # Validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Supported: {', '.join(ALLOWED_MIME_TYPES.values())}",
        )

    # Read and validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # Validate magic numbers (security check per MD070 4.2)
    if not validate_file_magic(content, file.content_type):
        raise HTTPException(
            status_code=400,
            detail="File content does not match declared type",
        )

    # Generate unique filename
    file_hash = hashlib.sha256(content).hexdigest()[:16]
    extension = ALLOWED_MIME_TYPES[file.content_type]
    safe_name = f"{file_hash}{extension}"

    # Ensure upload directory exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / safe_name

    # Save file
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Create document record
    document = Document(
        filename=safe_name,
        original_name=file.filename or "unknown",
        mime_type=file.content_type,
        file_size=len(content),
        status=DocumentStatus.PENDING.value,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    logger.info(
        "Document uploaded",
        document_id=str(document.id),
        filename=file.filename,
        size=len(content),
    )

    # Queue background processing
    background_tasks.add_task(
        process_document,
        document_id=document.id,
        file_path=str(file_path),
    )

    return DocumentUploadResponse(
        id=document.id,
        filename=document.filename,
        original_name=document.original_name,
        mime_type=document.mime_type,
        file_size=document.file_size,
        status=DocumentStatus(document.status),
        message="Document uploaded and queued for processing",
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: Annotated[DocumentStatus | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """List all documents with pagination.

    Args:
        page: Page number (1-indexed)
        page_size: Items per page
        status: Optional status filter
        db: Database session

    Returns:
        Paginated list of documents
    """
    # Count total
    count_query = select(func.count(Document.id))
    if status:
        count_query = count_query.where(Document.status == status.value)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get documents
    query = (
        select(Document)
        .order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if status:
        query = query.where(Document.status == status.value)

    result = await db.execute(query)
    documents = result.scalars().all()

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                original_name=doc.original_name,
                mime_type=doc.mime_type,
                file_size=doc.file_size,
                status=DocumentStatus(doc.status),
                chunk_count=doc.chunk_count,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                metadata=doc.metadata_ or {},
            )
            for doc in documents
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Get document details by ID.

    Args:
        document_id: Document UUID
        db: Database session

    Returns:
        Document details

    Raises:
        HTTPException: If document not found
    """
    query = select(Document).where(Document.id == document_id)
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        original_name=document.original_name,
        mime_type=document.mime_type,
        file_size=document.file_size,
        status=DocumentStatus(document.status),
        chunk_count=document.chunk_count,
        created_at=document.created_at,
        updated_at=document.updated_at,
        metadata=document.metadata_ or {},
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete a document and all its chunks.

    Args:
        document_id: Document UUID
        db: Database session

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If document not found
    """
    query = select(Document).where(Document.id == document_id)
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file from disk
    file_path = UPLOAD_DIR / document.filename
    if file_path.exists():
        os.remove(file_path)

    # Delete from database (cascades to chunks)
    await db.delete(document)
    await db.commit()

    logger.info("Document deleted", document_id=str(document_id))

    return {"message": "Document deleted successfully"}


@router.post("/{document_id}/reindex")
async def reindex_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Force re-indexation of a document.

    Deletes existing chunks and re-processes the document.

    Args:
        document_id: Document UUID
        background_tasks: FastAPI background task handler
        db: Database session

    Returns:
        Reindex confirmation

    Raises:
        HTTPException: If document not found
    """
    query = select(Document).where(Document.id == document_id)
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete existing chunks
    delete_query = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    chunk_result = await db.execute(delete_query)
    for chunk in chunk_result.scalars():
        await db.delete(chunk)

    # Reset document status
    document.status = DocumentStatus.PENDING.value
    document.chunk_count = 0
    await db.commit()

    # Queue reprocessing
    file_path = UPLOAD_DIR / document.filename
    background_tasks.add_task(
        process_document,
        document_id=document.id,
        file_path=str(file_path),
    )

    logger.info("Document reindex queued", document_id=str(document_id))

    return {"message": "Document queued for re-indexation"}


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Semantic search across document chunks.

    Uses vector similarity search to find relevant document fragments.

    Args:
        request: Search parameters
        db: Database session

    Returns:
        Search results with similarity scores
    """
    from src.rag.retrieval import search_similar_chunks

    results = await search_similar_chunks(
        db=db,
        query=request.query,
        top_k=request.top_k,
        threshold=request.threshold,
    )

    return SearchResponse(
        query=request.query,
        results=results,
        total_results=len(results),
    )
