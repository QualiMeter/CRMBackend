from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def get_or_404(db: AsyncSession, table, pk_value):
    pk = list(table.primary_key.columns)
    if len(pk) != 1:
        raise HTTPException(500, "This endpoint requires a single-column primary key")
    obj = (await db.execute(select(table).where(pk[0] == pk_value))).mappings().first()
    if obj is None:
        raise HTTPException(404, "Resource not found")
    return dict(obj)
