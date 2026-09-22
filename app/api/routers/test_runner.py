from __future__ import annotations
import asyncio, json, os, sys, uuid
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.core.config import settings

router = APIRouter(tags=["test-runner"])
ROOT = Path(__file__).resolve().parents[3]
UI = ROOT / "test_ui"
_jobs: dict[str, dict[str, Any]] = {}

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
    job["started_at"] = asyncio.get_running_loop().time()
    proc = await asyncio.create_subprocess_exec(*args, cwd=ROOT, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    assert proc.stdout
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        text = line.decode("utf-8", "replace")
        job["output"] += text
    code = await proc.wait()
    job["exit_code"] = code
    job["status"] = "passed" if code == 0 else "failed"
    job["finished_at"] = asyncio.get_running_loop().time()

@router.post("/tests/run")
async def run_tests(scope: str = "all"):
    if not settings.test_ui_enabled:
        raise HTTPException(404, "Test runner is disabled")
    allowed = {"all": [], "unit": ["tests/unit"], "api": ["tests/api"], "integration": ["tests/integration"]}
    if scope not in allowed:
        raise HTTPException(422, "Unknown test scope")
    job_id = str(uuid.uuid4())
    args = [sys.executable, "-m", "pytest", "-q", "-rA", "--tb=short", *allowed[scope]]
    _jobs[job_id] = {"id": job_id, "status": "queued", "output": "$ " + " ".join(args) + "\n", "exit_code": None}
    asyncio.create_task(_run(job_id, args))
    return _jobs[job_id]

@router.get("/tests/runs")
async def list_test_runs():
    if not settings.test_ui_enabled:
        raise HTTPException(404, "Test runner is disabled")
    return list(_jobs.values())[-20:][::-1]

@router.get("/tests/runs/{job_id}")
async def get_test_run(job_id: str):
    if not settings.test_ui_enabled:
        raise HTTPException(404, "Test runner is disabled")
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Test run not found")
    return job
