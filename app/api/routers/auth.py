from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    CurrentUser,
    create_access_token,
    get_current_user,
    get_roles,
    hash_password,
    _hash_refresh_token,
    verify_password,
)
from app.core.config import settings
from app.db.session import get_db
from app.models.models import metadata
from app.schemas.auth import (
    AuthResponse,
    AuthUserResponse,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)

router = APIRouter(tags=["auth"])


def _user_response(user: dict, roles: set[str], username: str) -> AuthUserResponse:
    return AuthUserResponse(
        id=int(user["id"]),
        username=username,
        email=str(user["email"]),
        full_name=str(user["full_name"]),
        roles=sorted(roles),
    )


async def _issue_tokens(db: AsyncSession, user: dict, roles: set[str], username: str) -> AuthResponse:
    access_token, expires_in = create_access_token(int(user["id"]), username, roles)
    refresh_token = secrets.token_urlsafe(64)
    sessions = metadata.tables["auth_sessions"]
    now = datetime.now(timezone.utc)
    await db.execute(insert(sessions).values(
        id=uuid.uuid4(),
        user_id=int(user["id"]),
        refresh_token_hash=_hash_refresh_token(refresh_token),
        created_at=now,
        expires_at=now + timedelta(days=settings.refresh_token_days),
    ))
    await db.execute(update(metadata.tables["users"]).where(metadata.tables["users"].c.id == user["id"]).values(last_login_at=now))
    await db.commit()
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=expires_in,
        refresh_expires_in=settings.refresh_token_days * 86400,
        user=_user_response(user, roles, username),
    )


@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED,
             summary="Register a local user and sign in")
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    users = metadata.tables["users"]
    credentials = metadata.tables["auth_credentials"]
    roles = metadata.tables["roles"]
    user_roles = metadata.tables["user_roles"]

    existing = await db.execute(
        select(credentials.c.user_id).where(credentials.c.username == payload.username)
    )
    if existing.first():
        raise HTTPException(409, "Username is already registered", headers={"X-Error-Code": "USERNAME_EXISTS"})
    existing_email = await db.execute(select(users.c.id).where(users.c.email == str(payload.email)))
    if existing_email.first():
        raise HTTPException(409, "Email is already registered", headers={"X-Error-Code": "EMAIL_EXISTS"})

    result = await db.execute(insert(users).values(
        email=str(payload.email),
        full_name=f"{payload.first_name} {payload.last_name}".strip(),
        status="active",
    ).returning(users))
    user = dict(result.mappings().one())
    await db.execute(insert(credentials).values(
        user_id=user["id"], username=payload.username, password_hash=hash_password(payload.password)
    ))
    role_id = await db.execute(select(roles.c.id).where(roles.c.code == settings.default_role))
    rid = role_id.scalar_one_or_none()
    if rid is None:
        await db.rollback()
        raise HTTPException(500, f"Default role '{settings.default_role}' is missing")
    await db.execute(insert(user_roles).values(user_id=user["id"], role_id=rid))
    await db.commit()
    return await _issue_tokens(db, user, {settings.default_role}, payload.username)


@router.post("/auth/login", response_model=AuthResponse, summary="Login with username or email")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    users = metadata.tables["users"]
    credentials = metadata.tables["auth_credentials"]
    query = select(credentials, users).join(users, users.c.id == credentials.c.user_id)
    if payload.username:
        query = query.where(credentials.c.username == payload.username)
    else:
        query = query.where(users.c.email == str(payload.email))
    row = (await db.execute(query)).mappings().first()
    if not row or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(401, "Invalid username/email or password", headers={"X-Error-Code": "AUTHENTICATION_FAILED"})
    user = {k: v for k, v in row.items() if k in users.c}
    if str(user.get("status")) == "blocked":
        raise HTTPException(403, "User is blocked")
    roles = await get_roles(db, int(user["id"]))
    username = str(row["username"])
    return await _issue_tokens(db, user, roles, username)


@router.post("/auth/refresh", response_model=AuthResponse, summary="Rotate a refresh token")
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    sessions = metadata.tables["auth_sessions"]
    credentials = metadata.tables["auth_credentials"]
    users = metadata.tables["users"]
    row = (await db.execute(
        select(sessions, users, credentials)
        .join(users, users.c.id == sessions.c.user_id)
        .join(credentials, credentials.c.user_id == users.c.id)
        .where(sessions.c.refresh_token_hash == _hash_refresh_token(payload.refresh_token))
    )).mappings().first()
    if not row or row["revoked_at"] is not None or row["expires_at"] <= datetime.now(timezone.utc):
        raise HTTPException(401, "Invalid or expired refresh token")
    await db.execute(delete(sessions).where(sessions.c.id == row["id"]))
    user = {k: v for k, v in row.items() if k in users.c}
    roles = await get_roles(db, int(user["id"]))
    return await _issue_tokens(db, user, roles, str(row["username"]))


@router.post("/auth/logout", response_model=MessageResponse, summary="Revoke a refresh token")
async def logout(payload: LogoutRequest, db: AsyncSession = Depends(get_db)):
    sessions = metadata.tables["auth_sessions"]
    await db.execute(delete(sessions).where(sessions.c.refresh_token_hash == _hash_refresh_token(payload.refresh_token)))
    await db.commit()
    return MessageResponse(message="Logged out")


@router.get("/auth/me", response_model=AuthUserResponse, summary="Current authenticated user")
async def me(user: CurrentUser = Depends(get_current_user)):
    return _user_response(user.db_user, user.roles, user.username)


@router.get("/me", response_model=AuthUserResponse, include_in_schema=False)
async def me_alias(user: CurrentUser = Depends(get_current_user)):
    return _user_response(user.db_user, user.roles, user.username)


@router.get("/me/roles", include_in_schema=False)
async def roles_alias(user: CurrentUser = Depends(get_current_user)):
    return sorted(user.roles)
