from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "RTK IT School CRM API"
    app_version: str = "3.0.0"
    api_prefix: str = "/api/v1"
    database_url: str
    cors_origins: str = "*"

    # service-account client. A separate admin client is preferred in production.
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
