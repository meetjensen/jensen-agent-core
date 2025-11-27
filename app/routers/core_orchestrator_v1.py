from __future__ import annotations

from typing import Generator, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app._db import DB_URL
from app.models.core_entities import Tenant, Workspace, Run, Task, AgentEvent
from app.services.core_runs import (
    create_run,
    create_task,
    log_agent_event,
    update_task_status_and_log_event,
)


# Local session factory for this router, using the same DB_URL as the app.
if not DB_URL:
    raise RuntimeError("DATABASE_URL (DB_URL) is not set; cannot use core_orchestrator_v1 router")

_engine = create_engine(DB_URL, pool_pre_ping=True, future=True)
_SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB Session and closes it afterwards."""
    session: Session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


class OrchestratorRunRequest(BaseModel):
    kind: str = "operator_request"
    label: str
    notes: Optional[str] = None
    workspace_name: str = "Core Orchestrator Workspace"
    workspace_category: str = "test"


class OrchestratorRunResponse(BaseModel):
    tenant_id: str
    workspace_id: str
    run_id: str
    task_id: str
    event_id: str
    tenant_created: bool
    workspace_created: bool


class OrchestratorTaskUpdateRequest(BaseModel):
    task_id: UUID
    status: str
    result_ref: Optional[str] = None
    notes: Optional[str] = None


class OrchestratorTaskUpdateResponse(BaseModel):
    task_id: str
    run_id: str
    event_id: str
    status: str
    result_ref: Optional[str] = None


class OrchestratorRunDebugTask(BaseModel):
    id: str
    owner: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    result_ref: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class OrchestratorRunDebugEvent(BaseModel):
    id: str
    task_id: Optional[str] = None
    actor: Optional[str] = None
    event_type: Optional[str] = None
    summary: Optional[str] = None
    step: Optional[int] = None
    created_at: Optional[str] = None


class OrchestratorRunDebug(BaseModel):
    run_id: str
    kind: Optional[str] = None
    label: Optional[str] = None
    status: Optional[str] = None
    workspace_id: Optional[str] = None
    initiator: Optional[str] = None
    created_at: Optional[str] = None
    tasks: list[OrchestratorRunDebugTask]
    events: list[OrchestratorRunDebugEvent]


router = APIRouter(
    prefix="/internal/core/orchestrator",
    tags=["internal-core"],
)


def _get_or_create_tenant(session: Session, name: str = "Jensen") -> tuple[Tenant, bool]:
    tenant = session.query(Tenant).filter(Tenant.name == name).first()
    created = False

    if tenant is None:
        tenant = Tenant(
            name=name,
            type="internal",
            status="active",
        )
        session.add(tenant)
        session.commit()
        session.refresh(tenant)
        created = True

    return tenant, created


def _get_or_create_workspace(
    session: Session,
    tenant: Tenant,
    name: str,
    category: str,
) -> tuple[Workspace, bool]:
    workspace = (
        session.query(Workspace)
        .filter(
            Workspace.tenant_id == tenant.id,
            Workspace.name == name,
        )
        .first()
    )
    created = False

    if workspace is None:
        workspace = Workspace(
            tenant_id=tenant.id,
            name=name,
            category=category,
            config_ref={},
        )
        session.add(workspace)
        session.commit()
        session.refresh(workspace)
        created = True

    return workspace, created


@router.post("/run", response_model=OrchestratorRunResponse)
def create_orchestrator_run(
    payload: OrchestratorRunRequest,
    session: Session = Depends(get_session),
) -> OrchestratorRunResponse:
    """
    Minimal Orchestrator v1 endpoint:

    - Ensures Tenant 'Jensen' exists.
    - Ensures a Workspace exists for that tenant (default 'Core Orchestrator Workspace').
    - Creates a Run, Task, and AgentEvent using the core_runs helpers.
    - Returns their IDs and whether tenant/workspace were newly created.
    """
    tenant, tenant_created = _get_or_create_tenant(session, name="Jensen")

    workspace, workspace_created = _get_or_create_workspace(
        session,
        tenant=tenant,
        name=payload.workspace_name,
        category=payload.workspace_category,
    )

    run = create_run(
        session,
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        kind=payload.kind,
        label=payload.label,
        initiator="operator:jensen",
        notes=payload.notes or "",
    )

    task = create_task(
        session,
        run_id=run.id,
        owner="orchestrator",
        title=payload.label,
        payload={
            "kind": payload.kind,
            "notes": payload.notes,
        },
        priority="normal",
        status="pending",
        result_ref=None,
    )

    event = log_agent_event(
        session,
        run_id=run.id,
        task_id=task.id,
        actor="orchestrator",
        event_type="run_created",
        summary=payload.label,
        details={
            "kind": payload.kind,
            "notes": payload.notes,
        },
        step=1,
    )

    return OrchestratorRunResponse(
        tenant_id=str(tenant.id),
        workspace_id=str(workspace.id),
        run_id=str(run.id),
        task_id=str(task.id),
        event_id=str(event.id),
        tenant_created=tenant_created,
        workspace_created=workspace_created,
    )


@router.post("/task/update", response_model=OrchestratorTaskUpdateResponse)
def update_orchestrator_task(
    payload: OrchestratorTaskUpdateRequest,
    session: Session = Depends(get_session),
) -> OrchestratorTaskUpdateResponse:
    """
    Minimal Orchestrator task update endpoint:

    - Updates a Task's status and optional result_ref.
    - Logs a corresponding AgentEvent.
    - Returns the updated Task and new event IDs.
    """
    try:
        task, event = update_task_status_and_log_event(
            session,
            task_id=payload.task_id,
            new_status=payload.status,
            result_ref=payload.result_ref,
            actor="orchestrator",
            event_type="task_updated",
            summary=payload.notes or "",
            details={
                "notes": payload.notes,
                "new_status": payload.status,
                "result_ref": payload.result_ref,
            },
        )
    except ValueError as exc:
        # Task not found
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return OrchestratorTaskUpdateResponse(
        task_id=str(task.id),
        run_id=str(task.run_id),
        event_id=str(event.id),
        status=task.status,
        result_ref=task.result_ref,
    )


def _build_run_debug_payload(
    session: Session,
    run: Run,
) -> OrchestratorRunDebug:
    # Load tasks for this run
    tasks_q = session.query(Task).filter(Task.run_id == run.id)
    tasks_order_column = getattr(Task, "created_at", None)
    if tasks_order_column is not None:
        tasks_q = tasks_q.order_by(tasks_order_column.asc())
    else:
        tasks_q = tasks_q.order_by(Task.id.asc())
    tasks = tasks_q.all()

    # Load events for this run
    events_q = session.query(AgentEvent).filter(AgentEvent.run_id == run.id)
    events_order_column = getattr(AgentEvent, "created_at", None)
    if events_order_column is not None:
        events_q = events_q.order_by(events_order_column.asc())
    else:
        events_q = events_q.order_by(AgentEvent.id.asc())
    events = events_q.all()

    task_items: list[OrchestratorRunDebugTask] = []
    for t in tasks:
        created_at = getattr(t, "created_at", None)
        updated_at = getattr(t, "updated_at", None)
        task_items.append(
            OrchestratorRunDebugTask(
                id=str(t.id),
                owner=getattr(t, "owner", None),
                title=getattr(t, "title", None),
                status=getattr(t, "status", None),
                priority=getattr(t, "priority", None),
                result_ref=getattr(t, "result_ref", None),
                created_at=created_at.isoformat() if created_at is not None else None,
                updated_at=updated_at.isoformat() if updated_at is not None else None,
            )
        )

    event_items: list[OrchestratorRunDebugEvent] = []
    for ev in events:
        created_at = getattr(ev, "created_at", None)
        event_items.append(
            OrchestratorRunDebugEvent(
                id=str(ev.id),
                task_id=str(ev.task_id) if getattr(ev, "task_id", None) else None,
                actor=getattr(ev, "actor", None),
                event_type=getattr(ev, "event_type", None),
                summary=getattr(ev, "summary", None),
                step=getattr(ev, "step", None),
                created_at=created_at.isoformat() if created_at is not None else None,
            )
        )

    created_at_run = getattr(run, "created_at", None)

    return OrchestratorRunDebug(
        run_id=str(run.id),
        kind=getattr(run, "kind", None),
        label=getattr(run, "label", None),
        status=getattr(run, "status", None),
        workspace_id=str(run.workspace_id) if getattr(run, "workspace_id", None) else None,
        initiator=getattr(run, "initiator", None),
        created_at=created_at_run.isoformat() if created_at_run is not None else None,
        tasks=task_items,
        events=event_items,
    )


@router.get("/run/{run_id}/debug", response_model=OrchestratorRunDebug)
def get_orchestrator_run_debug(
    run_id: str,
    session: Session = Depends(get_session),
) -> OrchestratorRunDebug:
    """
    Return a combined debug view for a single run:

    - Run metadata
    - All Tasks for that run
    - All AgentEvents for that run
    """
    try:
        run_uuid = UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id format")

    run = (
        session.query(Run)
        .filter(Run.id == run_uuid)
        .first()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return _build_run_debug_payload(session, run)