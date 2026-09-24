from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class StudentProfileBase(BaseModel):
    student_number: str | None = Field(default=None, max_length=80)
    university_id: int | None = None
    program_id: int | None = None
    course_year: int | None = Field(default=None, ge=1, le=12)
    group_name: str | None = Field(default=None, max_length=100)
    enrollment_year: int | None = Field(default=None, ge=1900, le=2200)
    graduation_year: int | None = Field(default=None, ge=1900, le=2200)


class StudentProfileUpsert(StudentProfileBase):
    pass


class StudentProfileResponse(StudentProfileBase):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    email: str
    full_name: str
    status: str
    created_at: datetime
    updated_at: datetime


class TeacherProfileBase(BaseModel):
    employee_number: str | None = Field(default=None, max_length=80)
    university_id: int | None = None
    department: str | None = Field(default=None, max_length=200)
    academic_title: str | None = Field(default=None, max_length=200)
    specialization: str | None = Field(default=None, max_length=300)


class TeacherProfileUpsert(TeacherProfileBase):
    pass


class TeacherProfileResponse(TeacherProfileBase):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    email: str
    full_name: str
    status: str
    created_at: datetime
    updated_at: datetime
