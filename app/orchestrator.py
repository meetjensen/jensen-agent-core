"""
Minimal orchestrator for Jensen Core AI OS (Phase E8.A).

This module provides basic orchestration functionality that:
- Dispatches pending tasks to appropriate engines based on owner
- Supports workflow tasks (owner='workflow')
- Returns execution summaries

The orchestrator follows a simple dispatch pattern and uses core_runs helpers
for all database operations.
"""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.core_entities import Task
from app.engines.workflow_engine import DbWorkflowEngine
from app.services.core_runs import log_agent_event


def orchestrate_single_cycle(
    session: Session,
    *,
    run_id: Optional[UUID | Any] = None,
    actor: str = "orchestrator",
) -> dict[str, Any]:
    """
    Execute a single orchestration cycle.

    This function:
    1. Finds the first pending task (optionally filtered by run_id)
    2. Dispatches the task to the appropriate engine based on owner
    3. Returns a summary of the dispatch/execution

    For Phase E8.A, only workflow tasks (owner='workflow') are supported.

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session for database operations.
    run_id : UUID | Any | None
        Optional Run ID to filter tasks. If None, processes any pending task.
    actor : str, default 'orchestrator'
        The actor name to record in events.

    Returns
    -------
    dict[str, Any]
        A summary dict containing:
        - status: 'dispatched', 'no_tasks', or 'error'
        - owner: The task owner (if dispatched)
        - task_id: The task ID (if dispatched)
        - Additional fields depend on the engine that executed the task

    Examples
    --------
    >>> from app._db import get_session
    >>> session = next(get_session())
    >>> result = orchestrate_single_cycle(session)
    >>> print(result)
    {'status': 'dispatched', 'owner': 'workflow', 'task_id': '...', ...}
    """
    # Find the first pending task
    query = session.query(Task).filter(Task.status == "pending")
    if run_id is not None:
        query = query.filter(Task.run_id == run_id)

    # Order by created_at if available, otherwise by id
    if hasattr(Task, "created_at"):
        query = query.order_by(Task.created_at.asc())
    else:
        query = query.order_by(Task.id.asc())

    task = query.first()

    if task is None:
        return {
            "status": "no_tasks",
            "message": "No pending tasks found",
        }

    # Dispatch based on task owner
    owner = task.owner

    if owner == "workflow":
        return _dispatch_workflow_task(session, task, actor)
    else:
        # For Phase E8.A, only workflow tasks are supported
        # Log an event and return unsupported status
        log_agent_event(
            session,
            run_id=task.run_id,
            task_id=task.id,
            actor=actor,
            event_type="task_dispatch_unsupported",
            summary=f"Task owner '{owner}' not supported in Phase E8.A",
            details={
                "owner": owner,
                "task_id": str(task.id),
            },
            step=None,
        )

        return {
            "status": "error",
            "owner": owner,
            "task_id": str(task.id),
            "message": f"Task owner '{owner}' not supported in Phase E8.A",
        }


def _dispatch_workflow_task(
    session: Session,
    task: Task,
    actor: str,
) -> dict[str, Any]:
    """
    Dispatch a workflow task to the workflow engine.

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session.
    task : Task
        The workflow task to execute.
    actor : str
        The actor name for event logging.

    Returns
    -------
    dict[str, Any]
        A summary dict from the workflow engine, with 'status': 'dispatched'
        added to indicate successful dispatch.
    """
    # Log dispatch event
    log_agent_event(
        session,
        run_id=task.run_id,
        task_id=task.id,
        actor=actor,
        event_type="task_dispatched",
        summary=f"Task dispatched to workflow engine",
        details={
            "owner": task.owner,
            "task_id": str(task.id),
        },
        step=None,
    )

    # Create workflow engine and execute the workflow
    engine = DbWorkflowEngine(session)
    result = engine.run_workflow(task, actor=actor)

    # Add status to indicate successful dispatch
    result["status"] = "dispatched"
    result["owner"] = task.owner

    return result
