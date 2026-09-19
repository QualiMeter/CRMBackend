from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.models import metadata
from app.api.routers.crud import row_json

router=APIRouter(prefix="/documents",tags=["Documents"])
def documents_table():
    return metadata.tables["documents"]

@router.get("")
async def list_documents(university_id:int|None=None,program_id:int|None=None,status:str|None=None,limit:int=Query(50,ge=1,le=200),offset:int=0,db:AsyncSession=Depends(get_db)):
    documents=documents_table(); stmt=select(documents).order_by(documents.c.created_at.desc()).offset(offset).limit(limit)
    if university_id is not None: stmt=stmt.where(documents.c.university_id==university_id)
    if program_id is not None: stmt=stmt.where(documents.c.program_id==program_id)
    if status: stmt=stmt.where(documents.c.status==status)
    return [row_json(x) for x in (await db.execute(stmt)).mappings().all()]

@router.get("/{document_id}/versions")
async def versions(document_id:int,db:AsyncSession=Depends(get_db)):
    versions=metadata.tables["document_versions"]
    rows=(await db.execute(select(versions).where(versions.c.document_id==document_id).order_by(versions.c.version_number.desc()))).mappings().all()
    return [row_json(x) for x in rows]
