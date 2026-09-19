from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import auth_user
from app.core.auth import CurrentUser
from app.db.session import get_db
from app.models.models import metadata
from app.schemas.schemas import MeResponse, RoleResponse
router=APIRouter(prefix="/me",tags=["me"])
@router.get("",response_model=MeResponse)
async def me(user:CurrentUser=Depends(auth_user),db:AsyncSession=Depends(get_db)):
    roles=metadata.tables['roles']; ur=metadata.tables['user_roles']
    result=await db.execute(select(roles.c.code).join(ur,ur.c.role_id==roles.c.id).where(ur.c.user_id==user.id))
    return {**user.db_user,"roles":[x[0] for x in result.all()],"claims":user.claims}
@router.get("/roles",response_model=list[RoleResponse])
async def my_roles(user:CurrentUser=Depends(auth_user),db:AsyncSession=Depends(get_db)):
    roles=metadata.tables['roles']; ur=metadata.tables['user_roles']
    result=await db.execute(select(roles).join(ur,ur.c.role_id==roles.c.id).where(ur.c.user_id==user.id))
    return [dict(x) for x in result.mappings().all()]
