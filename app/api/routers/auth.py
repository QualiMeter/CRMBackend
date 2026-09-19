from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session

router = APIRouter(prefix="/auth", tags=["Auth"])

# Development-friendly local auth. Passwords are hashed with PBKDF2-HMAC-SHA256.
# JWT-like opaque bearer tokens are stored server-side in memory only; for production,
# replace with a persistent token store or signed JWT implementation.
_sessions: dict[str, dict] = {}


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthUserResponse(BaseModel):
    id: str
    username: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    roles: list[str] = []


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return f"pbkdf2_sha256$210000${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        _, rounds, salt_hex, digest_hex = encoded.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds)
        )
        return secrets.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


async def _user_payload(session: AsyncSession, user_id: str) -> AuthUserResponse:
    result = await session.execute(
        text("""
            SELECT u.id, u.username, u.email, u.first_name, u.last_name,
                   COALESCE(array_agg(r.name) FILTER (WHERE r.name IS NOT NULL), '{}') AS roles
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.id
            LEFT JOIN roles r ON r.id = ur.role_id
            WHERE u.id = CAST(:id AS uuid)
            GROUP BY u.id
        """),
        {"id": user_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(404, "User not found")
    return AuthUserResponse(
        id=str(row["id"]),
        username=row["username"],
        email=row["email"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        roles=list(row["roles"] or []),
    )


def _tokens(user_id: str) -> TokenResponse:
    access = secrets.token_urlsafe(48)
    refresh = secrets.token_urlsafe(64)
    now = datetime.now(timezone.utc)
    _sessions[access] = {"user_id": user_id, "expires": now + timedelta(minutes=30), "refresh": refresh}
    _sessions[refresh] = {"user_id": user_id, "expires": now + timedelta(days=30), "access": access}
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=1800)


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)):
    exists = await session.execute(
        text("SELECT id FROM users WHERE username = :username OR email = :email LIMIT 1"),
        {"username": body.username, "email": body.email},
    )
    if exists.first():
        raise HTTPException(409, "A user with this username or email already exists", headers={"X-Error-Code": "USER_ALREADY_EXISTS"})

    user_id = str(uuid.uuid4())
    await session.execute(
        text("""
            INSERT INTO users (id, username, email, password_hash, first_name, last_name, is_active)
            VALUES (CAST(:id AS uuid), :username, :email, :password_hash, :first_name, :last_name, true)
        """),
        {
            "id": user_id, "username": body.username, "email": body.email,
            "password_hash": _hash_password(body.password),
            "first_name": body.first_name, "last_name": body.last_name,
        },
    )
    role = await session.execute(text("SELECT id FROM roles WHERE name = 'user' LIMIT 1"))
    role_row = role.first()
    if role_row:
        await session.execute(
            text("INSERT INTO user_roles (user_id, role_id) VALUES (CAST(:uid AS uuid), :rid) ON CONFLICT DO NOTHING"),
            {"uid": user_id, "rid": role_row[0]},
        )
    await session.commit()
    return _tokens(user_id)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    if not body.username and not body.email:
        raise HTTPException(422, "Either username or email is required", headers={"X-Error-Code": "VALIDATION_ERROR"})
    result = await session.execute(
        text("""
            SELECT id, password_hash, is_active
            FROM users
            WHERE (:username IS NOT NULL AND username = :username)
               OR (:email IS NOT NULL AND email = :email)
            LIMIT 1
        """),
        {"username": body.username, "email": body.email},
    )
    row = result.mappings().first()
    if not row or not row["is_active"] or not _verify_password(body.password, row["password_hash"]):
        raise HTTPException(401, "Invalid username/email or password", headers={"X-Error-Code": "AUTHENTICATION_FAILED"})
    return _tokens(str(row["id"]))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    data = _sessions.get(body.refresh_token)
    if not data or data.get("expires", datetime.min.replace(tzinfo=timezone.utc)) <= datetime.now(timezone.utc):
        raise HTTPException(401, "Invalid or expired refresh token")
    old_access = data.get("access")
    if old_access:
        _sessions.pop(old_access, None)
    _sessions.pop(body.refresh_token, None)
    return _tokens(data["user_id"])


@router.post("/logout", status_code=204)
async def logout(body: LogoutRequest):
    if body.refresh_token:
        data = _sessions.pop(body.refresh_token, None)
        if data and data.get("access"):
            _sessions.pop(data["access"], None)
    return None


from fastapi import Header

async def _current_user_from_header(
    authorization: str | None = Header(default=None),
) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Authentication required")
    token = authorization[7:].strip()
    data = _sessions.get(token)
    if not data or data.get("expires", datetime.min.replace(tzinfo=timezone.utc)) <= datetime.now(timezone.utc):
        raise HTTPException(401, "Invalid or expired access token")
    return data["user_id"]


@router.get("/me", response_model=AuthUserResponse)
async def me(
    current_user: str = Depends(_current_user_from_header),
    session: AsyncSession = Depends(get_session),
):
    return await _user_payload(session, current_user)
