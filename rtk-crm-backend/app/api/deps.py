from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.models import metadata

async def get_or_404(db: AsyncSession, table, pk_value):
    pk = list(table.primary_key.columns)
    if len(pk) != 1:
        raise HTTPException(500, "This endpoint requires a single-column primary key")
    column = pk[0]
    try:
        typed = column.type.python_type(pk_value)
    except Exception:
        typed = pk_value
    obj = (await db.execute(select(table).where(column == typed))).mappings().first()
    if obj is None:
        raise HTTPException(404, "Resource not found")
    return dict(obj)

async def auth_user(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return user
