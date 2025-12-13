"""Document ingestion pipeline for RAG.

Extracts text from documents, chunks content, and generates embeddings.
"""

import asyncio
from pathlib import Path
from uuid import UUID

import structlog
from pypdf import PdfReader
from docx import Document as DocxDocument

from src.config import get_settings
from src.database.connection import async_session_maker
from src.database.models import Document, DocumentChunk
from src.rag.embeddings import generate_embeddings
from src.schemas.documents import DocumentStatus

logger = structlog.get_logger()
settings = get_settings()

# Chunking parameters
CHUNK_SIZE = 1000  # characters
CHUNK_OVERLAP = 200  # characters


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text content from PDF file.

    Args:
        file_path: Path to PDF file

    Returns:
        Extracted text content
    """
    reader = PdfReader(file_path)
    text_parts: list[str] = []

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)

    return "\n\n".join(text_parts)


def extract_text_from_docx(file_path: str) -> str:
    """Extract text content from DOCX file.

    Args:
        file_path: Path to DOCX file

    Returns:
        Extracted text content
    """
    doc = DocxDocument(file_path)
    text_parts: list[str] = []

    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text)

    return "\n\n".join(text_parts)


def extract_text_from_txt(file_path: str) -> str:
    """Extract text content from plain text file.

    Args:
        file_path: Path to text file

    Returns:
        File content as string
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def extract_text(file_path: str, mime_type: str) -> str:
    """Extract text from document based on MIME type.

    Args:
        file_path: Path to document file
        mime_type: Document MIME type

    Returns:
        Extracted text content

    Raises:
        ValueError: If MIME type is not supported
    """
    extractors = {
        "application/pdf": extract_text_from_pdf,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": extract_text_from_docx,
        "text/plain": extract_text_from_txt,
        "text/markdown": extract_text_from_txt,
    }

    extractor = extractors.get(mime_type)
    if not extractor:
        raise ValueError(f"Unsupported MIME type: {mime_type}")

    return extractor(file_path)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks.

    Uses a sliding window approach to create chunks with overlap
    for better context preservation during retrieval.

    Args:
        text: Full text content
        chunk_size: Maximum characters per chunk
        overlap: Characters to overlap between chunks

    Returns:
        List of text chunks
    """
    if not text.strip():
        return []

    chunks: list[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size

        # Try to break at sentence boundary
        if end < text_length:
            # Look for sentence endings
            for sep in [". ", ".\n", "? ", "!\n", "\n\n"]:
                last_sep = text.rfind(sep, start, end)
                if last_sep > start + chunk_size // 2:
                    end = last_sep + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position with overlap
        start = end - overlap if end < text_length else text_length

    return chunks


async def process_document(document_id: UUID, file_path: str) -> None:
    """Process uploaded document: extract text, chunk, and embed.

    This function runs as a background task after file upload.

    Args:
        document_id: UUID of the document record
        file_path: Path to the uploaded file
    """
    logger.info("Starting document processing", document_id=str(document_id))

    async with async_session_maker() as db:
        try:
            # Get document record
            from sqlalchemy import select
            query = select(Document).where(Document.id == document_id)
            result = await db.execute(query)
            document = result.scalar_one_or_none()

            if not document:
                logger.error("Document not found", document_id=str(document_id))
                return

            # Update status to processing
            document.status = DocumentStatus.PROCESSING.value
            await db.commit()

            # Extract text
            logger.info("Extracting text", document_id=str(document_id))
            text = extract_text(file_path, document.mime_type)

            if not text.strip():
                document.status = DocumentStatus.ERROR.value
                document.metadata_ = {"error": "No text content extracted"}
                await db.commit()
                return

            # Chunk text
            logger.info("Chunking text", document_id=str(document_id))
            chunks = chunk_text(text)

            if not chunks:
                document.status = DocumentStatus.ERROR.value
                document.metadata_ = {"error": "No chunks generated"}
                await db.commit()
                return

            # Generate embeddings in batches
            logger.info(
                "Generating embeddings",
                document_id=str(document_id),
                chunk_count=len(chunks),
            )
            embeddings = await generate_embeddings(chunks)

            # Create chunk records
            for i, (chunk_text_content, embedding) in enumerate(zip(chunks, embeddings)):
                chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=chunk_text_content,
                    embedding=embedding,
                    token_count=len(chunk_text_content.split()),
                )
                db.add(chunk)

            # Update document status
            document.status = DocumentStatus.INDEXED.value
            document.chunk_count = len(chunks)
            document.metadata_ = {
                "total_characters": len(text),
                "total_chunks": len(chunks),
            }
            await db.commit()

            logger.info(
                "Document processing complete",
                document_id=str(document_id),
                chunks=len(chunks),
            )

        except Exception as e:
            logger.error(
                "Document processing failed",
                document_id=str(document_id),
                error=str(e),
                exc_info=True,
            )
            document.status = DocumentStatus.ERROR.value
            document.metadata_ = {"error": str(e)}
            await db.commit()
