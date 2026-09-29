from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import delete, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.auth import CurrentUser, require_roles
from app.db.session import get_db
from app.models.models import metadata
from app.schemas.tz import (
    IntegrationImportRequest,
    ReviewRequest,
    StudentCreate,
    StudentResponse,
    StudentUpdate,
    TransitionRequestCreate,
    WorkflowBackRequest,
    WorkflowBranchRequest,
    WorkflowStartRequest,
)

router = APIRouter(tags=["CRM requirements"])


def T(name: str):
    return metadata.tables[name]


async def _user_university_ids(db: AsyncSession, current: CurrentUser) -> set[int] | None:
    if "admin" in current.roles:
        return None
    ua = T("user_university_access")
    users = T("users")
    if "leader" in current.roles:
        team = select(users.c.id).where(users.c.supervisor_id == current.id)
        rows = await db.execute(select(ua.c.university_id).where(or_(ua.c.user_id == current.id, ua.c.user_id.in_(team))))
    else:
        rows = await db.execute(select(ua.c.university_id).where(ua.c.user_id == current.id))
    return {int(r[0]) for r in rows.all()}


async def _assert_university_access(db: AsyncSession, current: CurrentUser, university_id: int, *, write: bool = False) -> None:
    if "admin" in current.roles:
        return
    allowed = await _user_university_ids(db, current)
    if allowed is None or university_id in allowed:
        return
    raise HTTPException(403, "University is outside your access scope")


async def _assert_interaction_access(db: AsyncSession, current: CurrentUser, interaction_id: int, *, write: bool = False) -> dict:
    i = T("interactions")
    row = (await db.execute(select(i).where(i.c.id == interaction_id))).mappings().first()
    if not row:
        raise HTTPException(404, "Interaction not found")
    await _assert_university_access(db, current, int(row["university_id"]), write=write)
    return dict(row)


# ----------------------------- access / team -----------------------------

@router.get("/users/team", dependencies=[Depends(require_roles("leader", "admin"))])
async def team_users(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    users, roles, ur = T("users"), T("roles"), T("user_roles")
    stmt = select(users).where(users.c.id != current.id)
    if "leader" in current.roles and "admin" not in current.roles:
        stmt = stmt.where(users.c.supervisor_id == current.id)
    rows = (await db.execute(stmt.order_by(users.c.id))).mappings().all()
    result = []
    for row in rows:
        role_rows = await db.execute(select(roles.c.code).join(ur, ur.c.role_id == roles.c.id).where(ur.c.user_id == row["id"]))
        item = dict(row)
        item["roles"] = [str(x[0]) for x in role_rows.all()]
        result.append(item)
    return result


@router.put("/universities/{university_id}/manager", dependencies=[Depends(require_roles("leader", "admin"))])
async def assign_university_manager(university_id: int, manager_user_id: int, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _assert_university_access(db, current, university_id)
    users, roles, ur, ua = T("users"), T("roles"), T("user_roles"), T("user_university_access")
    manager = (await db.execute(select(users.c.id, users.c.supervisor_id).join(ur, ur.c.user_id == users.c.id).join(roles, roles.c.id == ur.c.role_id).where(users.c.id == manager_user_id, roles.c.code == "manager"))).first()
    if not manager:
        raise HTTPException(422, "manager_user_id must belong to a manager")
    if "leader" in current.roles and "admin" not in current.roles and manager[1] != current.id:
        raise HTTPException(403, "You can assign only managers from your team")
    await db.execute(update(ua).where(ua.c.university_id == university_id).values(is_manager=False))
    existing = await db.scalar(select(ua.c.user_id).where(ua.c.user_id == manager_user_id, ua.c.university_id == university_id))
    if existing is None:
        await db.execute(insert(ua).values(user_id=manager_user_id, university_id=university_id, is_manager=True, granted_by=current.id))
    else:
        await db.execute(update(ua).where(ua.c.user_id == manager_user_id, ua.c.university_id == university_id).values(is_manager=True, granted_by=current.id))
    await db.commit()
    return {"university_id": university_id, "manager_user_id": manager_user_id}


# ----------------------------- directions/products/vendors -----------------------------

@router.get("/it-directions")
async def list_directions(db: AsyncSession = Depends(get_db)):
    t = T("it_directions")
    return [dict(x) for x in (await db.execute(select(t).order_by(t.c.name))).mappings().all()]


@router.post("/it-directions", status_code=201, dependencies=[Depends(require_roles("admin"))])
async def create_direction(payload: dict, db: AsyncSession = Depends(get_db)):
    t = T("it_directions")
    values = {k: v for k, v in payload.items() if k in t.c and k not in {"id", "created_at", "updated_at"}}
    row = (await db.execute(insert(t).values(**values).returning(t))).mappings().one()
    await db.commit()
    return dict(row)


@router.patch("/it-directions/{direction_id}", dependencies=[Depends(require_roles("admin"))])
async def update_direction(direction_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    t = T("it_directions")
    values = {k: v for k, v in payload.items() if k in t.c and k not in {"id", "created_at", "updated_at"}}
    row = (await db.execute(update(t).where(t.c.id == direction_id).values(**values).returning(t))).mappings().first()
    if not row:
        raise HTTPException(404, "IT direction not found")
    await db.commit()
    return dict(row)


@router.get("/it-products")
async def list_products(db: AsyncSession = Depends(get_db)):
    t = T("it_products")
    return [dict(x) for x in (await db.execute(select(t).order_by(t.c.name))).mappings().all()]


@router.post("/it-products", status_code=201, dependencies=[Depends(require_roles("admin"))])
async def create_product(payload: dict, db: AsyncSession = Depends(get_db)):
    t = T("it_products")
    values = {k: v for k, v in payload.items() if k in t.c and k not in {"id", "created_at", "updated_at"}}
    row = (await db.execute(insert(t).values(**values).returning(t))).mappings().one()
    await db.commit()
    return dict(row)


@router.patch("/it-products/{product_id}", dependencies=[Depends(require_roles("admin"))])
async def update_product(product_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    t = T("it_products")
    values = {k: v for k, v in payload.items() if k in t.c and k not in {"id", "created_at", "updated_at"}}
    row = (await db.execute(update(t).where(t.c.id == product_id).values(**values).returning(t))).mappings().first()
    if not row:
        raise HTTPException(404, "IT product not found")
    await db.commit()
    return dict(row)


@router.get("/vendors")
async def list_vendors(db: AsyncSession = Depends(get_db)):
    t = T("vendors")
    return [dict(x) for x in (await db.execute(select(t).order_by(t.c.name))).mappings().all()]


@router.post("/vendors", status_code=201, dependencies=[Depends(require_roles("admin"))])
async def create_vendor(payload: dict, db: AsyncSession = Depends(get_db)):
    t = T("vendors")
    values = {k: v for k, v in payload.items() if k in t.c and k not in {"id", "created_at", "updated_at"}}
    if "website" in payload and "website_url" in t.c and "website_url" not in values:
        values["website_url"] = payload["website"]
    row = (await db.execute(insert(t).values(**values).returning(t))).mappings().one()
    await db.commit()
    return dict(row)


@router.patch("/vendors/{vendor_id}", dependencies=[Depends(require_roles("admin"))])
async def update_vendor(vendor_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    t = T("vendors")
    values = {k: v for k, v in payload.items() if k in t.c and k not in {"id", "created_at", "updated_at"}}
    if "website" in payload and "website_url" in t.c:
        values["website_url"] = payload["website"]
    row = (await db.execute(update(t).where(t.c.id == vendor_id).values(**values).returning(t))).mappings().first()
    if not row:
        raise HTTPException(404, "Vendor not found")
    await db.commit()
    return dict(row)


@router.delete("/vendors/{vendor_id}", status_code=204, dependencies=[Depends(require_roles("admin"))])
async def delete_vendor(vendor_id: int, db: AsyncSession = Depends(get_db)):
    t = T("vendors")
    result = await db.execute(delete(t).where(t.c.id == vendor_id))
    if result.rowcount == 0:
        raise HTTPException(404, "Vendor not found")
    await db.commit()


# ----------------------------- programs / interactions -----------------------------

@router.get("/programs")
async def list_programs(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db), university_id: int | None = None, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    t = T("programs")
    stmt = select(t).order_by(t.c.id.desc()).offset(offset).limit(limit)
    allowed = await _user_university_ids(db, current)
    if allowed is not None:
        if not allowed:
            return []
        stmt = stmt.where(t.c.university_id.in_(allowed))
    if university_id is not None:
        stmt = stmt.where(t.c.university_id == university_id)
    return [dict(x) for x in (await db.execute(stmt)).mappings().all()]


@router.post("/programs", status_code=201, dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def create_program(payload: dict, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not payload.get("direction_id"):
        raise HTTPException(422, "direction_id is required")
    await _assert_university_access(db, current, int(payload["university_id"]), write=True)
    t = T("programs")
    values = {k: v for k, v in payload.items() if k in t.c and k not in {"id", "demand_score", "created_at", "updated_at"}}
    row = (await db.execute(insert(t).values(**values).returning(t))).mappings().one()
    await db.commit()
    return dict(row)


@router.patch("/programs/{program_id}", dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def update_program(program_id: int, payload: dict, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    t = T("programs")
    existing = (await db.execute(select(t).where(t.c.id == program_id))).mappings().first()
    if not existing:
        raise HTTPException(404, "Program not found")
    await _assert_university_access(db, current, int(existing["university_id"]), write=True)
    values = {k: v for k, v in payload.items() if k in t.c and k not in {"id", "demand_score", "created_at", "updated_at"}}
    row = (await db.execute(update(t).where(t.c.id == program_id).values(**values).returning(t))).mappings().one()
    await db.commit()
    return dict(row)


@router.get("/interactions")
async def list_interactions(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db), university_id: int | None = None, program_id: int | None = None, status: str | None = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    i = T("interactions")
    stmt = select(i).order_by(i.c.id.desc()).offset(offset).limit(limit)
    allowed = await _user_university_ids(db, current)
    if allowed is not None:
        if not allowed:
            return []
        stmt = stmt.where(i.c.university_id.in_(allowed))
    if university_id is not None:
        stmt = stmt.where(i.c.university_id == university_id)
    if program_id is not None:
        stmt = stmt.where(i.c.program_id == program_id)
    if status:
        stmt = stmt.where(i.c.status == status)
    return [dict(x) for x in (await db.execute(stmt)).mappings().all()]


@router.post("/interactions", status_code=201, dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def create_interaction(payload: dict, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not payload.get("university_id") or not payload.get("name"):
        raise HTTPException(422, "university_id and name are required")
    await _assert_university_access(db, current, int(payload["university_id"]), write=True)
    i = T("interactions")
    values = {k: v for k, v in payload.items() if k in i.c and k not in {"id", "created_at", "updated_at"}}
    if "responsible_user_id" in payload and "owner_user_id" in i.c:
        values["owner_user_id"] = payload["responsible_user_id"]
    if "workflow_template_id" in payload and "template_id" in i.c:
        values["template_id"] = payload["workflow_template_id"]
    if "template_id" in payload and "workflow_template_id" in i.c:
        values["workflow_template_id"] = payload["template_id"]
    if "responsible_user_id" in payload and "responsible_user_id" in i.c:
        values["responsible_user_id"] = payload["responsible_user_id"]
    row = (await db.execute(insert(i).values(**values).returning(i))).mappings().one()
    await db.commit()
    return dict(row)


@router.get("/interactions/{interaction_id}")
async def get_interaction(interaction_id: int, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _assert_interaction_access(db, current, interaction_id)


@router.patch("/interactions/{interaction_id}", dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def update_interaction(interaction_id: int, payload: dict, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    existing = await _assert_interaction_access(db, current, interaction_id, write=True)
    i, wi = T("interactions"), T("workflow_instances")
    values = {k: v for k, v in payload.items() if k in i.c and k not in {"id", "created_at", "updated_at"}}
    if "responsible_user_id" in payload:
        values["owner_user_id"] = payload["responsible_user_id"]
        if "responsible_user_id" in i.c:
            values["responsible_user_id"] = payload["responsible_user_id"]
    if "workflow_template_id" in payload:
        values["template_id"] = payload["workflow_template_id"]
        if "workflow_template_id" in i.c:
            values["workflow_template_id"] = payload["workflow_template_id"]
    if "template_id" in payload and "workflow_template_id" in i.c:
        values["workflow_template_id"] = payload["template_id"]
    if "template_id" in payload and await db.scalar(select(wi.c.id).where(wi.c.interaction_id == interaction_id)):
        old = existing.get("template_id")
        if old != payload["template_id"]:
            raise HTTPException(409, "Нельзя менять шаблон уже запущенного workflow")
    row = (await db.execute(update(i).where(i.c.id == interaction_id).values(**values).returning(i))).mappings().first()
    if not row:
        raise HTTPException(404, "Interaction not found")
    await db.commit()
    return dict(row)


# ----------------------------- workflow instance -----------------------------

@router.post("/interactions/{interaction_id}/workflow/start", dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def start_workflow(interaction_id: int, payload: WorkflowStartRequest, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _assert_interaction_access(db, current, interaction_id, write=True)
    wi, i, wt, stages, ts, history = (T("workflow_instances"), T("interactions"), T("workflow_templates"), T("workflow_stage_instances"), T("workflow_template_stages"), T("workflow_transition_history"))
    if await db.scalar(select(wi.c.id).where(wi.c.interaction_id == interaction_id)):
        raise HTTPException(409, "У взаимодействия уже существует активный workflow", headers={"X-Error-Code": "WORKFLOW_ALREADY_STARTED"})
    template = (await db.execute(select(wt).where(wt.c.id == payload.template_id))).mappings().first()
    if not template:
        raise HTTPException(404, "Workflow template not found")
    interaction = (await db.execute(select(i).where(i.c.id == interaction_id))).mappings().one()
    # A workflow instance snapshots the template version and all stages. Template edits later are independent.
    instance = (await db.execute(insert(wi).values(interaction_id=interaction_id, template_id=payload.template_id, template_version=template["version"]).returning(wi))).mappings().one()
    source = (await db.execute(select(ts).where(ts.c.template_id == payload.template_id).order_by(ts.c.position))).mappings().all()
    if not source:
        raise HTTPException(409, "Workflow template has no stages")
    for idx, stage in enumerate(source):
        status = "in_progress" if idx == 0 else "pending"
        await db.execute(insert(stages).values(
            interaction_id=interaction_id,
            template_stage_id=stage["id"],
            position=stage["position"],
            code=stage["code"],
            name=stage["name"],
            status=status,
            responsible_user_id=interaction.get("responsible_user_id") or interaction.get("owner_user_id"),
            is_optional=stage["is_optional"],
        ))
    first = (await db.execute(select(stages.c.id).where(stages.c.interaction_id == interaction_id).order_by(stages.c.position).limit(1))).scalar_one()
    await db.execute(insert(history).values(interaction_id=interaction_id, to_stage_instance_id=first, action="start", user_id=current.id, comment="Workflow started"))
    await db.commit()
    return dict(instance)


@router.get("/interactions/{interaction_id}/workflow")
async def get_workflow(interaction_id: int, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _assert_interaction_access(db, current, interaction_id)
    wi, stages = T("workflow_instances"), T("workflow_stage_instances")
    instance = (await db.execute(select(wi).where(wi.c.interaction_id == interaction_id))).mappings().first()
    stage_rows = (await db.execute(select(stages).where(stages.c.interaction_id == interaction_id).order_by(stages.c.position))).mappings().all()
    return {"instance": dict(instance) if instance else None, "stages": [dict(x) for x in stage_rows]}


# ----------------------------- approval / rollback / branches -----------------------------

@router.post("/workflow-transition-requests", dependencies=[Depends(require_roles("manager", "leader", "admin"))])
async def request_transition(payload: TransitionRequestCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    s, r = T("workflow_stage_instances"), T("workflow_transition_requests")
    stage = (await db.execute(select(s).where(s.c.id == payload.stage_instance_id))).mappings().first()
    if not stage:
        raise HTTPException(404, "Stage not found")
    await _assert_interaction_access(db, current, int(stage["interaction_id"]), write=True)
    if stage["status"] == payload.to_status:
        raise HTTPException(409, "Stage is already in requested status")
    values = dict(interaction_id=stage["interaction_id"], stage_instance_id=stage["id"], target_stage_instance_id=payload.target_stage_instance_id, requested_by=current.id, transition_kind=payload.transition_kind, from_status=stage["status"], to_status=payload.to_status, comment=payload.comment)
    if payload.transition_kind == "rollback" and payload.target_stage_instance_id:
        target = (await db.execute(select(s).where(s.c.id == payload.target_stage_instance_id, s.c.interaction_id == stage["interaction_id"]))).mappings().first()
        if not target:
            raise HTTPException(404, "Rollback target stage not found")
    row = (await db.execute(insert(r).values(**values).returning(r))).mappings().one()
    await db.commit()
    return dict(row)


@router.get("/workflow-transition-requests")
async def list_transition_requests(status: str | None = None, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r, i = T("workflow_transition_requests"), T("interactions")
    stmt = select(r).order_by(r.c.id.desc())
    if status:
        stmt = stmt.where(r.c.status == status)
    if "admin" not in current.roles:
        allowed = await _user_university_ids(db, current)
        if not allowed:
            return []
        stmt = stmt.join(i, i.c.id == r.c.interaction_id).where(i.c.university_id.in_(allowed))
    return [dict(x) for x in (await db.execute(stmt)).mappings().all()]


async def _review(request_id: int, approve: bool, payload: ReviewRequest, current: CurrentUser, db: AsyncSession):
    if not (set(current.roles) & {"leader", "admin"}):
        raise HTTPException(403, "Leader or admin role required")
    r, s, h = T("workflow_transition_requests"), T("workflow_stage_instances"), T("workflow_transition_history")
    req = (await db.execute(select(r).where(r.c.id == request_id))).mappings().first()
    if not req:
        raise HTTPException(404, "Transition request not found")
    if req["status"] != "pending":
        raise HTTPException(409, "Transition request already reviewed")
    await _assert_interaction_access(db, current, int(req["interaction_id"]), write=True)
    new_status = "approved" if approve else "rejected"
    await db.execute(update(r).where(r.c.id == request_id).values(status=new_status, reviewed_by=current.id, reviewed_at=func.now(), review_comment=payload.comment))
    if approve:
        if req["transition_kind"] == "rollback":
            # target_stage_instance_id is encoded in the comment-compatible request payload only in old DBs;
            # for the new rollback endpoint the stage_instance_id is the current stage and the target is stored
            # in a companion row in request metadata when available. See rollback endpoint below.
            target_id = req.get("target_stage_instance_id")
            if target_id is None:
                target_id = await db.scalar(select(s.c.id).where(s.c.interaction_id == req["interaction_id"], s.c.position < (select(s.c.position).where(s.c.id == req["stage_instance_id"]))).order_by(s.c.position.desc()).limit(1))
            target = (await db.execute(select(s).where(s.c.id == target_id, s.c.interaction_id == req["interaction_id"]))).mappings().first() if target_id else None
            if target is None:
                raise HTTPException(409, "Rollback target stage not found")
            await db.execute(update(s).where(s.c.id == req["stage_instance_id"]).values(status="pending"))
            await db.execute(update(s).where(s.c.id == target_id).values(status="in_progress"))
            await db.execute(insert(h).values(interaction_id=req["interaction_id"], from_stage_instance_id=req["stage_instance_id"], to_stage_instance_id=target_id, action="back", user_id=current.id, comment=payload.comment or req["comment"]))
        else:
            target_id = req.get("target_stage_instance_id")
            if target_id is not None:
                target = (await db.execute(select(s).where(s.c.id == target_id, s.c.interaction_id == req["interaction_id"]))).mappings().first()
                if not target:
                    raise HTTPException(409, "Branch target stage not found")
                await db.execute(update(s).where(s.c.id == req["stage_instance_id"]).values(status="done"))
                await db.execute(update(s).where(s.c.id == target_id).values(status="in_progress"))
                await db.execute(insert(h).values(interaction_id=req["interaction_id"], from_stage_instance_id=req["stage_instance_id"], to_stage_instance_id=target_id, action="branch", user_id=current.id, comment=payload.comment or req["comment"]))
            else:
                await db.execute(update(s).where(s.c.id == req["stage_instance_id"]).values(status=req["to_status"]))
                await db.execute(insert(h).values(interaction_id=req["interaction_id"], from_stage_instance_id=req["stage_instance_id"], to_stage_instance_id=req["stage_instance_id"], action="approve", user_id=current.id, comment=payload.comment or req["comment"]))
    else:
        await db.execute(insert(h).values(interaction_id=req["interaction_id"], to_stage_instance_id=req["stage_instance_id"], action="reject", user_id=current.id, comment=payload.comment))
    await db.commit()
    return dict((await db.execute(select(r).where(r.c.id == request_id))).mappings().one())


@router.post("/workflow-transition-requests/{request_id}/approve")
async def approve_transition(request_id: int, payload: ReviewRequest = ReviewRequest(), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _review(request_id, True, payload, current, db)


@router.post("/workflow-transition-requests/{request_id}/reject")
async def reject_transition(request_id: int, payload: ReviewRequest = ReviewRequest(), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _review(request_id, False, payload, current, db)


@router.post("/interactions/{interaction_id}/workflow/rollback", dependencies=[Depends(require_roles("manager", "leader", "admin"))])
async def rollback_workflow(interaction_id: int, payload: WorkflowBackRequest, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _assert_interaction_access(db, current, interaction_id, write=True)
    s, r = T("workflow_stage_instances"), T("workflow_transition_requests")
    current_id = payload.current_stage_instance_id
    if current_id is None:
        current_id = await db.scalar(select(s.c.id).where(s.c.interaction_id == interaction_id, s.c.status == "in_progress").order_by(s.c.position.desc()).limit(1))
    current_stage = (await db.execute(select(s).where(s.c.id == current_id, s.c.interaction_id == interaction_id))).mappings().first()
    target = (await db.execute(select(s).where(s.c.id == payload.target_stage_instance_id, s.c.interaction_id == interaction_id))).mappings().first()
    if not current_stage or not target:
        raise HTTPException(404, "Workflow stage not found")
    if target["position"] >= current_stage["position"]:
        raise HTTPException(422, "Rollback target must be a previous stage")
    # Store target in the request comment in a backwards-compatible textual form; approval is still atomic.
    row = (await db.execute(insert(r).values(interaction_id=interaction_id, stage_instance_id=current_stage["id"], target_stage_instance_id=target["id"], requested_by=current.id, transition_kind="rollback", from_status=current_stage["status"], to_status="pending", comment=payload.reason).returning(r))).mappings().one()
    await db.commit()
    return dict(row)


@router.post("/interactions/{interaction_id}/workflow/transition", dependencies=[Depends(require_roles("manager", "leader", "admin"))])
async def branch_transition(interaction_id: int, payload: WorkflowBranchRequest, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _assert_interaction_access(db, current, interaction_id, write=True)
    s = T("workflow_stage_instances")
    source = (await db.execute(select(s).where(s.c.id == payload.from_stage_instance_id, s.c.interaction_id == interaction_id))).mappings().first()
    target = (await db.execute(select(s).where(s.c.id == payload.to_stage_instance_id, s.c.interaction_id == interaction_id))).mappings().first()
    if not source or not target:
        raise HTTPException(404, "Workflow stage not found")
    wi = T("workflow_instances")
    instance = (await db.execute(select(wi).where(wi.c.interaction_id == interaction_id))).mappings().first()
    if not instance:
        raise HTTPException(409, "Workflow has not been started")
    tr = T("workflow_template_transitions")
    allowed = await db.scalar(select(tr.c.id).where(tr.c.template_id == instance["template_id"], tr.c.from_stage_id == source["template_stage_id"], tr.c.to_stage_id == target["template_stage_id"]))
    if allowed is None:
        raise HTTPException(409, "Workflow branch is not allowed by the template")
    r = T("workflow_transition_requests")
    row = (await db.execute(insert(r).values(interaction_id=interaction_id, stage_instance_id=source["id"], target_stage_instance_id=target["id"], requested_by=current.id, transition_kind="status_change", from_status=source["status"], to_status="done", comment=payload.reason))).mappings().one()
    await db.commit()
    return dict(row)


@router.get("/interactions/{interaction_id}/workflow/history")
async def workflow_history(interaction_id: int, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _assert_interaction_access(db, current, interaction_id)
    h = T("workflow_transition_history")
    rows = (await db.execute(select(h).where(h.c.interaction_id == interaction_id).order_by(h.c.created_at, h.c.id))).mappings().all()
    return [dict(x) for x in rows]


@router.get("/workflow-templates/{template_id}/transitions")
async def list_template_transitions(template_id: int, db: AsyncSession = Depends(get_db)):
    t = T("workflow_template_transitions")
    return [dict(x) for x in (await db.execute(select(t).where(t.c.template_id == template_id).order_by(t.c.id))).mappings().all()]


@router.post("/workflow-templates/{template_id}/transitions", dependencies=[Depends(require_roles("admin"))])
async def add_template_transition(template_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    t = T("workflow_template_transitions")
    values = {k: v for k, v in payload.items() if k in {"from_stage_id", "to_stage_id", "condition_code", "label"}}
    row = (await db.execute(insert(t).values(template_id=template_id, **values).returning(t))).mappings().one()
    await db.commit()
    return dict(row)


@router.patch("/workflow-template-transitions/{transition_id}", dependencies=[Depends(require_roles("admin"))])
async def update_template_transition(transition_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    t = T("workflow_template_transitions")
    values = {k: v for k, v in payload.items() if k in {"from_stage_id", "to_stage_id", "condition_code", "label"}}
    row = (await db.execute(update(t).where(t.c.id == transition_id).values(**values).returning(t))).mappings().first()
    if not row:
        raise HTTPException(404, "Workflow template transition not found")
    await db.commit()
    return dict(row)


@router.delete("/workflow-template-transitions/{transition_id}", status_code=204, dependencies=[Depends(require_roles("admin"))])
async def delete_template_transition(transition_id: int, db: AsyncSession = Depends(get_db)):
    t = T("workflow_template_transitions")
    result = await db.execute(delete(t).where(t.c.id == transition_id))
    if result.rowcount == 0:
        raise HTTPException(404, "Workflow template transition not found")
    await db.commit()


# ----------------------------- students -----------------------------

@router.get("/students", response_model=list[StudentResponse], dependencies=[Depends(require_roles("admin", "manager", "leader", "teacher"))])
async def list_students(university_id: int | None = None, program_id: int | None = None, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    t = T("students")
    stmt = select(t).order_by(t.c.id.desc()).offset(offset).limit(limit)
    allowed = await _user_university_ids(db, current)
    if allowed is not None:
        if not allowed:
            return []
        stmt = stmt.where(t.c.university_id.in_(allowed))
    if university_id is not None:
        stmt = stmt.where(t.c.university_id == university_id)
    if program_id is not None:
        stmt = stmt.where(t.c.program_id == program_id)
    return [dict(x) for x in (await db.execute(stmt)).mappings().all()]


@router.post("/students", response_model=StudentResponse, status_code=201, dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def create_student(payload: StudentCreate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _assert_university_access(db, current, payload.university_id, write=True)
    t = T("students")
    row = (await db.execute(insert(t).values(**payload.model_dump()).returning(t))).mappings().one()
    await db.commit()
    return dict(row)


@router.patch("/students/{student_id}", response_model=StudentResponse, dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def update_student(student_id: int, payload: StudentUpdate, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    t = T("students")
    existing = (await db.execute(select(t).where(t.c.id == student_id))).mappings().first()
    if not existing:
        raise HTTPException(404, "Student not found")
    university_id = int(payload.university_id if payload.university_id is not None else existing["university_id"])
    await _assert_university_access(db, current, university_id, write=True)
    values = payload.model_dump(exclude_unset=True)
    row = (await db.execute(update(t).where(t.c.id == student_id).values(**values).returning(t))).mappings().one()
    await db.commit()
    return dict(row)


@router.delete("/students/{student_id}", status_code=204, dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def delete_student(student_id: int, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    t = T("students")
    existing = (await db.execute(select(t).where(t.c.id == student_id))).mappings().first()
    if not existing:
        raise HTTPException(404, "Student not found")
    await _assert_university_access(db, current, int(existing["university_id"]), write=True)
    await db.execute(delete(t).where(t.c.id == student_id))
    await db.commit()


@router.post("/students/import", dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def import_students(file: UploadFile = File(...), current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await file.read()
    ext = Path(file.filename or "").suffix.lower()
    if ext == ".csv":
        rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    elif ext == ".xlsx":
        from openpyxl import load_workbook
        ws = load_workbook(io.BytesIO(data), read_only=True, data_only=True).active
        vals = list(ws.iter_rows(values_only=True))
        headers = [str(x or "") for x in vals[0]] if vals else []
        rows = [dict(zip(headers, r)) for r in vals[1:]]
    elif ext == ".xls":
        import xlrd
        book = xlrd.open_workbook(file_contents=data)
        sh = book.sheet_by_index(0)
        headers = [str(x) for x in sh.row_values(0)]
        rows = [dict(zip(headers, sh.row_values(i))) for i in range(1, sh.nrows)]
    else:
        raise HTTPException(422, "Supported formats: CSV, XLS, XLSX")
    t = T("students")
    created = updated = skipped = 0
    errors = []
    for n, row in enumerate(rows, 2):
        try:
            email = str(row.get("email") or "").strip()
            full_name = str(row.get("full_name") or row.get("ФИО") or "").strip()
            university_id = int(row.get("university_id"))
            program_raw = row.get("program_id")
            await _assert_university_access(db, current, university_id, write=True)
            if not email or "@" not in email:
                raise ValueError("Некорректный email")
            if not full_name:
                raise ValueError("Не указано ФИО")
            program_id = int(program_raw) if program_raw not in (None, "",) else None
            existing = (await db.execute(select(t).where(t.c.email == email, t.c.university_id == university_id))).mappings().first()
            values = dict(university_id=university_id, program_id=program_id, full_name=full_name, email=email)
            if existing:
                await db.execute(update(t).where(t.c.id == existing["id"]).values(**values))
                updated += 1
            else:
                await db.execute(insert(t).values(**values))
                created += 1
        except Exception as exc:
            skipped += 1
            errors.append({"row": n, "message": str(exc)})
    await db.commit()
    return {"total": len(rows), "created": created, "updated": updated, "skipped": skipped, "errors": errors}


# ----------------------------- mock integrations -----------------------------

async def _integration_run(db: AsyncSession, current: CurrentUser, source: str, direction: str, *, total: int = 0, created: int = 0, updated_count: int = 0, skipped: int = 0, error: str | None = None):
    run = T("integration_runs")
    status = "failed" if error else "success"
    row = (await db.execute(insert(run).values(source=source, direction=direction, status=status, records_total=total, records_created=created, records_updated=updated_count, records_skipped=skipped, error_message=error, started_by=current.id, finished_at=func.now()).returning(run))).mappings().one()
    await db.commit()
    return dict(row)


@router.get("/integrations/lms/preview", dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def lms_preview():
    return {"source": "lms", "records": [{"external_id": "LMS-10015", "full_name": "Иванов Иван Иванович", "email": "ivanov@example.ru", "program_external_id": "DEVOPS-01"}], "total": 124}


@router.post("/integrations/lms/import", dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def lms_import(payload: IntegrationImportRequest, current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    run = await _integration_run(db, current, "lms", "inbound", total=1, created=1)
    return {"created": 1, "updated": 0, "skipped": 0, "errors": [], "run_id": run["id"]}


@router.post("/integrations/lms/export", dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def lms_export(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    run = await _integration_run(db, current, "lms", "outbound")
    return {"source": "lms", "direction": "outbound", "run_id": run["id"], "records": []}


@router.get("/integrations/site/preview", dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def site_preview():
    return {"source": "site", "records": [{"external_id": "APP-8544", "university": "МГТУ им. Баумана", "direction": "DevOps", "program": "DevOps Tools", "applicant_count": 87}]}


@router.post("/integrations/site/import", dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def site_import(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    run = await _integration_run(db, current, "site", "inbound", total=1, created=1)
    return {"created": 1, "updated": 0, "skipped": 0, "errors": [], "run_id": run["id"]}


@router.post("/integrations/site/export", dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def site_export(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    run = await _integration_run(db, current, "site", "outbound")
    return {"source": "site", "direction": "outbound", "run_id": run["id"], "records": []}


@router.get("/integrations/history", dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def integration_history(db: AsyncSession = Depends(get_db)):
    run = T("integration_runs")
    return [dict(x) for x in (await db.execute(select(run).order_by(run.c.id.desc()))).mappings().all()]


@router.get("/integrations/history/{run_id}", dependencies=[Depends(require_roles("admin", "manager", "leader"))])
async def integration_history_one(run_id: int, db: AsyncSession = Depends(get_db)):
    run = T("integration_runs")
    row = (await db.execute(select(run).where(run.c.id == run_id))).mappings().first()
    if not row:
        raise HTTPException(404, "Integration run not found")
    return dict(row)
