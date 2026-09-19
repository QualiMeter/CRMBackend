from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.auth import CurrentUser, require_roles
from app.schemas.schemas import ListResponse

router=APIRouter(prefix="/dashboard",tags=["dashboard"])

@router.get("/universities", dependencies=[Depends(require_roles("admin","manager","user"))])
async def university_dashboard(db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(text("SELECT * FROM v_university_dashboard ORDER BY id"))).mappings().all()
    return [dict(r) for r in rows]

@router.get("/interactions/{interaction_id}/progress", dependencies=[Depends(require_roles("admin","manager","user"))])
async def interaction_progress(interaction_id:int,db:AsyncSession=Depends(get_db)):
    row=(await db.execute(text("SELECT * FROM v_interaction_progress WHERE interaction_id=:id"),{"id":interaction_id})).mappings().first()
    if not row: return {"interaction_id":interaction_id,"stages_total":0,"stages_done":0,"progress_percent":0,"current_stage_position":None}
    return dict(row)
