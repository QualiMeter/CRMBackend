from typing import Any
from pydantic import BaseModel, Field, ConfigDict

class DatabaseSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tables: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    deleted: dict[str, list[Any]] = Field(default_factory=dict)
    replace: bool = False

class DatabaseSyncResponse(BaseModel):
    success: bool
    tables: dict[str, dict[str, int]]
    total_received: int
    total_created: int
    total_updated: int
    total_deleted: int
