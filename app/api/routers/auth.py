from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import auth_user
from app.core.auth import CurrentUser, _decode, _extract_roles, _load_or_provision
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
from app.services.keycloak import keycloak

router = APIRouter(tags=["auth"])


def _token_response(tokens: dict) -> TokenResponse:
    return TokenResponse(
        access_token=str(tokens["access_token"]),
        refresh_token=tokens.get("refresh_token"),
        token_type=str(tokens.get("token_type", "Bearer")),
        expires_in=int(tokens.get("expires_in", 0)),
        refresh_expires_in=(
            int(tokens["refresh_expires_in"])
            if tokens.get("refresh_expires_in") is not None
            else None
        ),
        scope=tokens.get("scope"),
        session_state=tokens.get("session_state"),
    )


def _user_response(user: dict, claims: dict, roles: set[str]) -> AuthUserResponse:
    return AuthUserResponse(
        id=int(user["id"]),
        keycloak_subject=(
            str(user["keycloak_subject"])
            if user.get("keycloak_subject")
            else None
        ),
        username=str(claims.get("preferred_username") or claims.get("email")),
        email=str(user["email"]),
        full_name=str(user["full_name"]),
        roles=sorted(roles),
        claims=claims,
    )


async def _auth_response(tokens: dict, db: AsyncSession) -> AuthResponse:
    claims = _decode(str(tokens["access_token"]))
    jwt_roles = _extract_roles(claims)
    user, db_roles = await _load_or_provision(db, claims, jwt_roles)
    return AuthResponse(
        **_token_response(tokens).model_dump(),
        user=_user_response(user, claims, db_roles or jwt_roles),
    )


@router.post(
    "/auth/login",
    response_model=AuthResponse,
    summary="Login with Keycloak username/email and password",
    responses={401: {"description": "Invalid username or password"}},
)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    tokens = await keycloak.login(payload.username, payload.password)
    return await _auth_response(tokens, db)


@router.post(
    "/auth/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Keycloak user and sign in",
    responses={
        409: {"description": "Username or email already exists"},
        500: {"description": "Keycloak admin credentials are not configured"},
    },
)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user_id = await keycloak.register(
        username=payload.username,
        email=str(payload.email),
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    try:
        await keycloak.assign_default_role(user_id, settings.keycloak_default_role)
        tokens = await keycloak.login(payload.username, payload.password)
        return await _auth_response(tokens, db)
    except Exception:
        # Avoid leaving a Keycloak account behind if role assignment/login fails.
        try:
            await keycloak.delete_user(user_id)
        except Exception:
            pass
        raise


@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh(payload: RefreshRequest):
    return _token_response(await keycloak.refresh(payload.refresh_token))


@router.post(
    "/auth/logout",
    response_model=MessageResponse,
    summary="Logout and invalidate the Keycloak refresh token",
)
async def logout(payload: LogoutRequest):
    await keycloak.logout(payload.refresh_token)
    return MessageResponse(message="Logged out")


@router.get(
    "/auth/me",
    response_model=AuthUserResponse,
    summary="Current authenticated user",
)
async def auth_me(
    user: CurrentUser = Depends(auth_user),
) -> AuthUserResponse:
    return _user_response(user.db_user, user.claims, user.roles)


@router.get("/me", response_model=AuthUserResponse, include_in_schema=False)
async def me_alias(user: CurrentUser = Depends(auth_user)) -> AuthUserResponse:
    return _user_response(user.db_user, user.claims, user.roles)


@router.get("/me/roles", include_in_schema=False)
async def roles_alias(
    user: CurrentUser = Depends(auth_user),
    db: AsyncSession = Depends(get_db),
):
    roles = metadata.tables["roles"]
    ur = metadata.tables["user_roles"]
    result = await db.execute(
        select(roles)
        .join(ur, ur.c.role_id == roles.c.id)
        .where(ur.c.user_id == user.id)
    )
    return [dict(x) for x in result.mappings().all()]
