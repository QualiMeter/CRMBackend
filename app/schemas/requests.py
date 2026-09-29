from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class BaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

class UserCreateRequest(BaseRequest):
    email: str
    full_name: str
    position: str | None = None
    phone: str | None = None
    supervisor_id: int | None = None
    status: str = "invited"
    role_codes: list[str] = Field(default_factory=list)

class UserUpdateRequest(BaseRequest):
    email: str | None = None
    full_name: str | None = None
    position: str | None = None
    phone: str | None = None
    supervisor_id: int | None = None
    status: str | None = None
    role_codes: list[str] | None = None

class RoleAssignmentRequest(BaseRequest):
    role_codes: list[str]

class CommentCreateRequest(BaseRequest):
    body: str = Field(min_length=1)

class CommentUpdateRequest(BaseRequest):
    body: str = Field(min_length=1)

class ImportCreateRequest(BaseRequest):
    entity_type: str
    column_mapping: dict[str, str] = Field(default_factory=dict)
    dry_run: bool = False

class ReportCreateRequest(BaseRequest):
    format: str
    filters: dict[str, Any] = Field(default_factory=dict)
    selected_columns: list[str] = Field(default_factory=list)

class DraftUpsertRequest(BaseRequest):
    payload: dict[str, Any]
    expires_at: str

class AttachmentRequest(BaseRequest):
    file_id: UUID
