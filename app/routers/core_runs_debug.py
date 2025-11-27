from __future__ import annotations

from typing import Generator, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app._db import DB_URL
from app.models.core_entities import Run, Task, AgentEvent


# Local session factory for this router, using the same DB_URL as the app.
# This mirrors the pattern used in scripts but packaged as a FastAPI dependency.
if not DB_URL:
    raise RuntimeError("DATABASE_URL (DB_URL) is not set; cannot use core_runs_debug router")

_engine = create_engine(DB_URL, pool_pre_ping=True, future=True)
_SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB Session and closes it afterwards."""
    session: Session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


router = APIRouter(
    prefix="/internal/core/runs",
    tags=["internal-core"],
)


@router.get("/debug")
def list_recent_runs(
    limit: int = 10,
    session: Session = Depends(get_session),
) -> List[dict]:
    """
    Return a JSON list of the most recent runs for internal debugging.

    - Ordered by created_at DESC
    - Limited by the `limit` query parameter (default 10, max 100)
    """
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be positive")
    if limit > 100:
        limit = 100

    q = (
        session.query(Run)
        .order_by(Run.created_at.desc())
        .limit(limit)
    )

    out: List[dict] = []
    for run in q:
        out.append(
            {
                "id": str(run.id),
                "kind": run.kind,
                "label": run.label,
                "status": run.status,
                "workspace_id": str(run.workspace_id) if getattr(run, "workspace_id", None) else None,
                "initiator": getattr(run, "initiator", None),
                "created_at": run.created_at.isoformat() if getattr(run, "created_at", None) else None,
            }
        )

    return out


@router.get("/{run_id}/tasks")
def list_run_tasks(
    run_id: str,
    session: Session = Depends(get_session),
) -> List[dict]:
    """
    Return a JSON list of tasks for the given run_id.

    - Ordered by created_at ASC if available; otherwise by id ASC.
    - Returns 200 with an empty list if no tasks exist.
    """
    try:
        run_uuid = UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id format")

    q = session.query(Task).filter(Task.run_id == run_uuid)

    # Order by created_at if present, otherwise by id
    order_column = getattr(Task, "created_at", None)
    if order_column is not None:
        q = q.order_by(order_column.asc())
    else:
        q = q.order_by(Task.id.asc())

    tasks = q.all()

    out: List[dict] = []
    for task in tasks:
        created_at = getattr(task, "created_at", None)
        updated_at = getattr(task, "updated_at", None)

        out.append(
            {
                "id": str(task.id),
                "run_id": str(task.run_id),
                "owner": getattr(task, "owner", None),
                "title": getattr(task, "title", None),
                "status": getattr(task, "status", None),
                "priority": getattr(task, "priority", None),
                "result_ref": getattr(task, "result_ref", None),
                "created_at": created_at.isoformat() if created_at is not None else None,
                "updated_at": updated_at.isoformat() if updated_at is not None else None,
            }
        )

    return out


@router.get("/{run_id}/events")
def list_run_events(
    run_id: str,
    session: Session = Depends(get_session),
) -> List[dict]:
    """
    Return a JSON list of agent events for the given run_id.

    - Ordered by created_at ASC if available; otherwise by id ASC.
    - Returns 200 with an empty list if no events exist.
    """
    try:
        run_uuid = UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id format")

    q = session.query(AgentEvent).filter(AgentEvent.run_id == run_uuid)

    # Order by created_at if present, otherwise by id
    order_column = getattr(AgentEvent, "created_at", None)
    if order_column is not None:
        q = q.order_by(order_column.asc())
    else:
        q = q.order_by(AgentEvent.id.asc())

    events = q.all()

    out: List[dict] = []
    for event in events:
        created_at = getattr(event, "created_at", None)

        out.append(
            {
                "id": str(event.id),
                "run_id": str(event.run_id),
                "task_id": str(event.task_id) if getattr(event, "task_id", None) else None,
                "actor": getattr(event, "actor", None),
                "event_type": getattr(event, "event_type", None),
                "summary": getattr(event, "summary", None),
                "step": getattr(event, "step", None),
                "created_at": created_at.isoformat() if created_at is not None else None,
            }
        )

    return out