def test_settings_are_loaded():
    from app.core.config import settings
    assert settings.api_prefix == "/api/v1"
    assert settings.database_url
    assert settings.jwt_algorithm
