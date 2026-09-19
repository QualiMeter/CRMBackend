from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from scalar_fastapi import add_scalar_reference
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.session import engine, ping_db
from app.models.models import reflect_schema
from app.api.routers import health, crud, auth, users, files, comments, imports, reports, documents_extra, sync

@asynccontextmanager
async def lifespan(app: FastAPI):
    await ping_db()
    await reflect_schema(engine)
    crud.register_all_tables()
    yield

app=FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="RTK IT School CRM API with Keycloak JWT, role-based access, explicit CRUD resources, file upload, imports and reports.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins if origins else ["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id=str(uuid4())
    response=await call_next(request)
    response.headers["X-Request-ID"]=request.state.request_id
    return response

def error(request:Request,status_code:int,detail:str,code:str|None=None):
    return JSONResponse(status_code=status_code,content={"detail":detail,"code":code,"request_id":getattr(request.state,"request_id",None)})

@app.exception_handler(RequestValidationError)
async def validation_handler(request:Request,exc:RequestValidationError):
    return error(request,422,"Request validation failed","VALIDATION_ERROR")

@app.exception_handler(IntegrityError)
async def integrity_handler(request:Request,exc:IntegrityError):
    return error(request,409,"Database constraint conflict","CONFLICT")

@app.exception_handler(Exception)
async def unhandled_handler(request:Request,exc:Exception):
    return error(request,500,"Internal server error","INTERNAL_ERROR")

app.include_router(health.router)
app.include_router(auth.router,prefix=settings.api_prefix)
app.include_router(users.router,prefix=settings.api_prefix)
app.include_router(files.router,prefix=settings.api_prefix)
app.include_router(comments.router,prefix=settings.api_prefix)
app.include_router(imports.router,prefix=settings.api_prefix)
app.include_router(reports.router,prefix=settings.api_prefix)
app.include_router(documents_extra.router,prefix=settings.api_prefix)
app.include_router(sync.router,prefix=settings.api_prefix)
app.include_router(crud.router,prefix=settings.api_prefix)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema=get_openapi(title=app.title,version=app.version,description=app.description,routes=app.routes)
    components=schema.setdefault("components",{}).setdefault("schemas",{})
    components["ErrorResponse"]={"type":"object","required":["detail"],"properties":{"detail":{"type":"string"},"code":{"type":"string","nullable":True},"request_id":{"type":"string","format":"uuid","nullable":True}}}
    common={
      "401":{"description":"Authentication required or JWT is invalid/expired","content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErrorResponse"}}}},
      "403":{"description":"Authenticated user lacks the required role or access","content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErrorResponse"}}}},
      "404":{"description":"Resource not found","content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErrorResponse"}}}},
      "409":{"description":"Database/unique/relationship conflict","content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErrorResponse"}}}},
      "422":{"description":"Request validation failed","content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErrorResponse"}}}},
      "500":{"description":"Internal server error","content":{"application/json":{"schema":{"$ref":"#/components/schemas/ErrorResponse"}}}},
    }
    for path in schema.get("paths",{}).values():
        for operation in path.values():
            if isinstance(operation,dict) and "responses" in operation:
                for code,value in common.items(): operation["responses"].setdefault(code,value)
    app.openapi_schema=schema
    return schema

app.openapi=custom_openapi

add_scalar_reference(app,route="/scalar")
