from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "RTK IT School CRM API"
    app_version: str = "3.0.0"
    api_prefix: str = "/api/v1"
    database_url: str
    cors_origins: str = "*"

    # Keycloak / JWT
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "rtk"
    keycloak_client_id: str = "rtk-crm"
    keycloak_audience: str | None = None
    keycloak_client_secret: str | None = None
    keycloak_admin_client_id: str | None = None
    keycloak_admin_client_secret: str | None = None
    keycloak_default_role: str = "user"
    keycloak_verify_audience: bool = False
    keycloak_role_claim: str = "realm_access"
    keycloak_roles_claim: str = "roles"
    auth_required: bool = True
    auth_auto_provision: bool = True

    # Local file storage
    storage_path: str = "./storage"
    max_upload_size: int = 50 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
