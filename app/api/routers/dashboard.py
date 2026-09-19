from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.routers.crud import json_value

router=APIRouter(prefix="/dashboard",tags=["Dashboard"])

@router.get("/universities")
async def university_dashboard(db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(text("SELECT * FROM v_university_dashboard ORDER BY id"))).mappings().all()
    return [{k:json_value(v) for k,v in dict(r).items()} for r in rows]

@router.get("/interactions/{interaction_id}/progress")
async def interaction_progress(interaction_id:int,db:AsyncSession=Depends(get_db)):
    row=(await db.execute(text("SELECT * FROM v_interaction_progress WHERE interaction_id=:id"),{"id":interaction_id})).mappings().first()
    if not row: return {"interaction_id":interaction_id,"stages_total":0,"stages_done":0,"progress_percent":0,"current_stage_position":None}
    return {k:json_value(v) for k,v in dict(row).items()}
