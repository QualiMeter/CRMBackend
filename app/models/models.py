from sqlalchemy import MetaData

# The database schema is the source of truth. Tables are reflected at runtime,
# so the API cannot silently drift from 001_schema.sql.
metadata = MetaData()

async def reflect_schema(engine):
    from sqlalchemy.ext.asyncio import AsyncConnection
    async with engine.begin() as conn:
        await conn.run_sync(metadata.reflect)
