from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select, update, delete, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import CurrentUser, get_current_user, require_roles, hash_password
from app.core.config import settings
from app.db.session import get_db
from app.models.models import metadata
from app.services.platform import audit, create_notification
from pydantic import BaseModel, Field, HttpUrl

router=APIRouter(tags=["platform"])

class PasswordChange(BaseModel):
    current_password:str=Field(min_length=1,max_length=4096)
    new_password:str=Field(min_length=8,max_length=4096)
class PasswordResetRequest(BaseModel): email:str
class PasswordResetConfirm(BaseModel): token:str; new_password:str=Field(min_length=8,max_length=4096)
class EmailVerifyRequest(BaseModel): token:str
class NotificationCreate(BaseModel): user_id:int; type:str; title:str; message:str; data:dict={}
class PreferenceUpdate(BaseModel): email_enabled:bool=True; in_app_enabled:bool=True; workflow_enabled:bool=True; task_enabled:bool=True; document_enabled:bool=True
class WebhookCreate(BaseModel): name:str; url:HttpUrl; secret:str|None=None; events:list[str]=[]; active:bool=True

@router.post("/auth/verify-email")
async def verify_email(payload:EmailVerifyRequest,db:AsyncSession=Depends(get_db)):
    r=metadata.tables["auth_email_verifications"]; users=metadata.tables["users"]
    h=__import__('hashlib').sha256(payload.token.encode()).hexdigest()
    row=(await db.execute(select(r).where(r.c.token_hash==h))).mappings().first(); now=datetime.now(timezone.utc)
    if not row or row["verified_at"] or row["revoked_at"] or row["expires_at"]<=now: raise HTTPException(400,"Invalid or expired verification token")
    await db.execute(update(users).where(users.c.id==row["user_id"]).values(email_verified_at=now))
    await db.execute(update(r).where(r.c.id==row["id"]).values(verified_at=now)); await audit(db,row["user_id"],"auth.email_verified","user",row["user_id"]); await db.commit()
    return {"message":"Email verified successfully"}

@router.post("/auth/resend-verification")
async def resend_verification(user:CurrentUser=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    users=metadata.tables["users"]; r=metadata.tables["auth_email_verifications"]; row=(await db.execute(select(users.c.email,users.c.email_verified_at).where(users.c.id==user.id))).mappings().one()
    if row["email_verified_at"] is not None: return {"message":"Email is already verified"}
    import secrets, uuid
    now=datetime.now(timezone.utc); token=secrets.token_urlsafe(48)
    await db.execute(update(r).where((r.c.user_id==user.id)&r.c.verified_at.is_(None)&r.c.revoked_at.is_(None)).values(revoked_at=now))
    await db.execute(__import__('sqlalchemy').insert(r).values(id=uuid.uuid4(),user_id=user.id,token_hash=__import__('hashlib').sha256(token.encode()).hexdigest(),expires_at=now+timedelta(hours=settings.email_verification_expire_hours)))
    from app.services.email import send_email
    url=f"{settings.frontend_base_url.rstrip('/')}/verify-email/{token}"; sent=await send_email(str(row["email"]),"Verify your RTK CRM email",f"Open this link to verify your email: {url}")
    await db.commit(); result={"message":"Verification instructions created","email_sent":sent}
    if settings.debug_return_auth_tokens: result["verification_url"]=url
    return result

@router.post("/auth/change-password")
async def change_password(payload:PasswordChange,user:CurrentUser=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    from app.core.auth import verify_password
    c=metadata.tables["auth_credentials"]
    row=(await db.execute(select(c).where(c.c.user_id==user.id))).mappings().first()
    if not row or not verify_password(payload.current_password,row["password_hash"]): raise HTTPException(400,"Current password is incorrect")
    await db.execute(update(c).where(c.c.user_id==user.id).values(password_hash=hash_password(payload.new_password)))
    await db.execute(delete(metadata.tables["auth_sessions"]).where(metadata.tables["auth_sessions"].c.user_id==user.id))
    await audit(db,user.id,"auth.password_changed","user",user.id)
    await db.commit(); return {"message":"Password changed; all refresh sessions were revoked"}

@router.post("/auth/request-password-reset")
async def request_password_reset(payload:PasswordResetRequest,request:Request,db:AsyncSession=Depends(get_db)):
    users=metadata.tables["users"]; c=metadata.tables["auth_credentials"]; r=metadata.tables["auth_password_resets"]
    row=(await db.execute(select(users.c.id).join(c,c.c.user_id==users.c.id).where(users.c.email==payload.email))).first()
    # Always return the same response to prevent account enumeration.
    if row:
        now=datetime.now(timezone.utc); token=__import__('secrets').token_urlsafe(48)
        await db.execute(update(r).where((r.c.user_id==row[0])&r.c.used_at.is_(None)&r.c.revoked_at.is_(None)).values(revoked_at=now))
        await db.execute(__import__('sqlalchemy').insert(r).values(id=__import__('uuid').uuid4(),user_id=row[0],token_hash=__import__('hashlib').sha256(token.encode()).hexdigest(),expires_at=now+timedelta(hours=settings.password_reset_expire_hours)))
        await audit(db,row[0],"auth.password_reset_requested","user",row[0])
        # In development/testing the URL is available when explicitly enabled.
        if settings.debug_return_auth_tokens: result={"message":"If the account exists, reset instructions were created","reset_url":f"{settings.frontend_base_url.rstrip('/')}/reset-password/{token}"}
        else: result={"message":"If the account exists, reset instructions were created"}
        await db.commit(); return result
    return {"message":"If the account exists, reset instructions were created"}

@router.post("/auth/reset-password")
async def reset_password(payload:PasswordResetConfirm,db:AsyncSession=Depends(get_db)):
    r=metadata.tables["auth_password_resets"]; c=metadata.tables["auth_credentials"]; s=metadata.tables["auth_sessions"]
    h=__import__('hashlib').sha256(payload.token.encode()).hexdigest(); row=(await db.execute(select(r).where(r.c.token_hash==h))).mappings().first()
    now=datetime.now(timezone.utc)
    if not row or row["used_at"] or row["revoked_at"] or row["expires_at"]<=now: raise HTTPException(400,"Invalid or expired reset token")
    await db.execute(update(c).where(c.c.user_id==row["user_id"]).values(password_hash=hash_password(payload.new_password)))
    await db.execute(update(r).where(r.c.id==row["id"]).values(used_at=now)); await db.execute(delete(s).where(s.c.user_id==row["user_id"]))
    await audit(db,row["user_id"],"auth.password_reset_completed","user",row["user_id"]); await db.commit()
    return {"message":"Password reset successfully"}

@router.get("/auth/sessions")
async def sessions(user:CurrentUser=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    t=metadata.tables["auth_sessions"]; rows=(await db.execute(select(t.c.id,t.c.created_at,t.c.expires_at,t.c.revoked_at).where(t.c.user_id==user.id).order_by(t.c.created_at.desc()))).mappings().all(); return [dict(x) for x in rows]

@router.delete("/auth/sessions/{session_id}")
async def revoke_session(session_id:str,user:CurrentUser=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    t=metadata.tables["auth_sessions"]; r=await db.execute(delete(t).where(t.c.id==session_id,t.c.user_id==user.id));
    if not r.rowcount: raise HTTPException(404,"Session not found")
    await audit(db,user.id,"auth.session_revoked","auth_session",session_id); await db.commit(); return {"message":"Session revoked"}

@router.get("/notifications")
async def notifications(user:CurrentUser=Depends(get_current_user),unread_only:bool=False,limit:int=Query(50,ge=1,le=200),db:AsyncSession=Depends(get_db)):
    t=metadata.tables["notifications"]; q=select(t).where(t.c.user_id==user.id).order_by(t.c.created_at.desc()).limit(limit)
    if unread_only:q=q.where(t.c.read_at.is_(None))
    return [dict(x) for x in (await db.execute(q)).mappings().all()]

@router.get("/notifications/unread-count")
async def unread_count(user:CurrentUser=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    t=metadata.tables["notifications"]; n=(await db.execute(select(func.count()).select_from(t).where(t.c.user_id==user.id,t.c.read_at.is_(None)))).scalar_one(); return {"count":n}

@router.post("/notifications/{notification_id}/read")
async def mark_read(notification_id:int,user:CurrentUser=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    t=metadata.tables["notifications"]; r=await db.execute(update(t).where(t.c.id==notification_id,t.c.user_id==user.id).values(read_at=datetime.now(timezone.utc)))
    if not r.rowcount: raise HTTPException(404,"Notification not found")
    await db.commit(); return {"message":"Marked as read"}

@router.post("/notifications/read-all")
async def read_all(user:CurrentUser=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    t=metadata.tables["notifications"]; await db.execute(update(t).where(t.c.user_id==user.id,t.c.read_at.is_(None)).values(read_at=datetime.now(timezone.utc))); await db.commit(); return {"message":"All notifications marked as read"}

@router.get("/notifications/preferences")
async def get_preferences(user:CurrentUser=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    t=metadata.tables["notification_preferences"]; row=(await db.execute(select(t).where(t.c.user_id==user.id))).mappings().first()
    if not row:
        await db.execute(__import__('sqlalchemy').insert(t).values(user_id=user.id)); await db.commit(); row=(await db.execute(select(t).where(t.c.user_id==user.id))).mappings().one()
    return dict(row)

@router.put("/notifications/preferences")
async def update_preferences(payload:PreferenceUpdate,user:CurrentUser=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    t=metadata.tables["notification_preferences"]; values=payload.model_dump()
    exists=(await db.execute(select(t.c.user_id).where(t.c.user_id==user.id))).first()
    if exists:
        await db.execute(update(t).where(t.c.user_id==user.id).values(**values))
    else:
        await db.execute(__import__('sqlalchemy').insert(t).values(user_id=user.id,**values))
    await db.commit(); return await get_preferences(user,db)

@router.get("/search")
async def search(q:str=Query(min_length=2),limit:int=Query(20,ge=1,le=100),user:CurrentUser=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    term=f"%{q}%"; out=[]
    tables=[("users","full_name","email"),("universities","name",None),("vendors","name",None),("it_products","name",None),("programs","name",None)]
    for name,a,b in tables:
        t=metadata.tables.get(name)
        if t is None or a not in t.c: continue
        cond=t.c[a].ilike(term); 
        if b and b in t.c: cond=cond|t.c[b].ilike(term)
        rows=(await db.execute(select(t).where(cond).limit(limit))).mappings().all()
        for row in rows: out.append({"type":name,"id":row.get("id"),"data":dict(row)})
    return out[:limit]

@router.get("/audit-log",dependencies=[Depends(require_roles("admin"))])
async def audit_log(limit:int=Query(100,ge=1,le=500),db:AsyncSession=Depends(get_db)):
    t=metadata.tables["audit_log"]; return [dict(x) for x in (await db.execute(select(t).order_by(t.c.created_at.desc()).limit(limit))).mappings().all()]

@router.post("/webhooks",dependencies=[Depends(require_roles("admin"))])
async def create_webhook(payload:WebhookCreate,user:CurrentUser=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    t=metadata.tables["webhooks"]; row=(await db.execute(__import__('sqlalchemy').insert(t).values(name=payload.name,url=str(payload.url),secret=payload.secret,events=payload.events,active=payload.active,created_by=user.id).returning(t))).mappings().one(); await db.commit(); return dict(row)

@router.get("/webhooks",dependencies=[Depends(require_roles("admin"))])
async def list_webhooks(db:AsyncSession=Depends(get_db)):
    t=metadata.tables["webhooks"]; return [dict(x) for x in (await db.execute(select(t).order_by(t.c.id.desc()))).mappings().all()]

@router.delete("/webhooks/{webhook_id}",dependencies=[Depends(require_roles("admin"))])
async def delete_webhook(webhook_id:int,db:AsyncSession=Depends(get_db)):
    t=metadata.tables["webhooks"]; r=await db.execute(delete(t).where(t.c.id==webhook_id));
    if not r.rowcount: raise HTTPException(404,"Webhook not found")
    await db.commit(); return {"message":"Webhook deleted"}

@router.get("/metrics",dependencies=[Depends(require_roles("admin"))])
async def metrics(db:AsyncSession=Depends(get_db)):
    result={}
    for table in ("users","universities","programs","interactions","tasks","documents"):
        t=metadata.tables.get(table)
        if t is not None: result[table]=(await db.execute(select(func.count()).select_from(t))).scalar_one()
    return result

@router.websocket("/ws")
async def websocket_notifications(websocket:WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()
            await websocket.send_json({"type":"ping","timestamp":datetime.now(timezone.utc).isoformat()})
    except WebSocketDisconnect: pass
