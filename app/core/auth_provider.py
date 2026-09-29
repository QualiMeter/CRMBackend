from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.core.config import settings


class AuthProvider(ABC):
    """Replaceable authentication boundary. The demo continues to use local JWT."""

    name: str

    @abstractmethod
    async def authenticate(self, token: str) -> dict[str, Any]:
        raise NotImplementedError


class LocalJwtProvider(AuthProvider):
    name = "local"

    async def authenticate(self, token: str) -> dict[str, Any]:
        from app.core.auth import decode_access_token
        return decode_access_token(token)


class KeycloakProvider(AuthProvider):
    name = "keycloak"

    async def authenticate(self, token: str) -> dict[str, Any]:
        raise NotImplementedError(
            "KeycloakProvider is an architecture adapter for the future OIDC deployment; "
            "the demo must use AUTH_PROVIDER=local until a corporate Keycloak contract is supplied."
        )


def get_auth_provider() -> AuthProvider:
    if settings.auth_provider == "local":
        return LocalJwtProvider()
    if settings.auth_provider == "keycloak":
        return KeycloakProvider()
    raise ValueError(f"Unsupported AUTH_PROVIDER: {settings.auth_provider}")
