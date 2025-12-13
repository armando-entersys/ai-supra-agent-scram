"""Chat endpoints with SSE streaming.

Implements conversational AI with MCP tool support and RAG context.
"""

import json
from typing import Annotated, AsyncGenerator
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.connection import get_db
from src.database.models import ChatMessage, ChatSession
from src.mcp.orchestrator import AgentOrchestrator
from src.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatStreamRequest,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    request: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
) -> ChatSessionResponse:
    """Create a new chat session.

    Args:
        request: Session creation parameters
        db: Database session

    Returns:
        Created session details
    """
    session = ChatSession(
        title=request.title,
        user_id=request.user_id,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info("Chat session created", session_id=str(session.id))

    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        user_id=session.user_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0,
    )


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    user_id: Annotated[str | None, Query(description="Filter by user ID")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
) -> list[ChatSessionResponse]:
    """List chat sessions with pagination.

    Args:
        user_id: Optional user ID filter
        limit: Maximum results
        offset: Pagination offset
        db: Database session

    Returns:
        List of sessions with message counts
    """
    query = (
        select(
            ChatSession,
            func.count(ChatMessage.id).label("message_count"),
        )
        .outerjoin(ChatMessage)
        .group_by(ChatSession.id)
        .order_by(ChatSession.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if user_id:
        query = query.where(ChatSession.user_id == user_id)

    result = await db.execute(query)
    rows = result.all()

    return [
        ChatSessionResponse(
            id=session.id,
            title=session.title,
            user_id=session.user_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=count,
        )
        for session, count in rows
    ]


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ChatSessionResponse:
    """Get chat session details.

    Args:
        session_id: Session UUID
        db: Database session

    Returns:
        Session details with message count

    Raises:
        HTTPException: If session not found
    """
    query = (
        select(
            ChatSession,
            func.count(ChatMessage.id).label("message_count"),
        )
        .outerjoin(ChatMessage)
        .where(ChatSession.id == session_id)
        .group_by(ChatSession.id)
    )

    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    session, count = row

    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        user_id=session.user_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=count,
    )


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def get_messages(
    session_id: UUID,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    db: AsyncSession = Depends(get_db),
) -> list[ChatMessageResponse]:
    """Get messages from a chat session.

    Args:
        session_id: Session UUID
        limit: Maximum messages to return
        db: Database session

    Returns:
        List of messages in chronological order
    """
    query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
    )

    result = await db.execute(query)
    messages = result.scalars().all()

    return [
        ChatMessageResponse(
            id=msg.id,
            session_id=msg.session_id,
            role=msg.role,
            content=msg.content,
            tool_calls=msg.tool_calls,
            created_at=msg.created_at,
        )
        for msg in messages
    ]


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete a chat session and all its messages.

    Args:
        session_id: Session UUID
        db: Database session

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If session not found
    """
    query = select(ChatSession).where(ChatSession.id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.delete(session)
    await db.commit()

    logger.info("Chat session deleted", session_id=str(session_id))

    return {"message": "Session deleted successfully"}


@router.post("/stream")
async def stream_chat(
    request: ChatStreamRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream chat response with SSE.

    Processes user message through Gemini with optional RAG context
    and MCP tools, streaming the response as Server-Sent Events.

    Args:
        request: Chat stream request with message and options
        db: Database session

    Returns:
        StreamingResponse with SSE events
    """
    # Get or create session
    if request.session_id:
        query = select(ChatSession).where(ChatSession.id == request.session_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = ChatSession(title=request.message[:50])
        db.add(session)
        await db.commit()
        await db.refresh(session)

    # Save user message
    user_message = ChatMessage(
        session_id=session.id,
        role="user",
        content=request.message,
    )
    db.add(user_message)
    await db.commit()

    async def generate() -> AsyncGenerator[str, None]:
        """Generate SSE events for chat stream."""
        orchestrator = AgentOrchestrator()
        full_response = ""
        tool_calls_data: list[dict] = []

        try:
            # Get conversation history
            history_query = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session.id)
                .order_by(ChatMessage.created_at.asc())
                .limit(20)
            )
            history_result = await db.execute(history_query)
            history = history_result.scalars().all()

            messages = [
                {"role": msg.role, "content": msg.content}
                for msg in history
            ]

            # Stream response from orchestrator
            async for event in orchestrator.stream_response(
                messages=messages,
                use_rag=request.use_rag,
                use_analytics=request.use_analytics,
            ):
                if event["type"] == "text":
                    full_response += event["content"]
                    yield f"data: {json.dumps({'event': 'text', 'data': event['content']})}\n\n"

                elif event["type"] == "tool_call":
                    tool_calls_data.append(event["data"])
                    yield f"data: {json.dumps({'event': 'tool_call', 'data': event['data']})}\n\n"

                elif event["type"] == "error":
                    yield f"data: {json.dumps({'event': 'error', 'data': event['message']})}\n\n"

            # Save assistant response
            assistant_message = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=full_response,
                tool_calls={"calls": tool_calls_data} if tool_calls_data else None,
            )
            db.add(assistant_message)
            await db.commit()

            yield f"data: {json.dumps({'event': 'done', 'data': {'session_id': str(session.id)}})}\n\n"

        except Exception as e:
            logger.error("Chat stream error", error=str(e), exc_info=True)
            yield f"data: {json.dumps({'event': 'error', 'data': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
