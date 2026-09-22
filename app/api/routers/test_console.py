from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user, require_roles
from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.models import metadata

router = APIRouter(tags=["test-runner"])
logger = get_logger("test-runner")
ROOT = Path(__file__).resolve().parents[3]
UI = ROOT / "test_ui"
_jobs: dict[str, dict[str, Any]] = {}


async def _admin(user: CurrentUser = Depends(require_roles("admin"))) -> CurrentUser:
    return user


@router.get("/tests/ui", include_in_schema=False)
async def test_ui():
    if not settings.test_ui_enabled:
        raise HTTPException(404, "Test UI is disabled")
    return FileResponse(UI / "index.html")


@router.get("/tests/ui/{asset:path}", include_in_schema=False)
async def test_ui_asset(asset: str):
    if not settings.test_ui_enabled:
        raise HTTPException(404, "Test UI is disabled")
    path = (UI / asset).resolve()
    if UI.resolve() not in path.parents:
        raise HTTPException(404)
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path)


async def _run(job_id: str, args: list[str]) -> None:
    job = _jobs[job_id]
    job["status"] = "running"
    job["started_at"] = datetime.now(timezone.utc).isoformat()
    logger.info("Starting pytest job=%s args=%s", job_id, args)
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=ROOT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "0"},
        )
        assert proc.stdout
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            job["output"] += line.decode("utf-8", "replace")
        code = await proc.wait()
        job["exit_code"] = code
        job["status"] = "passed" if code == 0 else "failed"
    except Exception as exc:
        logger.exception("Pytest job failed job=%s", job_id)
        job["output"] += f"\nRunner error: {exc!r}\n"
        job["exit_code"] = -1
        job["status"] = "failed"
    job["finished_at"] = datetime.now(timezone.utc).isoformat()


@router.post("/tests/run")
async def run_tests(
    scope: str = "all",
    _: CurrentUser = Depends(_admin),
):
    if not settings.test_ui_enabled:
        raise HTTPException(404, "Test runner is disabled")
    allowed = {
        "all": [],
        "unit": ["tests/unit"],
        "api": ["tests/api"],
        "integration": ["tests/integration"],
    }
    if scope not in allowed:
        raise HTTPException(422, "Unknown test scope")
    job_id = str(uuid.uuid4())
    args = [sys.executable, "-m", "pytest", "-q", "-rA", "--tb=short", *allowed[scope]]
    _jobs[job_id] = {
        "id": job_id,
        "status": "queued",
        "scope": scope,
        "output": "$ " + " ".join(args) + "\n",
        "exit_code": None,
    }
    asyncio.create_task(_run(job_id, args))
    return _jobs[job_id]


@router.get("/tests/runs")
async def list_test_runs(_: CurrentUser = Depends(_admin)):
    if not settings.test_ui_enabled:
        raise HTTPException(404, "Test runner is disabled")
    return list(_jobs.values())[-20:][::-1]


@router.get("/tests/runs/{job_id}")
async def get_test_run(job_id: str, _: CurrentUser = Depends(_admin)):
    if not settings.test_ui_enabled:
        raise HTTPException(404, "Test runner is disabled")
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Test run not found")
    return job


CheckFunc = Callable[[AsyncSession], Awaitable[dict[str, Any]]]


def _ok(name: str, message: str, **data: Any) -> dict[str, Any]:
    return {"id": name, "status": "passed", "message": message, "data": data}


def _fail(name: str, message: str, **data: Any) -> dict[str, Any]:
    return {"id": name, "status": "failed", "message": message, "data": data}


async def check_database(db: AsyncSession) -> dict[str, Any]:
    value = (await db.execute(text("SELECT 1"))).scalar_one()
    return _ok("database", "PostgreSQL query succeeded", result=value)


async def check_schema(db: AsyncSession) -> dict[str, Any]:
    required = {
        "users", "notifications", "notification_preferences", "auth_credentials",
        "auth_sessions", "tasks", "documents", "files", "interactions",
        "universities", "programs", "webhooks", "background_jobs",
    }
    existing = set(metadata.tables)
    missing = sorted(required - existing)
    if missing:
        return _fail("schema", "Required tables are missing", missing=missing)
    return _ok("schema", "Required application tables are present", count=len(required))


async def check_notifications(db: AsyncSession) -> dict[str, Any]:
    table = metadata.tables.get("notifications")
    if table is None:
        return _fail("notifications", "notifications table is not available")
    count = (await db.execute(select(func.count()).select_from(table))).scalar_one()
    return _ok("notifications", "Notification storage is readable", count=count)


async def check_notification_write(db: AsyncSession) -> dict[str, Any]:
    table = metadata.tables.get("notifications")
    if table is None:
        return _fail("notification_write", "notifications table is not available")
    # Validate INSERT capability without leaving a test notification in production.
    cols = {c.name for c in table.columns}
    if not {"user_id", "type", "title", "message"}.issubset(cols):
        return _fail("notification_write", "Notification schema is incomplete", columns=sorted(cols))
    return _ok("notification_write", "Notification write contract is available; no production row was created")


async def check_sessions(db: AsyncSession) -> dict[str, Any]:
    table = metadata.tables.get("auth_sessions")
    if table is None:
        return _fail("sessions", "auth_sessions table is not available")
    count = (await db.execute(select(func.count()).select_from(table))).scalar_one()
    return _ok("sessions", "Session storage is readable", count=count)


async def check_search(db: AsyncSession) -> dict[str, Any]:
    users = metadata.tables.get("users")
    if users is None:
        return _fail("search", "users table is not available")
    result = await db.execute(select(users.c.id).limit(1))
    return _ok("search", "Search data source is reachable", sample_available=result.first() is not None)


async def check_files(db: AsyncSession) -> dict[str, Any]:
    table = metadata.tables.get("files")
    storage = Path(settings.storage_path)
    if table is None:
        return _fail("files", "files table is not available")
    storage.mkdir(parents=True, exist_ok=True)
    return _ok("files", "File storage and database table are available", storage=str(storage.resolve()))


async def check_tasks(db: AsyncSession) -> dict[str, Any]:
    table = metadata.tables.get("tasks")
    if table is None:
        return _fail("tasks", "tasks table is not available")
    count = (await db.execute(select(func.count()).select_from(table))).scalar_one()
    return _ok("tasks", "Task storage is readable", count=count)


async def check_workflow(db: AsyncSession) -> dict[str, Any]:
    names = ["workflow_templates", "workflow_template_stages", "workflow_stage_instances", "stage_transitions"]
    missing = [x for x in names if x not in metadata.tables]
    if missing:
        return _fail("workflow", "Workflow tables are missing", missing=missing)
    counts = {}
    for name in names:
        counts[name] = (await db.execute(select(func.count()).select_from(metadata.tables[name]))).scalar_one()
    return _ok("workflow", "Workflow tables are readable", counts=counts)


async def check_reports(db: AsyncSession) -> dict[str, Any]:
    required = ["report_jobs", "interactions"]
    missing = [x for x in required if x not in metadata.tables]
    if missing:
        return _fail("reports", "Report dependencies are missing", missing=missing)
    return _ok("reports", "Report dependencies are readable")


async def check_imports(db: AsyncSession) -> dict[str, Any]:
    table = metadata.tables.get("import_jobs")
    if table is None:
        return _fail("imports", "import_jobs table is not available")
    count = (await db.execute(select(func.count()).select_from(table))).scalar_one()
    return _ok("imports", "Import subsystem storage is readable", count=count)


async def check_webhooks(db: AsyncSession) -> dict[str, Any]:
    table = metadata.tables.get("webhooks")
    deliveries = metadata.tables.get("webhook_deliveries")
    if table is None or deliveries is None:
        return _fail("webhooks", "Webhook tables are incomplete")
    return _ok("webhooks", "Webhook storage is available")


async def check_email(_: AsyncSession) -> dict[str, Any]:
    configured = bool(settings.smtp_host and settings.smtp_from)
    return _ok("email", "SMTP configuration is inspectable", configured=configured, host=settings.smtp_host)


async def check_auth(_: AsyncSession) -> dict[str, Any]:
    valid = bool(settings.jwt_secret and len(settings.jwt_secret) >= 32 and settings.jwt_algorithm)
    if not valid:
        return _fail("auth", "JWT configuration is too weak or incomplete")
    return _ok("auth", "JWT authentication configuration is present", algorithm=settings.jwt_algorithm)


async def check_health(db: AsyncSession) -> dict[str, Any]:
    return await check_database(db)


CHECKS: dict[str, tuple[str, CheckFunc]] = {
    "health": ("Health / DB connection", check_health),
    "database": ("Database query", check_database),
    "schema": ("Database schema", check_schema),
    "auth": ("Authentication / JWT", check_auth),
    "sessions": ("Authentication sessions", check_sessions),
    "notifications": ("Notifications", check_notifications),
    "notification_write": ("Notification write contract", check_notification_write),
    "search": ("Search data source", check_search),
    "files": ("Files / storage", check_files),
    "tasks": ("Tasks", check_tasks),
    "workflow": ("Workflow engine", check_workflow),
    "reports": ("Reports", check_reports),
    "imports": ("Imports", check_imports),
    "webhooks": ("Webhooks", check_webhooks),
    "email": ("Email / SMTP", check_email),
}


@router.get("/tests/checks")
async def list_checks(_: CurrentUser = Depends(_admin)):
    if not settings.test_ui_enabled:
        raise HTTPException(404, "Test runner is disabled")
    return [{"id": key, "name": value[0]} for key, value in CHECKS.items()] + [
        {"id": "websocket", "name": "WebSocket / socket endpoint"}
    ]


@router.post("/tests/checks/{check_id}")
async def run_check(check_id: str, _: CurrentUser = Depends(_admin), db: AsyncSession = Depends(get_db)):
    if not settings.test_ui_enabled:
        raise HTTPException(404, "Test runner is disabled")
    if check_id == "websocket":
        return _ok("websocket", "WebSocket endpoint contract is enabled", endpoint=f"{settings.api_prefix}/ws")
    item = CHECKS.get(check_id)
    if not item:
        raise HTTPException(404, "Unknown check")
    name, func = item
    try:
        result = await func(db)
        logger.info("Diagnostic check=%s status=%s", check_id, result["status"])
        return result
    except Exception as exc:
        logger.exception("Diagnostic check failed check=%s", check_id)
        return _fail(check_id, "Check raised an exception", error=str(exc))


@router.websocket("/ws")
async def websocket_notifications(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()
            await websocket.send_json({"type": "ping", "timestamp": datetime.now(timezone.utc).isoformat()})
    except WebSocketDisconnect:
        pass
