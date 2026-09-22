import os, pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not configured")
    from app.core.config import settings
    settings.database_url = os.environ["TEST_DATABASE_URL"]
    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("x-request-id")

def test_validation_error_has_standard_shape(client):
    r = client.post("/api/v1/auth/login", json={})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "request_id" in body

def test_unauthorized_endpoint_has_standard_shape(client):
    r = client.get("/api/v1/me")
    assert r.status_code == 401
    body = r.json()
    assert body["code"] == "UNAUTHORIZED"
    assert body["request_id"]
