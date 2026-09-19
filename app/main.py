from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import add_scalar_reference
from app.core.config import settings
from app.db.session import engine, ping_db
from app.models.models import reflect_schema
from app.api.routers import health, universities, crud, interactions, tasks, documents, dashboard, sync

@asynccontextmanager
async def lifespan(app: FastAPI):
    await ping_db()
    await reflect_schema(engine)
    yield

app=FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="RTK IT School CRM backend. PostgreSQL schema is the source of truth.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)
origins=[x.strip() for x in settings.cors_origins.split(",")]
app.add_middleware(CORSMiddleware,allow_origins=origins if origins != ["*"] else ["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(health.router)
app.include_router(universities.router,prefix=settings.api_prefix)
app.include_router(interactions.router,prefix=settings.api_prefix)
app.include_router(tasks.router,prefix=settings.api_prefix)
app.include_router(documents.router,prefix=settings.api_prefix)
app.include_router(dashboard.router,prefix=settings.api_prefix)
app.include_router(crud.router,prefix=settings.api_prefix)
app.include_router(sync.router,prefix=settings.api_prefix)
add_scalar_reference(app,route="/scalar")
