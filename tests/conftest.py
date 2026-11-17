import pytest
from fastapi.testclient import TestClient

from app.database import db
from app.main import app


@pytest.fixture(autouse=True)
def clean_db():
    """Resets database before each test run for test isolation."""
    db.reset()
    yield
    db.reset()


@pytest.fixture
def client():
    """Provides FastAPI TestClient."""
    with TestClient(app) as test_client:
        yield test_client
