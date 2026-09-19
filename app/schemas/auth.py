from typing import Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class AuthBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

class LoginRequest(AuthBase):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=4096)

class RegisterRequest(AuthBase):
    username: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9._-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=4096)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)

class RefreshRequest(AuthBase):
    refresh_token: str = Field(min_length=1)

class LogoutRequest(AuthBase):
    refresh_token: str = Field(min_length=1)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_expires_in: int | None = None
    scope: str | None = None
    session_state: str | None = None

class AuthUserResponse(BaseModel):
    id: int
    keycloak_subject: str | None = None
    username: str
    email: EmailStr
    full_name: str
    roles: list[str] = []
    claims: dict[str, Any] = {}

class AuthResponse(TokenResponse):
    user: AuthUserResponse

class MessageResponse(BaseModel):
    message: str
