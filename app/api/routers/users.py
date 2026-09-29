from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta, timezone
import secrets
import uuid
from sqlalchemy import delete, select, insert, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import require_roles, _hash_refresh_token
from app.core.config import settings
from app.db.session import get_db
from app.models.models import metadata
from app.schemas.requests import UserCreateRequest, UserUpdateRequest, RoleAssignmentRequest
from app.schemas.schemas import UserResponse, RoleResponse
from app.schemas.auth import InvitationResponse, MessageResponse

router = APIRouter(prefix="/users", tags=["users"])


def _user_response(row: dict, roles: list[str] | None = None) -> dict:
    # Never expose internal/legacy database columns through the public user DTO.
    allowed = {
        "id", "email", "full_name", "position", "phone", "status",
        "last_login_at", "supervisor_id", "created_at", "updated_at",
    }
    result = {key: row[key] for key in allowed if key in row}
    result["roles"] = roles or []
    return result

async def _roles(db, user_id):
    r=metadata.tables["roles"]; ur=metadata.tables["user_roles"]
    q=await db.execute(select(r.c.code).join(ur,ur.c.role_id==r.c.id).where(ur.c.user_id==user_id))
    return [x[0] for x in q.all()]

@router.get("", response_model=list[UserResponse], dependencies=[Depends(require_roles("admin", "manager"))])
async def list_users(db: AsyncSession=Depends(get_db)):
    users=metadata.tables["users"]
    rows=(await db.execute(select(users).order_by(users.c.id))).mappings().all()
    return [_user_response(dict(x), await _roles(db, x["id"])) for x in rows]

@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_roles("admin", "manager"))])
async def get_user(user_id:int, db:AsyncSession=Depends(get_db)):
    users=metadata.tables["users"]
    row=(await db.execute(select(users).where(users.c.id==user_id))).mappings().first()
    if not row: raise HTTPException(404,"User not found")
    return _user_response(dict(row), await _roles(db, user_id))

@router.post("", response_model=UserResponse, status_code=201, dependencies=[Depends(require_roles("admin"))])
async def create_user(payload:UserCreateRequest, db:AsyncSession=Depends(get_db)):
    users=metadata.tables["users"]; roles=metadata.tables["roles"]; ur=metadata.tables["user_roles"]
    values=payload.model_dump(exclude={"role_codes"})
    try:
        result=await db.execute(insert(users).values(**values).returning(users))
        row=result.mappings().one(); uid=row["id"]
        for code in payload.role_codes:
            rid=(await db.execute(select(roles.c.id).where(roles.c.code==code))).scalar_one_or_none()
            if rid is None: raise HTTPException(422,f"Unknown role: {code}")
            await db.execute(insert(ur).values(user_id=uid,role_id=rid))
        await db.commit()
        return _user_response(dict(row), await _roles(db, uid))
    except IntegrityError as exc:
        await db.rollback(); raise HTTPException(409,"User violates a unique or foreign-key constraint") from exc

@router.post("/{user_id}/invite", response_model=InvitationResponse, dependencies=[Depends(require_roles("admin"))])
async def invite_user(user_id: int, db: AsyncSession = Depends(get_db)):
    users = metadata.tables["users"]
    invitations = metadata.tables["user_invitations"]
    credentials = metadata.tables["auth_credentials"]
    user = (await db.execute(select(users).where(users.c.id == user_id))).mappings().first()
    if not user:
        raise HTTPException(404, "User not found")
    if str(user["status"]) != "invited":
        raise HTTPException(409, "User must have invited status")
    existing_credentials = await db.execute(select(credentials.c.user_id).where(credentials.c.user_id == user_id))
    if existing_credentials.first():
        raise HTTPException(409, "User already has login credentials")
    now = datetime.now(timezone.utc)
    await db.execute(update(invitations).where(
        (invitations.c.user_id == user_id) &
        invitations.c.accepted_at.is_(None) &
        invitations.c.revoked_at.is_(None)
    ).values(revoked_at=now))
    token = secrets.token_urlsafe(48)
    expires_at = now + timedelta(hours=settings.invitation_expire_hours)
    await db.execute(insert(invitations).values(
        id=uuid.uuid4(),
        user_id=user_id,
        token_hash=_hash_refresh_token(token),
        created_at=now,
        expires_at=expires_at,
    ))
    await db.commit()
    invite_url = f"{settings.frontend_base_url.rstrip('/')}/invite/{token}"
    return InvitationResponse(message="Invitation created", invite_url=invite_url, expires_at=expires_at.isoformat())


@router.post("/{user_id}/invite/revoke", response_model=MessageResponse, dependencies=[Depends(require_roles("admin"))])
async def revoke_invite(user_id: int, db: AsyncSession = Depends(get_db)):
    users = metadata.tables["users"]
    invitations = metadata.tables["user_invitations"]
    user = (await db.execute(select(users.c.id).where(users.c.id == user_id))).first()
    if not user:
        raise HTTPException(404, "User not found")
    result = await db.execute(update(invitations).where(
        (invitations.c.user_id == user_id) &
        invitations.c.accepted_at.is_(None) &
        invitations.c.revoked_at.is_(None)
    ).values(revoked_at=datetime.now(timezone.utc)))
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(404, "Active invitation not found")
    return MessageResponse(message="Invitation revoked")


@router.patch("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_roles("admin"))])
async def update_user(user_id:int,payload:UserUpdateRequest,db:AsyncSession=Depends(get_db)):
    users=metadata.tables["users"]; ur=metadata.tables["user_roles"]; roles=metadata.tables["roles"]
    vals=payload.model_dump(exclude_unset=True, exclude={"role_codes"})
    if vals:
        await db.execute(update(users).where(users.c.id==user_id).values(**vals))
    if payload.role_codes is not None:
        await db.execute(delete(ur).where(ur.c.user_id==user_id))
        for code in payload.role_codes:
            rid=(await db.execute(select(roles.c.id).where(roles.c.code==code))).scalar_one_or_none()
            if rid is None: raise HTTPException(422,f"Unknown role: {code}")
            await db.execute(insert(ur).values(user_id=user_id,role_id=rid))
    await db.commit()
    return await get_user(user_id,db)

@router.delete("/{user_id}", status_code=204, dependencies=[Depends(require_roles("admin"))])
async def delete_user(user_id:int,db:AsyncSession=Depends(get_db)):
    users=metadata.tables["users"]
    result=await db.execute(delete(users).where(users.c.id==user_id))
    if result.rowcount==0: raise HTTPException(404,"User not found")
    await db.commit()

@router.put("/{user_id}/roles", response_model=list[RoleResponse], dependencies=[Depends(require_roles("admin"))])
async def set_roles(user_id:int,payload:RoleAssignmentRequest,db:AsyncSession=Depends(get_db)):
    roles=metadata.tables["roles"]; ur=metadata.tables["user_roles"]
    await db.execute(delete(ur).where(ur.c.user_id==user_id))
    for code in payload.role_codes:
        rid=(await db.execute(select(roles.c.id).where(roles.c.code==code))).scalar_one_or_none()
        if rid is None: raise HTTPException(422,f"Unknown role: {code}")
        await db.execute(insert(ur).values(user_id=user_id,role_id=rid))
    await db.commit()
    result=await db.execute(select(roles).join(ur,ur.c.role_id==roles.c.id).where(ur.c.user_id==user_id))
    return [dict(x) for x in result.mappings().all()]
