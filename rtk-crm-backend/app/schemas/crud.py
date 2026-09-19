from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

class UsersCreateRequest(SchemaBase):
    id: int | None = None
    email: str | None = None
    full_name: str | None = None
    position: str | None = None
    phone: str | None = None
    status: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class UsersUpdateRequest(SchemaBase):
    id: int | None = None
    email: str | None = None
    full_name: str | None = None
    position: str | None = None
    phone: str | None = None
    status: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class UsersResponse(SchemaBase):
    id: int | None = None
    email: str | None = None
    full_name: str | None = None
    position: str | None = None
    phone: str | None = None
    status: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class RolesCreateRequest(SchemaBase):
    id: int | None = None
    code: str | None = None
    name: str | None = None
    description: str | None = None

class RolesUpdateRequest(SchemaBase):
    id: int | None = None
    code: str | None = None
    name: str | None = None
    description: str | None = None

class RolesResponse(SchemaBase):
    id: int | None = None
    code: str | None = None
    name: str | None = None
    description: str | None = None

class PermissionsCreateRequest(SchemaBase):
    id: int | None = None
    code: str | None = None
    description: str | None = None

class PermissionsUpdateRequest(SchemaBase):
    id: int | None = None
    code: str | None = None
    description: str | None = None

class PermissionsResponse(SchemaBase):
    id: int | None = None
    code: str | None = None
    description: str | None = None

class RolePermissionsCreateRequest(SchemaBase):
    role_id: int | None = None
    permission_id: int | None = None

class RolePermissionsUpdateRequest(SchemaBase):
    role_id: int | None = None
    permission_id: int | None = None

class RolePermissionsResponse(SchemaBase):
    role_id: int | None = None
    permission_id: int | None = None

class UserRolesCreateRequest(SchemaBase):
    user_id: int | None = None
    role_id: int | None = None
    granted_by: int | None = None
    granted_at: datetime | None = None

class UserRolesUpdateRequest(SchemaBase):
    user_id: int | None = None
    role_id: int | None = None
    granted_by: int | None = None
    granted_at: datetime | None = None

class UserRolesResponse(SchemaBase):
    user_id: int | None = None
    role_id: int | None = None
    granted_by: int | None = None
    granted_at: datetime | None = None

class UniversitiesCreateRequest(SchemaBase):
    id: int | None = None
    name: str | None = None
    short_name: str | None = None
    city: str | None = None
    region: str | None = None
    website_url: str | None = None
    external_code: str | None = None
    status: str | None = None
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None

class UniversitiesUpdateRequest(SchemaBase):
    id: int | None = None
    name: str | None = None
    short_name: str | None = None
    city: str | None = None
    region: str | None = None
    website_url: str | None = None
    external_code: str | None = None
    status: str | None = None
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None

class UniversitiesResponse(SchemaBase):
    id: int | None = None
    name: str | None = None
    short_name: str | None = None
    city: str | None = None
    region: str | None = None
    website_url: str | None = None
    external_code: str | None = None
    status: str | None = None
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None

class UserUniversityAccessCreateRequest(SchemaBase):
    user_id: int | None = None
    university_id: int | None = None
    is_manager: bool | None = None
    granted_by: int | None = None
    granted_at: datetime | None = None

class UserUniversityAccessUpdateRequest(SchemaBase):
    user_id: int | None = None
    university_id: int | None = None
    is_manager: bool | None = None
    granted_by: int | None = None
    granted_at: datetime | None = None

class UserUniversityAccessResponse(SchemaBase):
    user_id: int | None = None
    university_id: int | None = None
    is_manager: bool | None = None
    granted_by: int | None = None
    granted_at: datetime | None = None

class UniversityContactsCreateRequest(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    full_name: str | None = None
    position: str | None = None
    email: str | None = None
    phone: str | None = None
    is_primary: bool | None = None
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class UniversityContactsUpdateRequest(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    full_name: str | None = None
    position: str | None = None
    email: str | None = None
    phone: str | None = None
    is_primary: bool | None = None
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class UniversityContactsResponse(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    full_name: str | None = None
    position: str | None = None
    email: str | None = None
    phone: str | None = None
    is_primary: bool | None = None
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class ItDirectionsCreateRequest(SchemaBase):
    id: int | None = None
    name: str | None = None
    code: str | None = None
    description: str | None = None
    is_active: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class ItDirectionsUpdateRequest(SchemaBase):
    id: int | None = None
    name: str | None = None
    code: str | None = None
    description: str | None = None
    is_active: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class ItDirectionsResponse(SchemaBase):
    id: int | None = None
    name: str | None = None
    code: str | None = None
    description: str | None = None
    is_active: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class VendorsCreateRequest(SchemaBase):
    id: int | None = None
    name: str | None = None
    website_url: str | None = None
    description: str | None = None
    is_active: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class VendorsUpdateRequest(SchemaBase):
    id: int | None = None
    name: str | None = None
    website_url: str | None = None
    description: str | None = None
    is_active: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class VendorsResponse(SchemaBase):
    id: int | None = None
    name: str | None = None
    website_url: str | None = None
    description: str | None = None
    is_active: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class ItProductsCreateRequest(SchemaBase):
    id: int | None = None
    vendor_id: int | None = None
    name: str | None = None
    software_name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class ItProductsUpdateRequest(SchemaBase):
    id: int | None = None
    vendor_id: int | None = None
    name: str | None = None
    software_name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class ItProductsResponse(SchemaBase):
    id: int | None = None
    vendor_id: int | None = None
    name: str | None = None
    software_name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class ItProductDirectionsCreateRequest(SchemaBase):
    product_id: int | None = None
    direction_id: int | None = None

class ItProductDirectionsUpdateRequest(SchemaBase):
    product_id: int | None = None
    direction_id: int | None = None

class ItProductDirectionsResponse(SchemaBase):
    product_id: int | None = None
    direction_id: int | None = None

class ProgramsCreateRequest(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    direction_id: int | None = None
    name: str | None = None
    description: str | None = None
    academic_year: str | None = None
    applications_count: int | None = None
    students_count: int | None = None
    streams_count: int | None = None
    demand_score: Decimal | None = None
    CASE: str | None = None
    ELSE: str | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None

class ProgramsUpdateRequest(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    direction_id: int | None = None
    name: str | None = None
    description: str | None = None
    academic_year: str | None = None
    applications_count: int | None = None
    students_count: int | None = None
    streams_count: int | None = None
    demand_score: Decimal | None = None
    CASE: str | None = None
    ELSE: str | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None

class ProgramsResponse(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    direction_id: int | None = None
    name: str | None = None
    description: str | None = None
    academic_year: str | None = None
    applications_count: int | None = None
    students_count: int | None = None
    streams_count: int | None = None
    demand_score: Decimal | None = None
    CASE: str | None = None
    ELSE: str | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None

class ProgramProductsCreateRequest(SchemaBase):
    program_id: int | None = None
    product_id: int | None = None
    is_primary: bool | None = None

class ProgramProductsUpdateRequest(SchemaBase):
    program_id: int | None = None
    product_id: int | None = None
    is_primary: bool | None = None

class ProgramProductsResponse(SchemaBase):
    program_id: int | None = None
    product_id: int | None = None
    is_primary: bool | None = None

class ContractsCreateRequest(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    program_id: int | None = None
    number: str | None = None
    signed_on: date | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    status: str | None = None
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    REFERENCES: str | None = None

class ContractsUpdateRequest(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    program_id: int | None = None
    number: str | None = None
    signed_on: date | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    status: str | None = None
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    REFERENCES: str | None = None

class ContractsResponse(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    program_id: int | None = None
    number: str | None = None
    signed_on: date | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    status: str | None = None
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    REFERENCES: str | None = None

class LicensesCreateRequest(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    program_id: int | None = None
    product_id: int | None = None
    contract_id: int | None = None
    signed_on: date | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    seats_count: int | None = None
    transfer_status: str | None = None
    transferred_at: datetime | None = None
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    REFERENCES: str | None = None
    REFERENCES: str | None = None

class LicensesUpdateRequest(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    program_id: int | None = None
    product_id: int | None = None
    contract_id: int | None = None
    signed_on: date | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    seats_count: int | None = None
    transfer_status: str | None = None
    transferred_at: datetime | None = None
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    REFERENCES: str | None = None
    REFERENCES: str | None = None

class LicensesResponse(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    program_id: int | None = None
    product_id: int | None = None
    contract_id: int | None = None
    signed_on: date | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    seats_count: int | None = None
    transfer_status: str | None = None
    transferred_at: datetime | None = None
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    REFERENCES: str | None = None
    REFERENCES: str | None = None

class WorkflowTemplatesCreateRequest(SchemaBase):
    id: int | None = None
    name: str | None = None
    description: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    version: int | None = None
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class WorkflowTemplatesUpdateRequest(SchemaBase):
    id: int | None = None
    name: str | None = None
    description: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    version: int | None = None
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class WorkflowTemplatesResponse(SchemaBase):
    id: int | None = None
    name: str | None = None
    description: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    version: int | None = None
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class WorkflowTemplateStagesCreateRequest(SchemaBase):
    id: int | None = None
    template_id: int | None = None
    position: int | None = None
    code: str | None = None
    name: str | None = None
    description: str | None = None
    is_optional: bool | None = None
    default_duration_days: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class WorkflowTemplateStagesUpdateRequest(SchemaBase):
    id: int | None = None
    template_id: int | None = None
    position: int | None = None
    code: str | None = None
    name: str | None = None
    description: str | None = None
    is_optional: bool | None = None
    default_duration_days: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class WorkflowTemplateStagesResponse(SchemaBase):
    id: int | None = None
    template_id: int | None = None
    position: int | None = None
    code: str | None = None
    name: str | None = None
    description: str | None = None
    is_optional: bool | None = None
    default_duration_days: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class InteractionsCreateRequest(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    program_id: int | None = None
    product_id: int | None = None
    template_id: int | None = None
    name: str | None = None
    status: str | None = None
    owner_user_id: int | None = None
    starts_on: date | None = None
    planned_end_on: date | None = None
    completed_on: date | None = None
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    REFERENCES: str | None = None
    REFERENCES: str | None = None

class InteractionsUpdateRequest(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    program_id: int | None = None
    product_id: int | None = None
    template_id: int | None = None
    name: str | None = None
    status: str | None = None
    owner_user_id: int | None = None
    starts_on: date | None = None
    planned_end_on: date | None = None
    completed_on: date | None = None
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    REFERENCES: str | None = None
    REFERENCES: str | None = None

class InteractionsResponse(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    program_id: int | None = None
    product_id: int | None = None
    template_id: int | None = None
    name: str | None = None
    status: str | None = None
    owner_user_id: int | None = None
    starts_on: date | None = None
    planned_end_on: date | None = None
    completed_on: date | None = None
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    REFERENCES: str | None = None
    REFERENCES: str | None = None

class WorkflowStageInstancesCreateRequest(SchemaBase):
    id: int | None = None
    interaction_id: int | None = None
    template_stage_id: int | None = None
    position: int | None = None
    code: str | None = None
    name: str | None = None
    status: str | None = None
    responsible_user_id: int | None = None
    started_at: datetime | None = None
    due_at: datetime | None = None
    completed_at: datetime | None = None
    is_optional: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class WorkflowStageInstancesUpdateRequest(SchemaBase):
    id: int | None = None
    interaction_id: int | None = None
    template_stage_id: int | None = None
    position: int | None = None
    code: str | None = None
    name: str | None = None
    status: str | None = None
    responsible_user_id: int | None = None
    started_at: datetime | None = None
    due_at: datetime | None = None
    completed_at: datetime | None = None
    is_optional: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class WorkflowStageInstancesResponse(SchemaBase):
    id: int | None = None
    interaction_id: int | None = None
    template_stage_id: int | None = None
    position: int | None = None
    code: str | None = None
    name: str | None = None
    status: str | None = None
    responsible_user_id: int | None = None
    started_at: datetime | None = None
    due_at: datetime | None = None
    completed_at: datetime | None = None
    is_optional: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class StageTransitionsCreateRequest(SchemaBase):
    id: int | None = None
    stage_instance_id: int | None = None
    from_status: str | None = None
    to_status: str | None = None
    changed_by: int | None = None
    comment: str | None = None
    created_at: datetime | None = None

class StageTransitionsUpdateRequest(SchemaBase):
    id: int | None = None
    stage_instance_id: int | None = None
    from_status: str | None = None
    to_status: str | None = None
    changed_by: int | None = None
    comment: str | None = None
    created_at: datetime | None = None

class StageTransitionsResponse(SchemaBase):
    id: int | None = None
    stage_instance_id: int | None = None
    from_status: str | None = None
    to_status: str | None = None
    changed_by: int | None = None
    comment: str | None = None
    created_at: datetime | None = None

class StageCommentsCreateRequest(SchemaBase):
    id: int | None = None
    stage_instance_id: int | None = None
    author_id: int | None = None
    body: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

class StageCommentsUpdateRequest(SchemaBase):
    id: int | None = None
    stage_instance_id: int | None = None
    author_id: int | None = None
    body: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

class StageCommentsResponse(SchemaBase):
    id: int | None = None
    stage_instance_id: int | None = None
    author_id: int | None = None
    body: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

class FilesCreateRequest(SchemaBase):
    id: UUID | None = None
    storage_key: str | None = None
    original_name: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    checksum_sha256: str | None = None
    uploaded_by: int | None = None
    created_at: datetime | None = None

class FilesUpdateRequest(SchemaBase):
    id: UUID | None = None
    storage_key: str | None = None
    original_name: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    checksum_sha256: str | None = None
    uploaded_by: int | None = None
    created_at: datetime | None = None

class FilesResponse(SchemaBase):
    id: UUID | None = None
    storage_key: str | None = None
    original_name: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    checksum_sha256: str | None = None
    uploaded_by: int | None = None
    created_at: datetime | None = None

class StageAttachmentsCreateRequest(SchemaBase):
    stage_instance_id: int | None = None
    file_id: UUID | None = None
    attached_by: int | None = None
    created_at: datetime | None = None

class StageAttachmentsUpdateRequest(SchemaBase):
    stage_instance_id: int | None = None
    file_id: UUID | None = None
    attached_by: int | None = None
    created_at: datetime | None = None

class StageAttachmentsResponse(SchemaBase):
    stage_instance_id: int | None = None
    file_id: UUID | None = None
    attached_by: int | None = None
    created_at: datetime | None = None

class TasksCreateRequest(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    program_id: int | None = None
    interaction_id: int | None = None
    stage_instance_id: int | None = None
    title: str | None = None
    description: str | None = None
    assignee_id: int | None = None
    created_by: int | None = None
    due_at: datetime | None = None
    priority: str | None = None
    status: str | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    REFERENCES: str | None = None

class TasksUpdateRequest(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    program_id: int | None = None
    interaction_id: int | None = None
    stage_instance_id: int | None = None
    title: str | None = None
    description: str | None = None
    assignee_id: int | None = None
    created_by: int | None = None
    due_at: datetime | None = None
    priority: str | None = None
    status: str | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    REFERENCES: str | None = None

class TasksResponse(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    program_id: int | None = None
    interaction_id: int | None = None
    stage_instance_id: int | None = None
    title: str | None = None
    description: str | None = None
    assignee_id: int | None = None
    created_by: int | None = None
    due_at: datetime | None = None
    priority: str | None = None
    status: str | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    REFERENCES: str | None = None

class TaskAttachmentsCreateRequest(SchemaBase):
    task_id: int | None = None
    file_id: UUID | None = None

class TaskAttachmentsUpdateRequest(SchemaBase):
    task_id: int | None = None
    file_id: UUID | None = None

class TaskAttachmentsResponse(SchemaBase):
    task_id: int | None = None
    file_id: UUID | None = None

class DocumentsCreateRequest(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    program_id: int | None = None
    interaction_id: int | None = None
    category: str | None = None
    name: str | None = None
    status: str | None = None
    owner_id: int | None = None
    comment: str | None = None
    current_version: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None
    REFERENCES: str | None = None

class DocumentsUpdateRequest(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    program_id: int | None = None
    interaction_id: int | None = None
    category: str | None = None
    name: str | None = None
    status: str | None = None
    owner_id: int | None = None
    comment: str | None = None
    current_version: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None
    REFERENCES: str | None = None

class DocumentsResponse(SchemaBase):
    id: int | None = None
    university_id: int | None = None
    program_id: int | None = None
    interaction_id: int | None = None
    category: str | None = None
    name: str | None = None
    status: str | None = None
    owner_id: int | None = None
    comment: str | None = None
    current_version: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None
    REFERENCES: str | None = None

class DocumentVersionsCreateRequest(SchemaBase):
    id: int | None = None
    document_id: int | None = None
    version_number: int | None = None
    file_id: UUID | None = None
    uploaded_by: int | None = None
    change_comment: str | None = None
    created_at: datetime | None = None

class DocumentVersionsUpdateRequest(SchemaBase):
    id: int | None = None
    document_id: int | None = None
    version_number: int | None = None
    file_id: UUID | None = None
    uploaded_by: int | None = None
    change_comment: str | None = None
    created_at: datetime | None = None

class DocumentVersionsResponse(SchemaBase):
    id: int | None = None
    document_id: int | None = None
    version_number: int | None = None
    file_id: UUID | None = None
    uploaded_by: int | None = None
    change_comment: str | None = None
    created_at: datetime | None = None

class ImportJobsCreateRequest(SchemaBase):
    id: UUID | None = None
    source_file_id: UUID | None = None
    entity_type: str | None = None
    status: str | None = None
    column_mapping: dict[str, Any] | None = None
    total_rows: int | None = None
    valid_rows: int | None = None
    invalid_rows: int | None = None
    imported_rows: int | None = None
    created_by: int | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class ImportJobsUpdateRequest(SchemaBase):
    id: UUID | None = None
    source_file_id: UUID | None = None
    entity_type: str | None = None
    status: str | None = None
    column_mapping: dict[str, Any] | None = None
    total_rows: int | None = None
    valid_rows: int | None = None
    invalid_rows: int | None = None
    imported_rows: int | None = None
    created_by: int | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class ImportJobsResponse(SchemaBase):
    id: UUID | None = None
    source_file_id: UUID | None = None
    entity_type: str | None = None
    status: str | None = None
    column_mapping: dict[str, Any] | None = None
    total_rows: int | None = None
    valid_rows: int | None = None
    invalid_rows: int | None = None
    imported_rows: int | None = None
    created_by: int | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class ImportRowsCreateRequest(SchemaBase):
    id: int | None = None
    import_job_id: UUID | None = None
    row_number: int | None = None
    source_data: dict[str, Any] | None = None
    normalized_data: dict[str, Any] | None = None
    status: str | None = None
    errors: dict[str, Any] | None = None
    target_entity_type: str | None = None
    target_entity_id: int | None = None
    created_at: datetime | None = None

class ImportRowsUpdateRequest(SchemaBase):
    id: int | None = None
    import_job_id: UUID | None = None
    row_number: int | None = None
    source_data: dict[str, Any] | None = None
    normalized_data: dict[str, Any] | None = None
    status: str | None = None
    errors: dict[str, Any] | None = None
    target_entity_type: str | None = None
    target_entity_id: int | None = None
    created_at: datetime | None = None

class ImportRowsResponse(SchemaBase):
    id: int | None = None
    import_job_id: UUID | None = None
    row_number: int | None = None
    source_data: dict[str, Any] | None = None
    normalized_data: dict[str, Any] | None = None
    status: str | None = None
    errors: dict[str, Any] | None = None
    target_entity_type: str | None = None
    target_entity_id: int | None = None
    created_at: datetime | None = None

class ReportJobsCreateRequest(SchemaBase):
    id: UUID | None = None
    requested_by: int | None = None
    format: str | None = None
    status: str | None = None
    filters: dict[str, Any] | None = None
    selected_columns: dict[str, Any] | None = None
    result_file_id: UUID | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None

class ReportJobsUpdateRequest(SchemaBase):
    id: UUID | None = None
    requested_by: int | None = None
    format: str | None = None
    status: str | None = None
    filters: dict[str, Any] | None = None
    selected_columns: dict[str, Any] | None = None
    result_file_id: UUID | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None

class ReportJobsResponse(SchemaBase):
    id: UUID | None = None
    requested_by: int | None = None
    format: str | None = None
    status: str | None = None
    filters: dict[str, Any] | None = None
    selected_columns: dict[str, Any] | None = None
    result_file_id: UUID | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None

class IntegrationConnectionsCreateRequest(SchemaBase):
    id: int | None = None
    source: str | None = None
    name: str | None = None
    base_url: str | None = None
    credentials_secret_ref: str | None = None
    field_mapping: dict[str, Any] | None = None
    is_active: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class IntegrationConnectionsUpdateRequest(SchemaBase):
    id: int | None = None
    source: str | None = None
    name: str | None = None
    base_url: str | None = None
    credentials_secret_ref: str | None = None
    field_mapping: dict[str, Any] | None = None
    is_active: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class IntegrationConnectionsResponse(SchemaBase):
    id: int | None = None
    source: str | None = None
    name: str | None = None
    base_url: str | None = None
    credentials_secret_ref: str | None = None
    field_mapping: dict[str, Any] | None = None
    is_active: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

class SyncJobsCreateRequest(SchemaBase):
    id: UUID | None = None
    connection_id: int | None = None
    status: str | None = None
    request_payload: dict[str, Any] | None = None
    response_summary: dict[str, Any] | None = None
    received_rows: int | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None

class SyncJobsUpdateRequest(SchemaBase):
    id: UUID | None = None
    connection_id: int | None = None
    status: str | None = None
    request_payload: dict[str, Any] | None = None
    response_summary: dict[str, Any] | None = None
    received_rows: int | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None

class SyncJobsResponse(SchemaBase):
    id: UUID | None = None
    connection_id: int | None = None
    status: str | None = None
    request_payload: dict[str, Any] | None = None
    response_summary: dict[str, Any] | None = None
    received_rows: int | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None

class ActivitiesCreateRequest(SchemaBase):
    id: int | None = None
    kind: str | None = None
    university_id: int | None = None
    program_id: int | None = None
    interaction_id: int | None = None
    actor_id: int | None = None
    title: str | None = None
    description: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None

class ActivitiesUpdateRequest(SchemaBase):
    id: int | None = None
    kind: str | None = None
    university_id: int | None = None
    program_id: int | None = None
    interaction_id: int | None = None
    actor_id: int | None = None
    title: str | None = None
    description: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None

class ActivitiesResponse(SchemaBase):
    id: int | None = None
    kind: str | None = None
    university_id: int | None = None
    program_id: int | None = None
    interaction_id: int | None = None
    actor_id: int | None = None
    title: str | None = None
    description: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None

class AuditLogCreateRequest(SchemaBase):
    id: int | None = None
    actor_id: int | None = None
    action: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    university_id: int | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    changes: dict[str, Any] | None = None
    created_at: datetime | None = None

class AuditLogUpdateRequest(SchemaBase):
    id: int | None = None
    actor_id: int | None = None
    action: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    university_id: int | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    changes: dict[str, Any] | None = None
    created_at: datetime | None = None

class AuditLogResponse(SchemaBase):
    id: int | None = None
    actor_id: int | None = None
    action: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    university_id: int | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    changes: dict[str, Any] | None = None
    created_at: datetime | None = None

class UserDraftsCreateRequest(SchemaBase):
    user_id: int | None = None
    draft_key: str | None = None
    payload: dict[str, Any] | None = None
    expires_at: datetime | None = None
    updated_at: datetime | None = None

class UserDraftsUpdateRequest(SchemaBase):
    user_id: int | None = None
    draft_key: str | None = None
    payload: dict[str, Any] | None = None
    expires_at: datetime | None = None
    updated_at: datetime | None = None

class UserDraftsResponse(SchemaBase):
    user_id: int | None = None
    draft_key: str | None = None
    payload: dict[str, Any] | None = None
    expires_at: datetime | None = None
    updated_at: datetime | None = None
