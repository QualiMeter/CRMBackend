from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.auth import CurrentUser, require_roles
from app.db.session import get_db
from app.models.models import metadata
from app.schemas.education import (
    StudentProfileResponse, StudentProfileUpsert,
    TeacherProfileResponse, TeacherProfileUpsert,
)

router = APIRouter(tags=["education"])


def _profile_tables():
    return metadata.tables["users"], metadata.tables["student_profiles"], metadata.tables["teacher_profiles"]


async def _student(db: AsyncSession, user_id: int):
    users, students, _ = _profile_tables()
    row = (await db.execute(select(users, students).join(students, students.c.user_id == users.c.id).where(users.c.id == user_id))).mappings().first()
    return dict(row) if row else None


async def _teacher(db: AsyncSession, user_id: int):
    users, _, teachers = _profile_tables()
    row = (await db.execute(select(users, teachers).join(teachers, teachers.c.user_id == users.c.id).where(users.c.id == user_id))).mappings().first()
    return dict(row) if row else None


def _student_response(row):
    return {k: row[k] for k in (
        "user_id", "email", "full_name", "status", "student_number", "university_id",
        "program_id", "course_year", "group_name", "enrollment_year", "graduation_year",
        "created_at", "updated_at") if k in row}


def _teacher_response(row):
    return {k: row[k] for k in (
        "user_id", "email", "full_name", "status", "employee_number", "university_id",
        "department", "academic_title", "specialization", "created_at", "updated_at") if k in row}


@router.get("/students", response_model=list[StudentProfileResponse], dependencies=[Depends(require_roles("admin", "manager", "teacher"))])
async def list_students(db: AsyncSession = Depends(get_db)):
    users, students, _ = _profile_tables()
    rows = (await db.execute(select(users, students).join(students, students.c.user_id == users.c.id).order_by(users.c.id))).mappings().all()
    return [_student_response(dict(r)) for r in rows]


@router.get("/students/me", response_model=StudentProfileResponse)
async def get_my_student_profile(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if "student" not in current.roles:
        raise HTTPException(403, "Student role required")
    row = await _student(db, current.id)
    if not row:
        raise HTTPException(404, "Student profile not found")
    return _student_response(row)


@router.put("/students/me", response_model=StudentProfileResponse)
async def upsert_my_student_profile(payload: StudentProfileUpsert, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if "student" not in current.roles:
        raise HTTPException(403, "Student role required")
    users, students, _ = _profile_tables()
    exists = await db.scalar(select(students.c.user_id).where(students.c.user_id == current.id))
    values = payload.model_dump()
    if exists is None:
        await db.execute(insert(students).values(user_id=current.id, **values))
    else:
        await db.execute(update(students).where(students.c.user_id == current.id).values(**values))
    await db.commit()
    row = await _student(db, current.id)
    return _student_response(row)


@router.get("/teachers", response_model=list[TeacherProfileResponse], dependencies=[Depends(require_roles("admin", "manager", "teacher"))])
async def list_teachers(db: AsyncSession = Depends(get_db)):
    users, _, teachers = _profile_tables()
    rows = (await db.execute(select(users, teachers).join(teachers, teachers.c.user_id == users.c.id).order_by(users.c.id))).mappings().all()
    return [_teacher_response(dict(r)) for r in rows]


@router.get("/teachers/me", response_model=TeacherProfileResponse)
async def get_my_teacher_profile(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if "teacher" not in current.roles:
        raise HTTPException(403, "Teacher role required")
    row = await _teacher(db, current.id)
    if not row:
        raise HTTPException(404, "Teacher profile not found")
    return _teacher_response(row)


@router.put("/teachers/me", response_model=TeacherProfileResponse)
async def upsert_my_teacher_profile(payload: TeacherProfileUpsert, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if "teacher" not in current.roles:
        raise HTTPException(403, "Teacher role required")
    users, _, teachers = _profile_tables()
    exists = await db.scalar(select(teachers.c.user_id).where(teachers.c.user_id == current.id))
    values = payload.model_dump()
    if exists is None:
        await db.execute(insert(teachers).values(user_id=current.id, **values))
    else:
        await db.execute(update(teachers).where(teachers.c.user_id == current.id).values(**values))
    await db.commit()
    row = await _teacher(db, current.id)
    return _teacher_response(row)
