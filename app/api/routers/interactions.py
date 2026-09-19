from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.models import metadata
from app.api.routers.crud import row_json

router=APIRouter(prefix="/interactions",tags=["Interactions & Workflow"])

def t(): return metadata.tables["interactions"],metadata.tables["workflow_stage_instances"],metadata.tables["stage_comments"],metadata.tables["stage_transitions"]

@router.get("")
async def list_interactions(university_id:int|None=None,program_id:int|None=None,status:str|None=None,limit:int=Query(50,ge=1,le=200),offset:int=0,db:AsyncSession=Depends(get_db)):
    i,_,_,_=t(); stmt=select(i).order_by(i.c.id.desc()).offset(offset).limit(limit)
    if university_id is not None: stmt=stmt.where(i.c.university_id==university_id)
    if program_id is not None: stmt=stmt.where(i.c.program_id==program_id)
    if status: stmt=stmt.where(i.c.status==status)
    return [row_json(x) for x in (await db.execute(stmt)).mappings().all()]

@router.get("/{interaction_id}")
async def get_interaction(interaction_id:int,db:AsyncSession=Depends(get_db)):
    i,_,_,_=t(); row=(await db.execute(select(i).where(i.c.id==interaction_id))).mappings().first()
    if not row: raise HTTPException(404,"Interaction not found")
    return row_json(row)

@router.get("/{interaction_id}/workflow")
async def workflow(interaction_id:int,db:AsyncSession=Depends(get_db)):
    i,s,_,_=t();
    if not await db.scalar(select(i.c.id).where(i.c.id==interaction_id)): raise HTTPException(404,"Interaction not found")
    rows=(await db.execute(select(s).where(s.c.interaction_id==interaction_id).order_by(s.c.position))).mappings().all()
    return [row_json(x) for x in rows]

@router.patch("/{interaction_id}/workflow/{stage_id}")
async def update_stage(interaction_id:int,stage_id:int,payload:dict,db:AsyncSession=Depends(get_db)):
    i,s,_,_=t();
    if not await db.scalar(select(i.c.id).where(i.c.id==interaction_id)): raise HTTPException(404,"Interaction not found")
    result=await db.execute(update(s).where(s.c.id==stage_id,s.c.interaction_id==interaction_id).values(**payload).returning(*s.c))
    row=result.mappings().first()
    if not row: raise HTTPException(404,"Stage not found")
    await db.commit(); return row_json(row)

@router.get("/{interaction_id}/comments")
async def comments(interaction_id:int,db:AsyncSession=Depends(get_db)):
    i,s,c,_=t();
    rows=(await db.execute(select(c).join(s,s.c.id==c.c.stage_instance_id).where(s.c.interaction_id==interaction_id).order_by(c.c.id))).mappings().all()
    return [row_json(x) for x in rows]
