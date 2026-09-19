
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, require_roles
from app.db.session import get_db
from app.models.models import metadata
from app.schemas import crud as schemas

router = APIRouter(tags=["crud"])

TABLE_PATHS = {
    "users":"users", "roles":"roles", "permissions":"permissions", "role_permissions":"role-permissions",
    "user_roles":"user-roles", "universities":"universities", "user_university_access":"user-university-access",
    "university_contacts":"university-contacts", "it_directions":"it-directions", "vendors":"vendors",
    "it_products":"it-products", "it_product_directions":"it-product-directions", "programs":"programs",
    "program_products":"program-products", "contracts":"contracts", "licenses":"licenses",
    "workflow_templates":"workflow-templates", "workflow_template_stages":"workflow-template-stages",
    "interactions":"interactions", "workflow_stage_instances":"workflow-stage-instances",
    "stage_transitions":"stage-transitions", "stage_comments":"stage-comments", "files":"files",
    "stage_attachments":"stage-attachments", "tasks":"tasks", "task_attachments":"task-attachments",
    "documents":"documents", "document_versions":"document-versions", "import_jobs":"import-jobs",
    "import_rows":"import-rows", "report_jobs":"report-jobs", "integration_connections":"integration-connections",
    "sync_jobs":"sync-jobs", "activities":"activities", "audit_log":"audit-log", "user_drafts":"user-drafts",
}

ADMIN_TABLES={"users","roles","permissions","role_permissions","user_roles","audit_log","integration_connections","sync_jobs"}


def _model(table: str, suffix: str):
    return getattr(schemas, "".join(x.title() for x in table.split("_")) + suffix)


def _pk_values(table, path_values: tuple[str, ...]):
    pks=list(table.primary_key.columns)
    if len(pks)!=len(path_values):
        raise HTTPException(422, f"Expected {len(pks)} primary-key values")
    result=[]
    for col, value in zip(pks,path_values):
        try: result.append(col.type.python_type(value))
        except Exception: result.append(value)
    return result


def _pk_where(table, values):
    return [c == v for c,v in zip(table.primary_key.columns, values)]

async def _one(db, table, values):
    row=(await db.execute(select(table).where(*_pk_where(table,values)))).mappings().first()
    if row is None: raise HTTPException(404,"Resource not found")
    return dict(row)


def _safe_values(table, data: dict[str,Any]):
    allowed={c.name for c in table.columns}
    return {k:v for k,v in data.items() if k in allowed}


def _dep(table):
    if table in ADMIN_TABLES:
        return Depends(require_roles("admin"))
    return Depends(require_roles("admin","manager","user"))

def _write_dep(table):
    if table in ADMIN_TABLES:
        return Depends(require_roles("admin"))
    return Depends(require_roles("admin","manager"))


def register_table(table_name: str):
    table = metadata.tables[table_name]
    path=TABLE_PATHS[table_name]
    create_model=_model(table_name,"CreateRequest")
    update_model=_model(table_name,"UpdateRequest")
    response_model=_model(table_name,"Response")
    pks=list(table.primary_key.columns)
    read_dep=_dep(table_name); write_dep=_write_dep(table_name)

    async def list_items(db:AsyncSession=Depends(get_db), limit:int=Query(100,ge=1,le=500), offset:int=Query(0,ge=0)):
        result=await db.execute(select(table).offset(offset).limit(limit))
        return [dict(x) for x in result.mappings().all()]
    list_items.__name__=f"list_{table_name}"
    router.add_api_route(f"/{path}",list_items,methods=["GET"],response_model=list[response_model],dependencies=[read_dep],summary=f"List {table_name}")

    async def create_item(payload:create_model, db:AsyncSession=Depends(get_db)):
        values=_safe_values(table,payload.model_dump(exclude_unset=True))
        try:
            row=(await db.execute(insert(table).values(**values).returning(table))).mappings().one()
            await db.commit(); return dict(row)
        except IntegrityError as exc:
            await db.rollback(); raise HTTPException(409,"Resource conflicts with an existing record or constraint") from exc
    create_item.__name__=f"create_{table_name}"
    router.add_api_route(f"/{path}",create_item,methods=["POST"],response_model=response_model,status_code=201,dependencies=[write_dep],summary=f"Create {table_name}")

    if len(pks)==1:
        async def get_item(pk_value:str, db:AsyncSession=Depends(get_db)):
            values=_pk_values(table,(pk_value,)); return await _one(db,table,values)
        get_item.__name__=f"get_{table_name}"
        router.add_api_route(f"/{path}/{{pk_value}}",get_item,methods=["GET"],response_model=response_model,dependencies=[read_dep],summary=f"Get {table_name}")

        async def update_item(pk_value:str,payload:update_model,db:AsyncSession=Depends(get_db)):
            values=_pk_values(table,(pk_value,)); data=_safe_values(table,payload.model_dump(exclude_unset=True))
            if not data: return await _one(db,table,values)
            try:
                await db.execute(update(table).where(*_pk_where(table,values)).values(**data)); await db.commit()
                return await _one(db,table,values)
            except IntegrityError as exc:
                await db.rollback(); raise HTTPException(409,"Resource conflicts with an existing record or constraint") from exc
        update_item.__name__=f"update_{table_name}"
        router.add_api_route(f"/{path}/{{pk_value}}",update_item,methods=["PATCH"],response_model=response_model,dependencies=[write_dep],summary=f"Update {table_name}")

        async def delete_item(pk_value:str,db:AsyncSession=Depends(get_db)):
            values=_pk_values(table,(pk_value,)); result=await db.execute(delete(table).where(*_pk_where(table,values)))
            if result.rowcount==0: raise HTTPException(404,"Resource not found")
            await db.commit()
        delete_item.__name__=f"delete_{table_name}"
        router.add_api_route(f"/{path}/{{pk_value}}",delete_item,methods=["DELETE"],status_code=204,dependencies=[write_dep],summary=f"Delete {table_name}")
    else:
        # Composite-key resources use one path segment per key, e.g. /role-permissions/{role_id}/{permission_id}.
        placeholders="/"+"/".join("{" + c.name + "}" for c in pks)
        async def get_composite(*args, db:AsyncSession=Depends(get_db)):
            values=_pk_values(table,tuple(args)); return await _one(db,table,values)
        # FastAPI cannot infer *args as path params, so generate explicit functions below.
        names=[c.name for c in pks]
        async def get_by_keys(db:AsyncSession=Depends(get_db), **kwargs):
            values=_pk_values(table,tuple(kwargs[n] for n in names)); return await _one(db,table,values)
        # Replace with generated endpoint via exec to keep OpenAPI path parameters explicit.
        namespace={"db":db if False else None}
        params=", ".join(f"{n}: str" for n in names)
        body = f"async def endpoint({params}, db: AsyncSession = Depends(get_db)):\n    values=_pk_values(table, ({', '.join(names)},))\n    return await _one(db, table, values)"
        local={"_pk_values":_pk_values,"_one":_one,"table":table,"get_db":get_db,"AsyncSession":AsyncSession,"Depends":Depends}
        exec(body,local)
        endpoint=local["endpoint"]; endpoint.__name__=f"get_{table_name}"
        router.add_api_route(f"/{path}{placeholders}",endpoint,methods=["GET"],response_model=response_model,dependencies=[read_dep],summary=f"Get {table_name}")

        body2 = f"async def endpoint({params}, payload: update_model, db: AsyncSession = Depends(get_db)):\n    values=_pk_values(table, ({', '.join(names)},))\n    data=_safe_values(table,payload.model_dump(exclude_unset=True))\n    if data:\n        try:\n            await db.execute(update(table).where(*_pk_where(table,values)).values(**data)); await db.commit()\n        except IntegrityError as exc:\n            await db.rollback(); raise HTTPException(409,'Resource conflicts with an existing record or constraint') from exc\n    return await _one(db,table,values)"
        local.update({"update_model":update_model,"_safe_values":_safe_values,"_pk_where":_pk_where,"update":update,"HTTPException":HTTPException,"IntegrityError":IntegrityError})
        exec(body2,local); endpoint=local["endpoint"]; endpoint.__name__=f"update_{table_name}"
        router.add_api_route(f"/{path}{placeholders}",endpoint,methods=["PATCH"],response_model=response_model,dependencies=[write_dep],summary=f"Update {table_name}")

        body3 = f"async def endpoint({params}, db: AsyncSession = Depends(get_db)):\n    values=_pk_values(table, ({', '.join(names)},))\n    result=await db.execute(delete(table).where(*_pk_where(table,values)))\n    if result.rowcount==0: raise HTTPException(404,'Resource not found')\n    await db.commit()"
        local.update({"delete":delete}); exec(body3,local); endpoint=local["endpoint"]; endpoint.__name__=f"delete_{table_name}"
        router.add_api_route(f"/{path}{placeholders}",endpoint,methods=["DELETE"],status_code=204,dependencies=[write_dep],summary=f"Delete {table_name}")

# Called after database reflection in main.py.
def register_all_tables():
    # Routes are registered exactly once after reflection. Specialized resources have dedicated routers.
    if getattr(router,"_rtk_registered",False): return
    specialized={"users","files","stage_comments","import_jobs","import_rows","report_jobs","document_versions"}
    for name in TABLE_PATHS:
        if name in metadata.tables and name not in specialized: register_table(name)
    router._rtk_registered=True
