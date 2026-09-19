from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine

metadata = MetaData()

async def reflect_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(metadata.reflect)
