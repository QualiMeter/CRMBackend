from __future__ import annotations
import hashlib
from pathlib import Path
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse as FastAPIFileResponse
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import CurrentUser, require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models.models import metadata
from app.schemas.schemas import FileResponse

router=APIRouter(prefix="/files",tags=["files"])

@router.post("/upload",response_model=FileResponse,status_code=201,summary="Upload a file with multipart/form-data")
async def upload_file(file:UploadFile=File(...), user:CurrentUser=Depends(require_roles("admin","manager","user")), db:AsyncSession=Depends(get_db)):
    settings.storage_path and Path(settings.storage_path).mkdir(parents=True,exist_ok=True)
    file_id=uuid4(); key=f"{file_id.hex}/{file.filename or 'file'}"; path=Path(settings.storage_path)/key
    path.parent.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(); size=0
    try:
        with path.open("wb") as out:
            while chunk:=await file.read(1024*1024):
                size += len(chunk)
                if size>settings.max_upload_size:
                    raise HTTPException(413,f"File exceeds {settings.max_upload_size} bytes")
                digest.update(chunk); out.write(chunk)
        table=metadata.tables["files"]
        row=(await db.execute(insert(table).values(id=file_id,storage_key=key,original_name=file.filename or "file",content_type=file.content_type or "application/octet-stream",size_bytes=size,checksum_sha256=digest.hexdigest(),uploaded_by=user.id).returning(table))).mappings().one()
        await db.commit(); return dict(row)
    except HTTPException:
        if path.exists(): path.unlink()
        await db.rollback(); raise
    except IntegrityError as exc:
        if path.exists(): path.unlink()
        await db.rollback(); raise HTTPException(409,"File metadata conflict") from exc

@router.get("/{file_id}",response_model=FileResponse,summary="Get file metadata")
async def get_file(file_id:UUID, user:CurrentUser=Depends(require_roles("admin","manager","user")), db:AsyncSession=Depends(get_db)):
    table=metadata.tables["files"]
    row=(await db.execute(select(table).where(table.c.id==file_id))).mappings().first()
    if not row: raise HTTPException(404,"File not found")
    return dict(row)

@router.get("/{file_id}/download",summary="Download a stored file")
async def download_file(file_id:UUID,user:CurrentUser=Depends(require_roles("admin","manager","user")),db:AsyncSession=Depends(get_db)):
    table=metadata.tables["files"]
    row=(await db.execute(select(table).where(table.c.id==file_id))).mappings().first()
    if not row: raise HTTPException(404,"File not found")
    path=Path(settings.storage_path)/row["storage_key"]
    if not path.is_file(): raise HTTPException(404,"Stored file not found")
    return FastAPIFileResponse(path,media_type=row["content_type"],filename=row["original_name"])
