"""Pytest fixtures for backend tests."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client() -> TestClient:
    """Create test client for API testing.

    Returns:
        TestClient: FastAPI test client instance
    """
    return TestClient(app)
