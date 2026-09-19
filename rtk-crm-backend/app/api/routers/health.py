from fastapi import APIRouter
from app.db.session import ping_db
router = APIRouter(tags=["health"])
@router.get("/health", summary="Health check")
async def health():
    await ping_db()
    return {"status": "ok", "database": "ok"}
