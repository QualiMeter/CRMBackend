from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

class ErrorResponse(APIModel):
    detail: str
    code: str | None = None
    request_id: str | None = None

class MessageResponse(APIModel):
    message: str

class UserResponse(APIModel):
    id: int
    keycloak_subject: UUID | None = None
    email: str
    full_name: str
    position: str | None = None
    phone: str | None = None
    status: str
    last_login_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    roles: list[str] = []

class MeResponse(UserResponse):
    claims: dict[str, Any] = {}

class RoleResponse(APIModel):
    id: int
    code: str
    name: str
    description: str | None = None

class PermissionResponse(APIModel):
    id: int
    code: str
    description: str

class UniversityResponse(APIModel):
    id: int; name: str; short_name: str; city: str; region: str|None=None; website_url: str|None=None; external_code: str|None=None; status: str; description: str|None=None; created_at: datetime|None=None; updated_at: datetime|None=None; archived_at: datetime|None=None
class UniversityContactResponse(APIModel):
    id:int; university_id:int; full_name:str; position:str; email:str|None=None; phone:str|None=None; is_primary:bool; comment:str|None=None; created_at:datetime|None=None; updated_at:datetime|None=None
class DirectionResponse(APIModel):
    id:int; name:str; code:str|None=None; description:str|None=None; is_active:bool; created_at:datetime|None=None; updated_at:datetime|None=None
class VendorResponse(APIModel):
    id:int; name:str; website_url:str|None=None; description:str|None=None; is_active:bool; created_at:datetime|None=None; updated_at:datetime|None=None
class ProductResponse(APIModel):
    id:int; vendor_id:int|None=None; name:str; software_name:str|None=None; description:str|None=None; is_active:bool; created_at:datetime|None=None; updated_at:datetime|None=None
class ProgramResponse(APIModel):
    id:int; university_id:int; direction_id:int; name:str; description:str|None=None; academic_year:str|None=None; applications_count:int; students_count:int; streams_count:int; demand_score:Decimal|None=None; starts_on:date|None=None; ends_on:date|None=None; created_at:datetime|None=None; updated_at:datetime|None=None; archived_at:datetime|None=None
class ContractResponse(APIModel):
    id:int; university_id:int; program_id:int|None=None; number:str; signed_on:date|None=None; valid_from:date|None=None; valid_until:date|None=None; status:str; comment:str|None=None; created_at:datetime|None=None; updated_at:datetime|None=None
class LicenseResponse(APIModel):
    id:int; university_id:int; program_id:int|None=None; product_id:int; contract_id:int|None=None; signed_on:date|None=None; valid_from:date|None=None; valid_until:date|None=None; seats_count:int|None=None; transfer_status:str; transferred_at:datetime|None=None; comment:str|None=None; created_at:datetime|None=None; updated_at:datetime|None=None
class WorkflowTemplateResponse(APIModel):
    id:int; name:str; description:str|None=None; is_default:bool; is_active:bool; version:int; created_by:int|None=None; created_at:datetime|None=None; updated_at:datetime|None=None
class WorkflowStageResponse(APIModel):
    id:int; template_id:int; position:int; code:str; name:str; description:str|None=None; is_optional:bool; default_duration_days:int|None=None; created_at:datetime|None=None; updated_at:datetime|None=None
class InteractionResponse(APIModel):
    id:int; university_id:int; program_id:int; product_id:int|None=None; template_id:int; name:str; status:str; owner_user_id:int|None=None; starts_on:date|None=None; planned_end_on:date|None=None; completed_on:date|None=None; comment:str|None=None; created_at:datetime|None=None; updated_at:datetime|None=None
class WorkflowStageInstanceResponse(APIModel):
    id:int; interaction_id:int; template_stage_id:int|None=None; position:int; code:str; name:str; status:str; responsible_user_id:int|None=None; started_at:datetime|None=None; due_at:datetime|None=None; completed_at:datetime|None=None; is_optional:bool; created_at:datetime|None=None; updated_at:datetime|None=None
class StageTransitionResponse(APIModel):
    id:int; stage_instance_id:int; from_status:str|None=None; to_status:str; changed_by:int|None=None; comment:str|None=None; created_at:datetime|None=None
class StageCommentResponse(APIModel):
    id:int; stage_instance_id:int; author_id:int|None=None; body:str; created_at:datetime|None=None; updated_at:datetime|None=None; deleted_at:datetime|None=None
class FileResponse(APIModel):
    id:UUID; storage_key:str; original_name:str; content_type:str; size_bytes:int; checksum_sha256:str|None=None; uploaded_by:int|None=None; created_at:datetime|None=None
class TaskResponse(APIModel):
    id:int; university_id:int; program_id:int|None=None; interaction_id:int|None=None; stage_instance_id:int|None=None; title:str; description:str|None=None; assignee_id:int|None=None; created_by:int|None=None; due_at:datetime|None=None; priority:str; status:str; completed_at:datetime|None=None; created_at:datetime|None=None; updated_at:datetime|None=None
class DocumentResponse(APIModel):
    id:int; university_id:int; program_id:int|None=None; interaction_id:int|None=None; category:str; name:str; status:str; owner_id:int|None=None; comment:str|None=None; current_version:int; created_at:datetime|None=None; updated_at:datetime|None=None; archived_at:datetime|None=None
class DocumentVersionResponse(APIModel):
    id:int; document_id:int; version_number:int; file_id:UUID; uploaded_by:int|None=None; change_comment:str|None=None; created_at:datetime|None=None
class ImportJobResponse(APIModel):
    id:UUID; source_file_id:UUID; entity_type:str; status:str; column_mapping:dict[str,Any]; total_rows:int; valid_rows:int; invalid_rows:int; imported_rows:int; created_by:int|None=None; error_message:str|None=None; started_at:datetime|None=None; completed_at:datetime|None=None; created_at:datetime|None=None; updated_at:datetime|None=None
class ImportRowResponse(APIModel):
    id:int; import_job_id:UUID; row_number:int; source_data:dict[str,Any]; normalized_data:dict[str,Any]|None=None; status:str; errors:list[Any]; target_entity_type:str|None=None; target_entity_id:int|None=None; created_at:datetime|None=None
class ReportJobResponse(APIModel):
    id:UUID; requested_by:int|None=None; format:str; status:str; filters:dict[str,Any]; selected_columns:list[Any]; result_file_id:UUID|None=None; error_message:str|None=None; started_at:datetime|None=None; completed_at:datetime|None=None; created_at:datetime|None=None
class IntegrationConnectionResponse(APIModel):
    id:int; source:str; name:str; base_url:str|None=None; credentials_secret_ref:str|None=None; field_mapping:dict[str,Any]; is_active:bool; created_at:datetime|None=None; updated_at:datetime|None=None
class SyncJobResponse(APIModel):
    id:UUID; connection_id:int; status:str; request_payload:dict[str,Any]|None=None; response_summary:dict[str,Any]|None=None; received_rows:int; error_message:str|None=None; started_at:datetime|None=None; completed_at:datetime|None=None; created_at:datetime|None=None
class ActivityResponse(APIModel):
    id:int; kind:str; university_id:int|None=None; program_id:int|None=None; interaction_id:int|None=None; actor_id:int|None=None; title:str; description:str|None=None; metadata:dict[str,Any]; created_at:datetime|None=None
class AuditLogResponse(APIModel):
    id:int; actor_id:int|None=None; action:str; entity_type:str; entity_id:str|None=None; university_id:int|None=None; ip_address:str|None=None; user_agent:str|None=None; changes:dict[str,Any]; created_at:datetime|None=None
class UserDraftResponse(APIModel):
    user_id:int; draft_key:str; payload:dict[str,Any]; expires_at:datetime; updated_at:datetime|None=None

# Generic request contracts used by all named CRUD endpoints.
class CRUDCreateRequest(APIModel):
    data: dict[str, Any] = Field(default_factory=dict)
class CRUDUpdateRequest(APIModel):
    data: dict[str, Any] = Field(default_factory=dict)
class ListResponse(APIModel):
    items: list[dict[str, Any]]
    total: int
