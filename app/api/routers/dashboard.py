from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.routers.tz import _user_university_ids
from app.db.session import get_db
from app.core.auth import CurrentUser, require_roles, get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/universities", dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def university_dashboard(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ids = await _user_university_ids(db, current)
    if ids is None:
        rows = (await db.execute(text("SELECT * FROM v_university_dashboard ORDER BY id"))).mappings().all()
    elif not ids:
        return []
    else:
        rows = (await db.execute(text("SELECT * FROM v_university_dashboard WHERE id = ANY(:ids) ORDER BY id"), {"ids": list(ids)})).mappings().all()
    return [dict(r) for r in rows]


@router.get("/interactions/{interaction_id}/progress", dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def interaction_progress(interaction_id: int, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.api.routers.tz import _assert_interaction_access
    await _assert_interaction_access(db, current, interaction_id)
    row = (await db.execute(text("SELECT * FROM v_interaction_progress WHERE interaction_id=:id"), {"id": interaction_id})).mappings().first()
    if not row:
        return {"interaction_id": interaction_id, "stages_total": 0, "stages_done": 0, "progress_percent": 0, "current_stage_position": None}
    return dict(row)
