import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/crm")
os.environ.setdefault("LOG_LEVEL", "WARNING")
import pytest

@pytest.fixture
def route_map():
    from app.main import app
    return {r.path: sorted(getattr(r, "methods", []) or []) for r in app.routes if hasattr(r, "path")}
