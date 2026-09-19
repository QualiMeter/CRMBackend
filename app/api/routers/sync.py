from collections import defaultdict, deque
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.models import metadata
from app.schemas.sync import DatabaseSyncRequest, DatabaseSyncResponse

router = APIRouter(prefix="/sync", tags=["Database Sync"])


def _tables_with_pk():
    return {
        name: table
        for name, table in metadata.tables.items()
        if len(table.primary_key.columns) > 0
    }


def _dependency_order(tables: dict[str, Any]) -> list[str]:
    deps = {name: set() for name in tables}
    reverse = defaultdict(set)
    for name, table in tables.items():
        for fk in table.foreign_keys:
            parent = fk.column.table.name
            if parent in tables and parent != name:
                deps[name].add(parent)
                reverse[parent].add(name)
    queue = deque(sorted(name for name, d in deps.items() if not d))
    result = []
    while queue:
        name = queue.popleft()
        result.append(name)
        for child in sorted(reverse[name]):
            deps[child].discard(name)
            if not deps[child]:
                queue.append(child)
    # Keep cyclic/self-referencing tables at the end; PostgreSQL FKs and
    # ON DELETE actions still enforce consistency.
    result.extend(name for name in tables if name not in result)
    return result


def _clean_row(table, row: dict[str, Any]) -> dict[str, Any]:
    known = {c.name for c in table.columns}
    result = {k: v for k, v in row.items() if k in known}
    # PostgreSQL generated columns cannot be written to.
    result = {k: v for k, v in result.items() if not getattr(table.c[k], "computed", None)}
    return result


def _pk_key(table, row: dict[str, Any]):
    cols = list(table.primary_key.columns)
    if len(cols) == 1:
        return row.get(cols[0].name)
    return tuple(row.get(c.name) for c in cols)


def _normalize_deleted(table, value: Any):
    cols = list(table.primary_key.columns)
    if len(cols) == 1:
        return {cols[0].name: value}
    if not isinstance(value, dict):
        raise HTTPException(400, f"Composite key deletion for {table.name} must be an object")
    return {c.name: value.get(c.name) for c in cols}


@router.post("/database", response_model=DatabaseSyncResponse)
async def sync_database(payload: DatabaseSyncRequest, db: AsyncSession = Depends(get_db)):
    """Synchronize a complete frontend snapshot in one transaction.

    `tables` contains the current frontend state. `deleted` contains primary keys
    that were removed on the frontend. `replace=true` additionally deletes rows
    that are absent from the supplied snapshot, so it should only be used when
    the frontend really has a complete database snapshot.
    """
    tables = _tables_with_pk()
    unknown = (set(payload.tables) | set(payload.deleted)) - set(tables)
    if unknown:
        raise HTTPException(400, f"Unknown or non-writable tables: {', '.join(sorted(unknown))}")

    order = _dependency_order(tables)
    stats: dict[str, dict[str, int]] = defaultdict(lambda: {"received": 0, "created": 0, "updated": 0, "deleted": 0})
    snapshot_keys: dict[str, set[Any]] = {}

    try:
        # Parents first so FK references in the snapshot can be inserted safely.
        for name in order:
            table = tables[name]
            rows = payload.tables.get(name, [])
            if not rows:
                snapshot_keys[name] = set()
                continue
            pk_cols = list(table.primary_key.columns)
            if not all(c.name in row for row in rows for c in pk_cols):
                raise HTTPException(400, f"Every row in '{name}' must contain its primary key")

            clean_rows = [_clean_row(table, row) for row in rows]
            snapshot_keys[name] = {_pk_key(table, row) for row in clean_rows}
            stats[name]["received"] += len(clean_rows)

            for row in clean_rows:
                stmt = pg_insert(table).values(**row)
                update_cols = {
                    c.name: getattr(stmt.excluded, c.name)
                    for c in table.columns
                    if c.name not in {pk.name for pk in pk_cols}
                    and not getattr(c, "computed", None)
                }
                if update_cols:
                    stmt = stmt.on_conflict_do_update(
                        index_elements=[c.name for c in pk_cols],
                        set_=update_cols,
                    )
                else:
                    stmt = stmt.on_conflict_do_nothing(
                        index_elements=[c.name for c in pk_cols]
                    )
                result = await db.execute(stmt)
                # PostgreSQL does not expose created/updated distinction for
                # ON CONFLICT without an extra query. Count successful rows as
                # updated/created-neutral; frontend only needs synchronization.
                if result.rowcount:
                    stats[name]["updated"] += 1

        # Explicit deletions are safest and work for composite primary keys.
        for name in reversed(order):
            table = tables[name]
            for value in payload.deleted.get(name, []):
                where = _normalize_deleted(table, value)
                result = await db.execute(delete(table).where(*[table.c[k] == v for k, v in where.items()]))
                stats[name]["deleted"] += result.rowcount or 0

        # Exact snapshot mode: delete rows missing from the snapshot, children first.
        if payload.replace:
            for name in reversed(order):
                table = tables[name]
                if name not in payload.tables:
                    continue
                pk_cols = list(table.primary_key.columns)
                if not pk_cols:
                    continue
                existing = (await db.execute(select(*pk_cols).select_from(table))).all()
                current = snapshot_keys.get(name, set())
                for row in existing:
                    key = row[0] if len(pk_cols) == 1 else tuple(row)
                    if key not in current:
                        conditions = [c == getattr(row, c.name, row[i]) for i, c in enumerate(pk_cols)]
                        await db.execute(delete(table).where(*conditions))
                        stats[name]["deleted"] += 1

        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(400, f"Database synchronization failed: {exc}") from exc

    compact = {name: dict(values) for name, values in stats.items() if any(values.values())}
    return DatabaseSyncResponse(
        success=True,
        tables=compact,
        total_received=sum(x["received"] for x in compact.values()),
        total_created=sum(x["created"] for x in compact.values()),
        total_updated=sum(x["updated"] for x in compact.values()),
        total_deleted=sum(x["deleted"] for x in compact.values()),
    )


@router.get("/database/tables")
async def sync_tables():
    """Return tables accepted by the bulk synchronization endpoint."""
    return {"tables": sorted(_tables_with_pk().keys())}
