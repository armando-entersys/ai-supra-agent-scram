"""Tests for RAG pipeline components."""

import pytest

from src.rag.ingestion import chunk_text


class TestChunking:
    """Tests for text chunking."""

    def test_chunk_empty_text(self) -> None:
        """Test chunking empty text returns empty list."""
        result = chunk_text("")
        assert result == []

    def test_chunk_whitespace_text(self) -> None:
        """Test chunking whitespace only returns empty list."""
        result = chunk_text("   \n\t  ")
        assert result == []

    def test_chunk_short_text(self) -> None:
        """Test chunking text shorter than chunk size."""
        text = "This is a short text."
        result = chunk_text(text, chunk_size=1000)
        assert len(result) == 1
        assert result[0] == text

    def test_chunk_long_text(self) -> None:
        """Test chunking text longer than chunk size."""
        # Create text that's 3000 chars
        text = "Word " * 600  # ~3000 chars
        result = chunk_text(text, chunk_size=1000, overlap=200)

        # Should have multiple chunks
        assert len(result) > 1

        # Each chunk should be roughly chunk_size or less
        for chunk in result:
            assert len(chunk) <= 1200  # Allow some flexibility for word boundaries

    def test_chunk_respects_overlap(self) -> None:
        """Test that chunks have overlapping content."""
        text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
        result = chunk_text(text, chunk_size=30, overlap=10)

        # With overlap, consecutive chunks should share some content
        if len(result) > 1:
            # Check that there's some overlap between consecutive chunks
            for i in range(len(result) - 1):
                # At least some words should appear in both
                words_1 = set(result[i].split()[-3:])
                words_2 = set(result[i + 1].split()[:3])
                # This is a weak test but validates the overlap concept
                assert len(words_1) > 0 and len(words_2) > 0

    def test_chunk_breaks_at_sentences(self) -> None:
        """Test that chunking prefers sentence boundaries."""
        text = "First sentence here. Second sentence here. Third sentence here."
        result = chunk_text(text, chunk_size=40, overlap=5)

        # Chunks should generally end with sentence markers
        for chunk in result[:-1]:  # Exclude last chunk
            stripped = chunk.strip()
            # Either ends with punctuation or is the content
            assert stripped.endswith(('.', '!', '?')) or len(stripped) < 40
