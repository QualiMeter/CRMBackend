from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
import hashlib, hmac, json, secrets
from sqlalchemy import insert, select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import metadata
from app.core.config import settings

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def random_token(n: int = 48) -> str:
    return secrets.token_urlsafe(n)

async def audit(db: AsyncSession, user_id: int | None, action: str, entity_type: str | None = None,
                entity_id: Any | None = None, old_value: Any = None, new_value: Any = None,
                request_id: str | None = None, ip_address: str | None = None, user_agent: str | None = None):
    t = metadata.tables.get("audit_log")
    if t is None: return
    await db.execute(insert(t).values(user_id=user_id, action=action, entity_type=entity_type,
        entity_id=None if entity_id is None else str(entity_id), old_value=old_value, new_value=new_value,
        request_id=request_id, ip_address=ip_address, user_agent=user_agent))

async def create_notification(db: AsyncSession, user_id: int, type_: str, title: str, message: str, data: dict | None = None):
    t=metadata.tables.get("notifications")
    if t is None: return
    await db.execute(insert(t).values(user_id=user_id,type=type_,title=title,message=message,data=data or {}))

async def fire_webhooks(db: AsyncSession, event: str, payload: dict):
    # Queue delivery; an external worker can process background_jobs later.
    wh=metadata.tables.get("webhooks"); jobs=metadata.tables.get("background_jobs")
    if wh is None or jobs is None: return
    rows=(await db.execute(select(wh).where(wh.c.active.is_(True)))).mappings().all()
    import datetime as dt
    for row in rows:
        events=row.get("events") or []
        if events and event not in events: continue
        await db.execute(insert(jobs).values(id=uuid4(),kind="webhook_delivery",payload={"webhook_id":row["id"],"event":event,"payload":payload}))
