from typing import Any
from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, field_validator


class AuthBase(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, str_strip_whitespace=True)


class LoginRequest(AuthBase):
    username: str | None = Field(default=None, min_length=1, max_length=100, validation_alias=AliasChoices("username", "login"))
    email: EmailStr | None = None
    password: str = Field(min_length=1, max_length=4096)

    @field_validator("password")
    @classmethod
    def nonblank_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password must contain non-whitespace characters")
        return value


class RegisterRequest(AuthBase):
    username: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9._-]+$")
    email: EmailStr
    password: str = Field(max_length=4096)
    first_name: str = Field(min_length=1, max_length=100, validation_alias=AliasChoices("first_name", "firstName"))
    last_name: str = Field(min_length=1, max_length=100, validation_alias=AliasChoices("last_name", "lastName"))

    @field_validator("password")
    @classmethod
    def nonblank_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password must contain non-whitespace characters")
        return value


class RefreshRequest(AuthBase):
    refresh_token: str = Field(min_length=20, validation_alias=AliasChoices("refresh_token", "refreshToken"))


class LogoutRequest(RefreshRequest):
    pass


class TokenResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int
    refresh_expires_in: int | None = None


class AuthUserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str
    roles: list[str] = Field(default_factory=list)


class AuthResponse(TokenResponse):
    user: AuthUserResponse


class MessageResponse(BaseModel):
    message: str


class InvitationInfoResponse(BaseModel):
    valid: bool
    email: EmailStr | None = None
    full_name: str | None = None
    expires_at: str | None = None


class AcceptInvitationRequest(AuthBase):
    token: str = Field(min_length=20, max_length=4096)
    username: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9._-]+$")
    password: str = Field(min_length=8, max_length=4096)

    @field_validator("password")
    @classmethod
    def accept_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password must contain non-whitespace characters")
        return value


class InvitationResponse(BaseModel):
    message: str
    invite_url: str
    expires_at: str
