"""Pytest configuration and session isolation fixtures."""

import pytest
from prismera.db.session_store import get_session_store
from prismera.engine import _SESSION_REGISTRY


@pytest.fixture(autouse=True)
def clean_test_sessions():
    """Ensure in-memory and SQLite test sessions are isolated and fresh per test."""
    _SESSION_REGISTRY.clear()
    store = get_session_store()
    try:
        with store._get_connection() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id LIKE 'test_%'")
            conn.commit()
    except Exception:
        pass

    yield

    _SESSION_REGISTRY.clear()
    try:
        with store._get_connection() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id LIKE 'test_%'")
            conn.commit()
    except Exception:
        pass
