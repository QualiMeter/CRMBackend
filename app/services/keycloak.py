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
        self.admin_client_id = (
            settings.keycloak_admin_client_id
            or (settings.keycloak_client_id if settings.keycloak_admin_use_main_client else None)
        )
        self.admin_client_secret = (
            settings.keycloak_admin_client_secret
            or (settings.keycloak_client_secret if settings.keycloak_admin_use_main_client else None)
        )

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

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                return await client.request(method, url, **kwargs)
        except httpx.RequestError as exc:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                "Keycloak is unavailable",
            ) from exc

    @staticmethod
    def _keycloak_error(response: httpx.Response, fallback: str) -> str:
        try:
            body = response.json()
        except Exception:
            body = {}
        if isinstance(body, dict):
            return str(
                body.get("error_description")
                or body.get("errorMessage")
                or body.get("error")
                or fallback
            )
        return fallback

    async def _post_token(self, data: dict[str, str], *, auth_error_message: str) -> dict[str, Any]:
        response = await self._request("POST", self.token_url, data=data)
        if response.status_code >= 400:
            detail = self._keycloak_error(response, auth_error_message)
            if response.status_code in (400, 401):
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail)
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail)
        try:
            return response.json()
        except ValueError as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Keycloak returned an invalid token response") from exc

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
        return await self._post_token(data, auth_error_message="Invalid username or password")

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "refresh_token": refresh_token,
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret
        return await self._post_token(data, auth_error_message="Invalid or expired refresh token")

    async def logout(self, refresh_token: str) -> None:
        data = {"client_id": self.client_id, "refresh_token": refresh_token}
        if self.client_secret:
            data["client_secret"] = self.client_secret
        response = await self._request("POST", self.logout_url, data=data)
        if response.status_code in (200, 204):
            return
        if response.status_code in (400, 401):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Keycloak logout failed")

    async def _admin_token(self) -> str:
        if not self.admin_client_id or not self.admin_client_secret:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Keycloak admin service credentials are not configured. Set KEYCLOAK_ADMIN_CLIENT_ID/KEYCLOAK_ADMIN_CLIENT_SECRET or enable the main confidential client Service Account and set KEYCLOAK_CLIENT_SECRET.",
            )

        data = {
            "grant_type": "client_credentials",
            "client_id": self.admin_client_id,
            "client_secret": self.admin_client_secret,
        }
        response = await self._request("POST", self.token_url, data=data)
        if response.status_code in (400, 401):
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                "Keycloak admin client authentication failed. Check the admin client credentials and Service Account configuration.",
            )
        if response.status_code >= 400:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Keycloak admin authentication failed")
        try:
            token = response.json().get("access_token")
        except ValueError as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Keycloak returned an invalid admin token response") from exc
        if not token:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Keycloak admin token is missing")
        return str(token)

    async def register(
        self,
        *,
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> str:
        token = await self._admin_token()
        payload = {
            "username": username,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": True,
            "emailVerified": False,
            "credentials": [
                {"type": "password", "value": password, "temporary": False}
            ],
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        response = await self._request(
            "POST",
            f"{self.admin_base}/users",
            json=payload,
            headers=headers,
        )
        if response.status_code == 409:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Username or email is already registered",
            )
        if response.status_code not in (201, 204):
            detail = self._keycloak_error(response, "Registration failed")
            if response.status_code in (400, 422):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail)
            if response.status_code in (401, 403):
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    "Keycloak admin client is not allowed to create users. Grant the Service Account the realm-management manage-users permission.",
                )
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail)

        location = response.headers.get("Location", "")
        user_id = location.rstrip("/").split("/")[-1] if location else ""
        if not user_id:
            # Keycloak normally returns Location on 201. If a proxy stripped it,
            # locate the newly created user by username instead of returning a
            # partially successful registration.
            user_id = await self.find_user_id(username, token)
        if not user_id:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Keycloak created the user but did not return its identifier")
        return user_id

    async def find_user_id(self, username: str, token: str | None = None) -> str | None:
        token = token or await self._admin_token()
        response = await self._request(
            "GET",
            f"{self.admin_base}/users",
            params={"username": username, "exact": "true"},
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 200:
            return None
        try:
            users = response.json()
        except ValueError:
            return None
        if isinstance(users, list) and users:
            return str(users[0].get("id")) if users[0].get("id") else None
        return None

    async def delete_user(self, user_id: str) -> None:
        token = await self._admin_token()
        response = await self._request(
            "DELETE",
            f"{self.admin_base}/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code not in (204, 404):
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Unable to roll back the Keycloak user")

    async def assign_default_role(self, user_id: str, role_name: str) -> None:
        if not role_name:
            return
        token = await self._admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        role_response = await self._request(
            "GET",
            f"{self.admin_base}/roles/{role_name}",
            headers=headers,
        )
        if role_response.status_code == 404:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"Keycloak realm role '{role_name}' does not exist",
            )
        if role_response.status_code != 200:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Unable to read the default Keycloak role")
        role = role_response.json()
        response = await self._request(
            "POST",
            f"{self.admin_base}/users/{user_id}/role-mappings/realm",
            json=[role],
            headers={**headers, "Content-Type": "application/json"},
        )
        if response.status_code not in (200, 204):
            if response.status_code in (401, 403):
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    "Keycloak admin client is not allowed to assign realm roles.",
                )
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Unable to assign the default Keycloak role")


keycloak = KeycloakService()
