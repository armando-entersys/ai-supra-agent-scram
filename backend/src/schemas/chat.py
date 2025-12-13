"""Pydantic schemas for chat endpoints."""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    """Request schema for creating a chat session."""

    title: Annotated[
        str | None,
        Field(default=None, max_length=255, description="Optional session title"),
    ]
    user_id: Annotated[
        str | None,
        Field(default=None, max_length=255, description="Optional user identifier"),
    ]

    model_config = {"strict": True}


class ChatSessionResponse(BaseModel):
    """Response schema for chat session."""

    id: UUID
    title: str | None
    user_id: str | None
    created_at: datetime
    updated_at: datetime
    message_count: Annotated[int, Field(default=0)]

    model_config = {"from_attributes": True}


class ChatMessageCreate(BaseModel):
    """Request schema for creating a chat message."""

    content: Annotated[
        str,
        Field(min_length=1, max_length=10000, description="Message content"),
    ]

    model_config = {"strict": True}


class ChatMessageResponse(BaseModel):
    """Response schema for chat message."""

    id: UUID
    session_id: UUID
    role: Annotated[str, Field(description="Message role: user, assistant, system")]
    content: str
    tool_calls: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatStreamRequest(BaseModel):
    """Request schema for streaming chat."""

    message: Annotated[
        str,
        Field(min_length=1, max_length=10000, description="User message"),
    ]
    session_id: Annotated[
        UUID | None,
        Field(default=None, description="Existing session ID or None for new"),
    ]
    use_rag: Annotated[
        bool,
        Field(default=True, description="Enable RAG context retrieval"),
    ]
    use_analytics: Annotated[
        bool,
        Field(default=True, description="Enable Google Analytics tools"),
    ]

    # Note: Not using strict mode to allow string-to-UUID coercion from JSON


class ToolCallEvent(BaseModel):
    """Schema for tool call events in SSE stream."""

    tool_name: str
    tool_input: dict[str, Any]
    status: Annotated[str, Field(description="pending, running, completed, error")]
    result: Any | None = None


class StreamEvent(BaseModel):
    """Schema for SSE stream events."""

    event: Annotated[
        str,
        Field(description="Event type: text, tool_call, error, done"),
    ]
    data: str | ToolCallEvent | dict[str, Any]
