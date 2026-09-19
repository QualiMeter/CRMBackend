from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RTK IT School CRM API"
    app_version: str = "4.0.0"
    api_prefix: str = "/api/v1"
    database_url: str
    cors_origins: str = "*"

    # Local API authentication. No external identity provider is required.
    jwt_secret: str = "change-this-development-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 30
    default_role: str = "user"
    auth_required: bool = True

    storage_path: str = "./storage"
    max_upload_size: int = 50 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
