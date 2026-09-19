from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import CurrentUser, require_roles
from app.db.session import get_db
from app.models.models import metadata
from app.schemas.requests import CommentCreateRequest, CommentUpdateRequest
from app.schemas.schemas import StageCommentResponse
router=APIRouter(prefix="/comments",tags=["comments"])

@router.get("/stage/{stage_instance_id}",response_model=list[StageCommentResponse])
async def list_comments(stage_instance_id:int,user:CurrentUser=Depends(require_roles("admin","manager","user")),db:AsyncSession=Depends(get_db)):
    t=metadata.tables["stage_comments"]
    rows=(await db.execute(select(t).where(t.c.stage_instance_id==stage_instance_id,t.c.deleted_at.is_(None)).order_by(t.c.created_at))).mappings().all()
    return [dict(x) for x in rows]

@router.post("/stage/{stage_instance_id}",response_model=StageCommentResponse,status_code=201)
async def create_comment(stage_instance_id:int,payload:CommentCreateRequest,user:CurrentUser=Depends(require_roles("admin","manager","user")),db:AsyncSession=Depends(get_db)):
    t=metadata.tables["stage_comments"]
    row=(await db.execute(insert(t).values(stage_instance_id=stage_instance_id,author_id=user.id,body=payload.body).returning(t))).mappings().one()
    await db.commit(); return dict(row)

@router.patch("/{comment_id}",response_model=StageCommentResponse)
async def update_comment(comment_id:int,payload:CommentUpdateRequest,user:CurrentUser=Depends(require_roles("admin","manager","user")),db:AsyncSession=Depends(get_db)):
    t=metadata.tables["stage_comments"]
    row=(await db.execute(select(t).where(t.c.id==comment_id))).mappings().first()
    if not row: raise HTTPException(404,"Comment not found")
    if row["author_id"]!=user.id and "admin" not in user.roles: raise HTTPException(403,"Only the author or admin can edit this comment")
    await db.execute(update(t).where(t.c.id==comment_id).values(body=payload.body)); await db.commit()
    return dict((await db.execute(select(t).where(t.c.id==comment_id))).mappings().one())

@router.delete("/{comment_id}",status_code=204)
async def delete_comment(comment_id:int,user:CurrentUser=Depends(require_roles("admin","manager","user")),db:AsyncSession=Depends(get_db)):
    t=metadata.tables["stage_comments"]
    row=(await db.execute(select(t).where(t.c.id==comment_id))).mappings().first()
    if not row: raise HTTPException(404,"Comment not found")
    if row["author_id"]!=user.id and "admin" not in user.roles: raise HTTPException(403,"Only the author or admin can delete this comment")
    await db.execute(update(t).where(t.c.id==comment_id).values(deleted_at=__import__('sqlalchemy').func.now())); await db.commit()
