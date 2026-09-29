from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.models import metadata
from app.api.routers.crud import row_json
from app.api.deps import get_current_user
from app.core.auth import CurrentUser, require_roles

router = APIRouter(prefix="/universities", tags=["Universities"])


def tables():
    return metadata.tables["universities"], metadata.tables["university_contacts"], metadata.tables["programs"]


async def allowed_ids(db: AsyncSession, current: CurrentUser):
    if "admin" in current.roles:
        return None
    ua, users = metadata.tables["user_university_access"], metadata.tables["users"]
    if "leader" in current.roles:
        team = select(users.c.id).where(users.c.supervisor_id == current.id)
        rows = await db.execute(select(ua.c.university_id).where(or_(ua.c.user_id == current.id, ua.c.user_id.in_(team))))
    else:
        rows = await db.execute(select(ua.c.university_id).where(ua.c.user_id == current.id))
    return {int(x[0]) for x in rows.all()}


async def assert_access(db, current, university_id):
    ids = await allowed_ids(db, current)
    if ids is not None and university_id not in ids:
        raise HTTPException(403, "University is outside your access scope")


@router.get("")
async def list_universities(current: CurrentUser = Depends(get_current_user), q: str | None = None, status: str | None = None, limit: int = Query(50, ge=1, le=200), offset: int = 0, db: AsyncSession = Depends(get_db)):
    u, _, _ = tables()
    stmt = select(u).where(u.c.archived_at.is_(None)).order_by(u.c.id.desc()).offset(offset).limit(limit)
    ids = await allowed_ids(db, current)
    if ids is not None:
        if not ids:
            return []
        stmt = stmt.where(u.c.id.in_(ids))
    if q:
        stmt = stmt.where(or_(u.c.name.ilike(f"%{q}%"), u.c.short_name.ilike(f"%{q}%"), u.c.city.ilike(f"%{q}%")))
    if status:
        stmt = stmt.where(u.c.status == status)
    return [row_json(x) for x in (await db.execute(stmt)).mappings().all()]


@router.get("/{university_id}")
async def get_university(university_id: int, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await assert_access(db, current, university_id)
    u, _, _ = tables()
    row = (await db.execute(select(u).where(u.c.id == university_id))).mappings().first()
    if not row:
        raise HTTPException(404, "University not found")
    return row_json(row)


@router.get("/{university_id}/contacts")
async def contacts(university_id: int, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await assert_access(db, current, university_id)
    u, c, _ = tables()
    if not await db.scalar(select(func.count()).select_from(u).where(u.c.id == university_id)):
        raise HTTPException(404, "University not found")
    return [row_json(x) for x in (await db.execute(select(c).where(c.c.university_id == university_id).order_by(c.c.id))).mappings().all()]


@router.get("/{university_id}/programs")
async def programs(university_id: int, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await assert_access(db, current, university_id)
    u, _, p = tables()
    if not await db.scalar(select(func.count()).select_from(u).where(u.c.id == university_id)):
        raise HTTPException(404, "University not found")
    return [row_json(x) for x in (await db.execute(select(p).where(p.c.university_id == university_id, p.c.archived_at.is_(None)).order_by(p.c.id.desc()))).mappings().all()]
