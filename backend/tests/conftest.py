"""
Pytest configuration and shared fixtures for endpoint tests.

The RAGSystem is mocked at the module level before app.py is imported so that
heavyweight initialisation (ChromaDB, SentenceTransformers, Anthropic client)
never runs during tests.
"""
import sys
import os

# Make the backend package importable from any working directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Build a reusable mock RAG instance and patch it in before importing app.py
# ---------------------------------------------------------------------------

_mock_rag = MagicMock()
# The startup event calls add_course_folder and unpacks the result as (int, int)
_mock_rag.add_course_folder.return_value = (0, 0)

with patch("rag_system.RAGSystem", return_value=_mock_rag):
    from app import app as _app  # noqa: E402  (import after sys.path manipulation)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_mock_rag():
    """
    Reset the shared mock and install sensible defaults before every test.
    This runs automatically for every test in the suite.
    """
    _mock_rag.reset_mock()

    # Restore the startup-event return value after reset
    _mock_rag.add_course_folder.return_value = (0, 0)

    # Default session behaviour
    _mock_rag.session_manager.create_session.return_value = "session_test_1"

    # Default query response
    _mock_rag.query.return_value = ("Here is a default answer.", ["lesson1.txt"])

    # Default analytics
    _mock_rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Python Basics", "Advanced Python"],
    }

    yield  # test runs here


@pytest.fixture
def client():
    """Provides a FastAPI TestClient bound to the (mocked) app."""
    with TestClient(_app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def mock_rag():
    """
    Gives individual tests direct access to the mock RAGSystem instance so
    they can override return values or inject side-effects.
    """
    return _mock_rag
