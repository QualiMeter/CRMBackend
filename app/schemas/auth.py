from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, field_validator


class AuthBase(BaseModel):
    # Accept the API's canonical snake_case names and the common camelCase names
    # used by browser/mobile clients. Unknown fields are still rejected.
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class LoginRequest(AuthBase):
    username: str = Field(
        min_length=1,
        max_length=255,
        validation_alias=AliasChoices("username", "login", "email"),
    )
    password: str = Field(min_length=1, max_length=4096)


class RegisterRequest(AuthBase):
    username: str = Field(
        min_length=3,
        max_length=100,
        pattern=r"^[a-zA-Z0-9._-]+$",
    )
    email: EmailStr
    password: str = Field(min_length=8, max_length=4096)
    first_name: str = Field(
        min_length=1,
        max_length=100,
        validation_alias=AliasChoices("first_name", "firstName"),
    )
    last_name: str = Field(
        min_length=1,
        max_length=100,
        validation_alias=AliasChoices("last_name", "lastName"),
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if value.isspace():
            raise ValueError("Password must contain non-whitespace characters")
        return value


class RefreshRequest(AuthBase):
    refresh_token: str = Field(
        min_length=1,
        validation_alias=AliasChoices("refresh_token", "refreshToken"),
    )


class LogoutRequest(RefreshRequest):
    pass


class TokenResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int
    refresh_expires_in: int | None = None
    scope: str | None = None
    session_state: str | None = None


class AuthUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    full_name: str
    roles: list[str] = Field(default_factory=list)
    claims: dict[str, Any] = Field(default_factory=dict)


class AuthResponse(TokenResponse):
    user: AuthUserResponse


class MessageResponse(BaseModel):
    message: str
