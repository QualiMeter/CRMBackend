from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

bearer = HTTPBearer(auto_error=False)
KNOWN_ROLES = {"user", "manager", "leader", "admin", "student", "teacher"}


@dataclass
class CurrentUser:
    db_user: dict[str, Any]
    roles: set[str]
    claims: dict[str, Any]

    @property
    def id(self) -> int:
        return int(self.db_user["id"])

    @property
    def username(self) -> str:
        return str(self.claims.get("username") or self.db_user.get("email"))


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000)
    return f"pbkdf2_sha256$210000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
        )
        return secrets.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, username: str, roles: set[str]) -> tuple[str, int]:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    claims = {
        "sub": str(user_id),
        "username": username,
        "roles": sorted(roles),
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": expires,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm), int(settings.access_token_minutes * 60)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if claims.get("type") != "access" or not claims.get("sub"):
            raise ValueError("invalid token type")
        return claims
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_roles(db: AsyncSession, user_id: int) -> set[str]:
    roles = metadata_tables()["roles"]
    ur = metadata_tables()["user_roles"]
    result = await db.execute(
        select(roles.c.code).join(ur, ur.c.role_id == roles.c.id).where(ur.c.user_id == user_id)
    )
    return {str(row[0]) for row in result.all()}


def metadata_tables():
    from app.models.models import metadata
    return metadata.tables


async def load_user(db: AsyncSession, user_id: int) -> tuple[dict[str, Any], set[str]]:
    users = metadata_tables()["users"]
    result = await db.execute(select(users).where(users.c.id == user_id))
    row = result.mappings().first()
    if not row:
        raise HTTPException(401, "User no longer exists")
    user = dict(row)
    if str(user.get("status")) == "blocked":
        raise HTTPException(403, "User is blocked")
    return user, await get_roles(db, user_id)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    if not settings.auth_required:
        return CurrentUser({"id": 0, "email": "anonymous", "status": "active"}, {"admin"}, {"sub": "0"})
    if credentials is None:
        raise HTTPException(401, "Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    claims = decode_access_token(credentials.credentials)
    try:
        user_id = int(claims["sub"])
    except (TypeError, ValueError) as exc:
        raise HTTPException(401, "Invalid access token") from exc
    user, roles = await load_user(db, user_id)
    return CurrentUser(user, roles, claims)


def require_permission(permission_code: str):
    async def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if "admin" in user.roles:
            return user
        # Permission checks are resolved lazily in request handlers through the DB dependency.
        from fastapi import Request
        raise HTTPException(403, f"Required permission: {permission_code}")
    return dependency

def require_roles(*required: str):
    async def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not user.roles.intersection(required):
            raise HTTPException(403, f"Required role: {' or '.join(required)}")
        return user
    return dependency


async def revoke_refresh_token(db: AsyncSession, token: str) -> None:
    sessions = metadata_tables()["auth_sessions"]
    await db.execute(
        sessions.delete().where(sessions.c.refresh_token_hash == _hash_refresh_token(token))
    )
    await db.commit()
