from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.models import metadata
from app.api.routers.crud import row_json

router=APIRouter(prefix="/tasks",tags=["Tasks"])
def tasks_table():
    return metadata.tables["tasks"]

@router.get("")
async def list_tasks(university_id:int|None=None,assignee_id:int|None=None,status:str|None=None,priority:str|None=None,limit:int=Query(50,ge=1,le=200),offset:int=0,db:AsyncSession=Depends(get_db)):
    tasks=tasks_table(); stmt=select(tasks).order_by(tasks.c.due_at.nulls_last(),tasks.c.id).offset(offset).limit(limit)
    if university_id is not None: stmt=stmt.where(tasks.c.university_id==university_id)
    if assignee_id is not None: stmt=stmt.where(tasks.c.assignee_id==assignee_id)
    if status: stmt=stmt.where(tasks.c.status==status)
    if priority: stmt=stmt.where(tasks.c.priority==priority)
    return [row_json(x) for x in (await db.execute(stmt)).mappings().all()]

@router.patch("/{task_id}")
async def update_task(task_id:int,payload:dict,db:AsyncSession=Depends(get_db)):
    if payload.get("status")=="done" and "completed_at" not in payload: payload["completed_at"]=datetime.now(timezone.utc)
    if payload.get("status") in {"open","in_progress","cancelled"}: payload["completed_at"]=None
    tasks=tasks_table(); result=await db.execute(update(tasks).where(tasks.c.id==task_id).values(**payload).returning(*tasks.c))
    row=result.mappings().first()
    if not row: from fastapi import HTTPException; raise HTTPException(404,"Task not found")
    await db.commit(); return row_json(row)
