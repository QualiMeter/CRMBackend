from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from scalar_fastapi import add_scalar_reference
from sqlalchemy.exc import IntegrityError

from app.api.routers import (
    auth, comments, crud, documents_extra, files, health, imports, reports,
    sync, users,
)
from app.core.config import settings
from app.db.session import engine, ping_db
from app.db.auth_tables import ensure_auth_tables
from app.models.models import reflect_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ping_db()
    await reflect_schema(engine)
    await ensure_auth_tables(engine)
    # Reflect the two authentication support tables so the auth layer can use them.
    await reflect_schema(engine)
    crud.register_all_tables()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "RTK IT School CRM API. Authentication is handled locally by the API using signed JWT access tokens and database-backed refresh sessions. "
        "The API exposes named CRUD "
        "resources, multipart uploads, imports and reports."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

origins = [x.strip() for x in settings.cors_origins.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID")
    try:
        UUID(request_id) if request_id else None
    except (ValueError, AttributeError):
        request_id = None
    request.state.request_id = request_id or str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


def error_body(request: Request, status_code: int, detail: str, code: str):
    return {
        "detail": detail,
        "code": code,
        "request_id": getattr(request.state, "request_id", None),
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code_by_status = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "TOO_MANY_REQUESTS",
        502: "UPSTREAM_ERROR",
    }
    code = code_by_status.get(exc.status_code, "HTTP_ERROR")
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(request, exc.status_code, detail, code),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    details = []
    for item in exc.errors():
        location = [str(x) for x in item.get("loc", [])]
        # Hide the raw password value if Pydantic ever includes input data.
        safe = {
            "field": ".".join(location),
            "message": item.get("msg", "Invalid value"),
            "type": item.get("type"),
        }
        details.append(safe)
    return JSONResponse(
        status_code=422,
        content={
            **error_body(request, 422, "Request validation failed", "VALIDATION_ERROR"),
            "details": details,
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content=error_body(request, 409, "Database constraint conflict", "CONFLICT"),
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=error_body(request, 500, "Internal server error", "INTERNAL_ERROR"),
    )


app.include_router(health.router)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(files.router, prefix=settings.api_prefix)
app.include_router(comments.router, prefix=settings.api_prefix)
app.include_router(imports.router, prefix=settings.api_prefix)
app.include_router(reports.router, prefix=settings.api_prefix)
app.include_router(documents_extra.router, prefix=settings.api_prefix)
app.include_router(sync.router, prefix=settings.api_prefix)
app.include_router(crud.router, prefix=settings.api_prefix)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    components["ErrorResponse"] = {
        "type": "object",
        "required": ["detail", "code", "request_id"],
        "properties": {
            "detail": {"type": "string"},
            "code": {"type": "string"},
            "request_id": {"type": "string", "format": "uuid"},
            "details": {"type": "array", "items": {"type": "object"}},
        },
    }
    common = {
        "401": "Authentication required or JWT is invalid/expired",
        "403": "Authenticated user lacks the required role or access",
        "404": "Resource not found",
        "409": "Database/unique/relationship conflict",
        "422": "Request validation failed",
        "500": "Unexpected server-side error",
    }
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict) or "responses" not in operation:
                continue
            for code, description in common.items():
                operation["responses"].setdefault(
                    code,
                    {
                        "description": description,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                )
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi
add_scalar_reference(app, route="/scalar")
