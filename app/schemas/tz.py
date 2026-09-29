from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class StudentCreate(BaseModel):
    university_id: int
    program_id: int | None = None
    full_name: str = Field(min_length=1, max_length=250)
    email: str
    user_id: int | None = None


class StudentUpdate(BaseModel):
    university_id: int | None = None
    program_id: int | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=250)
    email: str | None = None
    user_id: int | None = None


class StudentResponse(StudentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class TransitionRequestCreate(BaseModel):
    stage_instance_id: int
    to_status: str
    transition_kind: str = Field(default="status_change", pattern="^(status_change|rollback)$")
    target_stage_instance_id: int | None = None
    comment: str | None = None


class ReviewRequest(BaseModel):
    comment: str | None = None


class WorkflowStartRequest(BaseModel):
    template_id: int


class WorkflowBackRequest(BaseModel):
    current_stage_instance_id: int | None = None
    target_stage_instance_id: int
    reason: str = Field(min_length=1)


class WorkflowBranchRequest(BaseModel):
    from_stage_instance_id: int
    to_stage_instance_id: int
    reason: str | None = None


class IntegrationImportRequest(BaseModel):
    university_id: int | None = None
    program_id: int | None = None
