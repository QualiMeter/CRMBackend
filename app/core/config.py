from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RTK IT School CRM API"
    app_version: str = "4.0.0"
    api_prefix: str = "/api/v1"
    database_url: str
    cors_origins: str = "*"

    # Authentication provider abstraction. local is the current demo provider; keycloak is reserved for OIDC deployment.
    auth_provider: str = "local"
    keycloak_url: str = ""
    keycloak_realm: str = ""
    keycloak_client_id: str = ""
    jwt_secret: str = "change-this-development-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 30
    default_role: str = "user"
    auth_required: bool = True
    invitation_expire_hours: int = 48
    frontend_base_url: str = "http://localhost:3000"
    password_reset_expire_hours: int = 2
    email_verification_expire_hours: int = 24
    debug_return_auth_tokens: bool = False
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_starttls: bool = True
    log_level: str = "INFO"
    log_dir: str = "./storage/logs"
    test_ui_enabled: bool = False
    test_ui_require_admin: bool = True

    storage_path: str = "./storage"
    max_upload_size: int = 50 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
