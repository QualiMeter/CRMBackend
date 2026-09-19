from __future__ import annotations
from typing import Any
import httpx
from fastapi import HTTPException, status
from app.core.config import settings

class KeycloakService:
    def __init__(self) -> None:
        self.base = settings.keycloak_url.rstrip("/")
        self.realm = settings.keycloak_realm
        self.client_id = settings.keycloak_client_id
        self.client_secret = settings.keycloak_client_secret

    @property
    def issuer(self) -> str:
        return f"{self.base}/realms/{self.realm}"

    @property
    def token_url(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/token"

    @property
    def logout_url(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/logout"

    @property
    def admin_base(self) -> str:
        return f"{self.base}/admin/realms/{self.realm}"

    async def _post_token(self, data: dict[str, str]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(self.token_url, data=data)
        if response.status_code >= 400:
            try:
                body = response.json()
            except Exception:
                body = {}
            error = body.get("error_description") or body.get("error") or "Authentication failed"
            if response.status_code in (400, 401):
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, error)
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Keycloak authentication service unavailable")
        return response.json()

    async def login(self, username: str, password: str) -> dict[str, Any]:
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "username": username,
            "password": password,
            "scope": "openid profile email",
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret
        return await self._post_token(data)

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "refresh_token": refresh_token,
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret
        return await self._post_token(data)

    async def logout(self, refresh_token: str) -> None:
        data = {"client_id": self.client_id, "refresh_token": refresh_token}
        if self.client_secret:
            data["client_secret"] = self.client_secret
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(self.logout_url, data=data)
        if response.status_code not in (200, 204):
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Keycloak logout failed")

    async def _admin_token(self) -> str:
        if not settings.keycloak_admin_client_id or not settings.keycloak_admin_client_secret:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Keycloak admin service credentials are not configured")
        data = {
            "grant_type": "client_credentials",
            "client_id": settings.keycloak_admin_client_id,
            "client_secret": settings.keycloak_admin_client_secret,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(self.token_url, data=data)
        if response.status_code >= 400:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Keycloak admin authentication failed")
        return response.json()["access_token"]

    async def register(self, *, username: str, email: str, password: str, first_name: str, last_name: str) -> str:
        token = await self._admin_token()
        payload = {
            "username": username,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": True,
            "emailVerified": False,
            "credentials": [{"type": "password", "value": password, "temporary": False}],
        }
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(f"{self.admin_base}/users", json=payload, headers=headers)
        if response.status_code == 409:
            raise HTTPException(status.HTTP_409_CONFLICT, "Username or email is already registered")
        if response.status_code not in (201, 204):
            try:
                body = response.json()
                detail = body.get("errorMessage") or body.get("error") or "Registration failed"
            except Exception:
                detail = "Registration failed"
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail)
        location = response.headers.get("Location", "")
        user_id = location.rstrip("/").split("/")[-1] if location else ""
        return user_id

    async def assign_default_role(self, user_id: str, role_name: str) -> None:
        if not role_name:
            return
        token = await self._admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            role_response = await client.get(f"{self.admin_base}/roles/{role_name}", headers=headers)
            if role_response.status_code != 200:
                return
            await client.post(
                f"{self.admin_base}/users/{user_id}/role-mappings/realm",
                json=[role_response.json()],
                headers={**headers, "Content-Type": "application/json"},
            )

keycloak = KeycloakService()
