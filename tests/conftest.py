"""Shared pytest fixtures for the Spendly test suite.

Every test gets a fresh, isolated temp SQLite DB (never the real
``spendly.db`` file in the project root) with the schema created and the
demo user (``demo@spendly.com`` / ``demo123``) seeded exactly once.
"""

import pytest

from app import app as flask_app
import database.db as db
from database.db import init_db, seed_db


@pytest.fixture
def app(tmp_path, monkeypatch):
    """A configured Flask app backed by a per-test temp SQLite DB.

    The data layer's ``DB_PATH`` is monkeypatched to a throwaway file so no
    test can ever clobber the real ``spendly.db``. On top of the fresh
    schema, the demo user and its 8 seeded expenses are inserted.
    """
    test_db_path = str(tmp_path / "test-spendly.db")
    monkeypatch.setattr(db, "DB_PATH", test_db_path)

    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
        WTF_CSRF_ENABLED=False,
    )

    with flask_app.app_context():
        init_db()
        seed_db()

    return flask_app


@pytest.fixture
def client(app):
    """An unauthenticated Flask test client."""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """A test client logged in as a freshly registered, non-demo user."""
    response = client.post(
        "/register",
        data={
            "name": "New User",
            "email": "newuser@example.com",
            "password": "secret-password",
        },
    )
    assert response.status_code in (200, 302)
    return client


@pytest.fixture
def demo_client(client):
    """A test client logged in as the seeded ``demo@spendly.com`` user."""
    response = client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
    )
    assert response.status_code in (200, 302)
    return client