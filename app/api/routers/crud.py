from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.models import metadata

router = APIRouter(prefix="/data", tags=["Generic CRUD"])

# Public REST surface for all business tables in the current schema.
def table_or_404(name: str):
    table = metadata.tables.get(name)
    if table is None:
        raise HTTPException(404, f"Unknown table: {name}")
    return table


def json_value(v: Any):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, (UUID, Decimal)):
        return str(v)
    if isinstance(v, Enum):
        return v.value
    if isinstance(v, dict):
        return {k: json_value(x) for k, x in v.items()}
    if isinstance(v, list):
        return [json_value(x) for x in v]
    return v


def row_json(row):
    return {k: json_value(v) for k, v in dict(row).items()}

@router.get("/{table_name}")
async def list_rows(
    table_name: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    table = table_or_404(table_name)
    stmt = select(table).offset(offset).limit(limit)
    result = await db.execute(stmt)
    rows = [row_json(r) for r in result.mappings().all()]
    return {"items": rows, "limit": limit, "offset": offset}

@router.get("/{table_name}/count")
async def count_rows(table_name: str, db: AsyncSession = Depends(get_db)):
    table = table_or_404(table_name)
    value = await db.scalar(select(func.count()).select_from(table))
    return {"count": value}

@router.get("/{table_name}/{pk}")
async def get_row(table_name: str, pk: str, db: AsyncSession = Depends(get_db)):
    table = table_or_404(table_name)
    columns = list(table.primary_key.columns)
    if len(columns) != 1:
        raise HTTPException(400, "Composite primary keys are not supported by this route")
    result = await db.execute(select(table).where(columns[0] == pk))
    row = result.mappings().first()
    if row is None:
        raise HTTPException(404, "Resource not found")
    return row_json(row)

@router.post("/{table_name}", status_code=201)
async def create_row(table_name: str, payload: dict, db: AsyncSession = Depends(get_db)):
    table = table_or_404(table_name)
    try:
        result = await db.execute(insert(table).values(**payload).returning(*table.c))
        row = result.mappings().first()
        await db.commit()
        return row_json(row)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(400, str(exc))

@router.patch("/{table_name}/{pk}")
async def update_row(table_name: str, pk: str, payload: dict, db: AsyncSession = Depends(get_db)):
    table = table_or_404(table_name)
    columns = list(table.primary_key.columns)
    if len(columns) != 1:
        raise HTTPException(400, "Composite primary keys are not supported by this route")
    try:
        result = await db.execute(
            update(table).where(columns[0] == pk).values(**payload).returning(*table.c)
        )
        row = result.mappings().first()
        if row is None:
            await db.rollback()
            raise HTTPException(404, "Resource not found")
        await db.commit()
        return row_json(row)
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(400, str(exc))

@router.delete("/{table_name}/{pk}", status_code=204)
async def delete_row(table_name: str, pk: str, db: AsyncSession = Depends(get_db)):
    table = table_or_404(table_name)
    columns = list(table.primary_key.columns)
    if len(columns) != 1:
        raise HTTPException(400, "Composite primary keys are not supported by this route")
    result = await db.execute(delete(table).where(columns[0] == pk))
    if result.rowcount == 0:
        await db.rollback()
        raise HTTPException(404, "Resource not found")
    await db.commit()
