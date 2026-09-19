from __future__ import annotations
from typing import Any
from uuid import UUID
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import get_db

bearer=HTTPBearer(auto_error=False)
def _issuer(): return f"{settings.keycloak_url.rstrip('/')}/realms/{settings.keycloak_realm}"
def _jwks_url(): return f"{_issuer()}/protocol/openid-connect/certs"
_jwk_client=PyJWKClient(_jwks_url())

class CurrentUser:
    def __init__(self,claims,db_user,roles): self.claims=claims; self.db_user=db_user; self.roles=roles
    @property
    def id(self): return int(self.db_user["id"])
    @property
    def subject(self): return str(self.claims.get("sub"))

def _extract_roles(claims:dict[str,Any])->set[str]:
    realm=claims.get(settings.keycloak_role_claim,{})
    if isinstance(realm,dict) and isinstance(realm.get(settings.keycloak_roles_claim),list): return {str(x) for x in realm[settings.keycloak_roles_claim]}
    ra=claims.get("resource_access",{})
    if isinstance(ra,dict):
        client=ra.get(settings.keycloak_client_id,{})
        if isinstance(client,dict) and isinstance(client.get("roles"),list): return {str(x) for x in client["roles"]}
    return set()

def _decode(token:str):
    try:
        key=_jwk_client.get_signing_key_from_jwt(token).key
        kwargs={"key":key,"algorithms":["RS256","RS384","RS512"],"issuer":_issuer(),"options":{"verify_aud":settings.keycloak_verify_audience}}
        if settings.keycloak_verify_audience and settings.keycloak_audience: kwargs["audience"]=settings.keycloak_audience
        return jwt.decode(token,**kwargs)
    except Exception as exc:
        raise HTTPException(401,"Invalid or expired access token",headers={"WWW-Authenticate":"Bearer"}) from exc

async def _load_or_provision(db:AsyncSession,claims:dict[str,Any],jwt_roles:set[str]):
    from app.models.models import metadata
    users=metadata.tables["users"]; roles=metadata.tables["roles"]; ur=metadata.tables["user_roles"]
    sub=claims.get("sub"); email=claims.get("email") or claims.get("preferred_username")
    if not sub or not email: raise HTTPException(401,"JWT must contain sub and email")
    try: subject=UUID(str(sub))
    except ValueError: subject=None
    row=(await db.execute(select(users).where(users.c.keycloak_subject==subject))).mappings().first() if subject else None
    if row is None: row=(await db.execute(select(users).where(users.c.email==email))).mappings().first()
    if row is None:
        if not settings.auth_auto_provision: raise HTTPException(403,"User is not registered in CRM")
        valid_roles=[r for r in jwt_roles if r in {"user","manager","admin"}]
        default_role="user" if "user" not in valid_roles and not valid_roles else None
        result=await db.execute(insert(users).values(keycloak_subject=subject,email=email,full_name=claims.get("name") or claims.get("preferred_username") or email,status="active",last_login_at=__import__('sqlalchemy').func.now()).returning(users))
        row=result.mappings().one();
        role_names=valid_roles or [default_role]
        for code in role_names:
            rid=(await db.execute(select(roles.c.id).where(roles.c.code==code))).scalar_one_or_none()
            if rid: await db.execute(insert(ur).values(user_id=row["id"],role_id=rid))
        await db.commit()
    elif str(row["status"])=="blocked": raise HTTPException(403,"User is blocked")
    else:
        await db.execute(update(users).where(users.c.id==row["id"]).values(last_login_at=__import__('sqlalchemy').func.now()))
        # Sync known Keycloak roles into the CRM role table; unknown roles are ignored.
        known={"user","manager","admin"}; desired=jwt_roles & known
        if desired:
            role_rows=(await db.execute(select(roles.c.id,roles.c.code).where(roles.c.code.in_(desired)))).all()
            await db.execute(delete(ur).where(ur.c.user_id==row["id"]))
            for rid,_ in role_rows: await db.execute(insert(ur).values(user_id=row["id"],role_id=rid))
        await db.commit()
    role_rows=(await db.execute(select(roles.c.code).join(ur,ur.c.role_id==roles.c.id).where(ur.c.user_id==row["id"]))).all()
    return dict(row),{x[0] for x in role_rows}

async def get_current_user(credentials:HTTPAuthorizationCredentials|None=Depends(bearer),db:AsyncSession=Depends(get_db)):
    if not settings.auth_required:
        return CurrentUser({"sub":"anonymous"},{"id":0,"status":"active"},{"admin"})
    if credentials is None: raise HTTPException(401,"Bearer token required",headers={"WWW-Authenticate":"Bearer"})
    claims=_decode(credentials.credentials); jwt_roles=_extract_roles(claims)
    user,db_roles=await _load_or_provision(db,claims,jwt_roles)
    return CurrentUser(claims,user,db_roles or jwt_roles)

def require_roles(*required:str):
    async def dependency(user:CurrentUser=Depends(get_current_user)):
        if not user.roles.intersection(required): raise HTTPException(403,f"Required role: {' or '.join(required)}")
        return user
    return dependency
