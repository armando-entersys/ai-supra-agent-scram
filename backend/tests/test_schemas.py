"""Tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError

from src.schemas.chat import ChatMessageCreate, ChatSessionCreate, ChatStreamRequest
from src.schemas.documents import DocumentStatus, SearchRequest


class TestChatSchemas:
    """Tests for chat schemas."""

    def test_chat_session_create_valid(self) -> None:
        """Test valid session creation."""
        session = ChatSessionCreate(title="Test Session", user_id="user123")
        assert session.title == "Test Session"
        assert session.user_id == "user123"

    def test_chat_session_create_optional_fields(self) -> None:
        """Test session creation with optional fields."""
        session = ChatSessionCreate()
        assert session.title is None
        assert session.user_id is None

    def test_chat_message_create_valid(self) -> None:
        """Test valid message creation."""
        message = ChatMessageCreate(content="Hello, world!")
        assert message.content == "Hello, world!"

    def test_chat_message_create_empty_fails(self) -> None:
        """Test empty message fails validation."""
        with pytest.raises(ValidationError):
            ChatMessageCreate(content="")

    def test_chat_stream_request_defaults(self) -> None:
        """Test stream request defaults."""
        request = ChatStreamRequest(message="Test message")
        assert request.use_rag is True
        assert request.use_analytics is True
        assert request.session_id is None


class TestDocumentSchemas:
    """Tests for document schemas."""

    def test_document_status_enum(self) -> None:
        """Test document status enum values."""
        assert DocumentStatus.PENDING.value == "pending"
        assert DocumentStatus.PROCESSING.value == "processing"
        assert DocumentStatus.INDEXED.value == "indexed"
        assert DocumentStatus.ERROR.value == "error"

    def test_search_request_valid(self) -> None:
        """Test valid search request."""
        request = SearchRequest(query="test query")
        assert request.query == "test query"
        assert request.top_k == 5
        assert request.threshold == 0.7

    def test_search_request_custom_params(self) -> None:
        """Test search request with custom parameters."""
        request = SearchRequest(query="test", top_k=10, threshold=0.8)
        assert request.top_k == 10
        assert request.threshold == 0.8

    def test_search_request_invalid_top_k(self) -> None:
        """Test search request with invalid top_k."""
        with pytest.raises(ValidationError):
            SearchRequest(query="test", top_k=100)  # Max is 20

    def test_search_request_invalid_threshold(self) -> None:
        """Test search request with invalid threshold."""
        with pytest.raises(ValidationError):
            SearchRequest(query="test", threshold=1.5)  # Max is 1.0
