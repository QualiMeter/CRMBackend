from __future__ import annotations
import csv, io, json
from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import CurrentUser, require_roles
from app.db.session import get_db
from app.models.models import metadata
from app.schemas.requests import ImportCreateRequest
from app.schemas.schemas import ImportJobResponse, ImportRowResponse

router=APIRouter(prefix="/imports",tags=["imports"])
ALLOWED={"universities","university_contacts","it_directions","vendors","it_products","programs","contracts","licenses","tasks","documents"}

def parse_rows(filename:str,data:bytes):
    ext=Path(filename).suffix.lower()
    if ext=='.csv': return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
    if ext in {'.json','.jsonl'}:
        obj=json.loads(data.decode('utf-8')); return obj if isinstance(obj,list) else [obj]
    if ext in {'.xlsx'}:
        from openpyxl import load_workbook
        wb=load_workbook(io.BytesIO(data),read_only=True,data_only=True); ws=wb.active
        rows=list(ws.iter_rows(values_only=True));
        if not rows:return []
        headers=[str(x) if x is not None else '' for x in rows[0]]
        return [dict(zip(headers,r)) for r in rows[1:]]
    raise HTTPException(422,'Supported import formats: CSV, JSON, JSONL, XLSX')

@router.post("/upload",response_model=ImportJobResponse,status_code=201,summary="Upload and validate an import file")
async def upload_import(payload:ImportCreateRequest,file:UploadFile=File(...),user:CurrentUser=Depends(require_roles("admin","manager")),db:AsyncSession=Depends(get_db)):
    if payload.entity_type not in ALLOWED: raise HTTPException(422,f"Unsupported entity_type: {payload.entity_type}")
    data=await file.read()
    rows=parse_rows(file.filename or 'import.csv',data)
    files=metadata.tables['files']; jobs=metadata.tables['import_jobs']; ir=metadata.tables['import_rows']
    # Reuse the normal file storage endpoint logic inline to keep one transaction.
    from app.api.routers.files import upload_file
    # Direct helper is intentionally not called because it expects UploadFile stream; store bytes here.
    import hashlib
    from uuid import uuid4
    fid=uuid4(); key=f"imports/{fid.hex}/{file.filename or 'import'}"; path=Path('storage')/key; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
    frow=(await db.execute(insert(files).values(id=fid,storage_key=key,original_name=file.filename or 'import',content_type=file.content_type or 'application/octet-stream',size_bytes=len(data),checksum_sha256=hashlib.sha256(data).hexdigest(),uploaded_by=user.id).returning(files))).mappings().one()
    job=(await db.execute(insert(jobs).values(source_file_id=fid,entity_type=payload.entity_type,status='validated',column_mapping=payload.column_mapping,total_rows=len(rows),valid_rows=len(rows),invalid_rows=0,created_by=user.id).returning(jobs))).mappings().one()
    jid=job['id']
    for i,row in enumerate(rows,1):
        await db.execute(insert(ir).values(import_job_id=jid,row_number=i,source_data=row,status='valid',normalized_data=row,target_entity_type=payload.entity_type))
    await db.commit(); return dict(job)

@router.get("/{job_id}",response_model=ImportJobResponse)
async def get_import(job_id:UUID,user:CurrentUser=Depends(require_roles("admin","manager")),db:AsyncSession=Depends(get_db)):
    t=metadata.tables['import_jobs']; row=(await db.execute(select(t).where(t.c.id==job_id))).mappings().first()
    if not row: raise HTTPException(404,'Import job not found')
    return dict(row)

@router.get("/{job_id}/rows",response_model=list[ImportRowResponse])
async def get_import_rows(job_id:UUID,user:CurrentUser=Depends(require_roles("admin","manager")),db:AsyncSession=Depends(get_db)):
    t=metadata.tables['import_rows']; rows=(await db.execute(select(t).where(t.c.import_job_id==job_id).order_by(t.c.row_number))).mappings().all()
    return [dict(x) for x in rows]

@router.post("/{job_id}/execute",response_model=ImportJobResponse)
async def execute_import(job_id:UUID,user:CurrentUser=Depends(require_roles("admin","manager")),db:AsyncSession=Depends(get_db)):
    jobs=metadata.tables['import_jobs']; ir=metadata.tables['import_rows']
    job=(await db.execute(select(jobs).where(jobs.c.id==job_id))).mappings().first()
    if not job: raise HTTPException(404,'Import job not found')
    if job['status'] not in ('validated','mapping'): raise HTTPException(409,f"Import job is {job['status']}")
    table_name=job['entity_type']; table=metadata.tables.get(table_name)
    if table is None: raise HTTPException(422,f"Unknown target table: {table_name}")
    rows=(await db.execute(select(ir).where(ir.c.import_job_id==job_id,ir.c.status=='valid').order_by(ir.c.row_number))).mappings().all()
    imported=0; invalid=0
    await db.execute(update(jobs).where(jobs.c.id==job_id).values(status='processing',started_at=__import__('sqlalchemy').func.now()))
    for row in rows:
        values={k:v for k,v in (row['normalized_data'] or row['source_data']).items() if k in table.c and k not in {c.name for c in table.primary_key.columns if c.autoincrement}}
        try:
            result=await db.execute(insert(table).values(**values).returning(table.primary_key.columns.values()[0]))
            target_id=result.scalar_one() if len(table.primary_key.columns)==1 else None
            await db.execute(update(ir).where(ir.c.id==row['id']).values(status='imported',target_entity_id=target_id)); imported+=1
        except Exception as exc:
            invalid+=1
            await db.execute(update(ir).where(ir.c.id==row['id']).values(status='invalid',errors=[str(exc)]))
    await db.execute(update(jobs).where(jobs.c.id==job_id).values(status='completed' if invalid==0 else 'failed',imported_rows=imported,invalid_rows=invalid,completed_at=__import__('sqlalchemy').func.now(),error_message=None if invalid==0 else f'{invalid} rows failed'))
    await db.commit()
    return dict((await db.execute(select(jobs).where(jobs.c.id==job_id))).mappings().one())
