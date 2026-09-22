import os, pytest

pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_database_ping():
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL is not configured")
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"])
    async with engine.connect() as conn:
        result = await conn.exec_driver_sql("SELECT 1")
        assert result.scalar() == 1
    await engine.dispose()
