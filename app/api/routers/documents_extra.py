from __future__ import annotations
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
from uuid import UUID
import hashlib
from app.core.auth import CurrentUser, require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models.models import metadata
from app.schemas.schemas import DocumentVersionResponse

router=APIRouter(prefix="/documents",tags=["documents"])
@router.post("/{document_id}/versions/upload",response_model=DocumentVersionResponse,status_code=201)
async def upload_document_version(document_id:int,file:UploadFile=File(...),change_comment:str|None=None,user:CurrentUser=Depends(require_roles("admin","manager","user")),db:AsyncSession=Depends(get_db)):
    docs=metadata.tables['documents']; versions=metadata.tables['document_versions']; files=metadata.tables['files']
    doc=(await db.execute(select(docs).where(docs.c.id==document_id))).mappings().first()
    if not doc: raise HTTPException(404,'Document not found')
    version=(doc['current_version'] or 0)+1
    data=await file.read()
    if len(data)>settings.max_upload_size: raise HTTPException(413,'File too large')
    fid=UUID(bytes=__import__('secrets').token_bytes(16)); key=f'documents/{document_id}/{fid.hex}/{file.filename or "file"}'
    path=Path(settings.storage_path)/key; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
    await db.execute(insert(files).values(id=fid,storage_key=key,original_name=file.filename or 'file',content_type=file.content_type or 'application/octet-stream',size_bytes=len(data),checksum_sha256=hashlib.sha256(data).hexdigest(),uploaded_by=user.id))
    row=(await db.execute(insert(versions).values(document_id=document_id,version_number=version,file_id=fid,uploaded_by=user.id,change_comment=change_comment).returning(versions))).mappings().one()
    await db.execute(update(docs).where(docs.c.id==document_id).values(current_version=version)); await db.commit()
    return dict(row)
