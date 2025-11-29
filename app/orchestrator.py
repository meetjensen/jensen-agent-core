"""
Minimal Orchestrator Dispatcher for Jensen Core AI OS (Phase E7).

This module provides a single-step orchestrator that:
- Fetches at most ONE pending task from the database
- Dispatches to the appropriate engine based on Task.owner
- Returns a summary of the operation

This is NOT a background scheduler or loop. It's a single-cycle dispatcher
that can be called once to process one task.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.engines.platform_engine import DbPlatformEngine
from app.engines.workflow_engine import DbWorkflowEngine
from app.models.core_entities import Task
from app.services.core_runs import get_next_pending_task


def orchestrate_single_cycle(session: Session) -> Dict[str, Any]:
    """
    Process at most ONE pending task from the database.

    This is the main orchestrator entry point for Phase E7. It:
    1. Fetches the next pending task (any owner)
    2. Determines which engine to use based on Task.owner
    3. Delegates to the appropriate engine method
    4. Returns a summary dict

    If no tasks are pending, returns a summary indicating "no work".

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session for database operations.

    Returns
    -------
    dict
        A summary dictionary with keys:
        - status: "no_work" | "dispatched"
        - task_id: UUID of the task (if dispatched)
        - owner: "platform" | "workflow" (if dispatched)
        - event_type: The type of event logged (if dispatched)
        - summary: Human-readable summary message

    Examples
    --------
    >>> from sqlalchemy.orm import Session
    >>> summary = orchestrate_single_cycle(session)
    >>> print(summary)
    {'status': 'no_work', 'summary': 'No pending tasks found'}

    >>> # When a task exists:
    >>> summary = orchestrate_single_cycle(session)
    >>> print(summary)
    {
        'status': 'dispatched',
        'task_id': '123e4567-e89b-12d3-a456-426614174000',
        'owner': 'platform',
        'event_type': 'platform_stub_handled',
        'summary': 'Dispatched platform task to DbPlatformEngine'
    }
    """
    # Try to fetch ONE pending task (any owner)
    task = get_next_pending_task(session, owner=None)

    if task is None:
        return {
            "status": "no_work",
            "summary": "No pending tasks found",
        }

    # Dispatch based on task owner
    owner = task.owner
    task_id = task.id
    run_id = task.run_id

    if owner == "platform":
        # Use DbPlatformEngine to handle platform tasks
        engine = DbPlatformEngine(session)
        event = engine.consume_task(task=task, actor="platform_engine")

        return {
            "status": "dispatched",
            "task_id": str(task_id),
            "owner": owner,
            "event_type": event.event_type,
            "event_id": str(event.id),
            "summary": f"Dispatched platform task '{task.title}' to DbPlatformEngine",
        }

    elif owner == "workflow":
        # Use DbWorkflowEngine to plan workflow tasks
        engine = DbWorkflowEngine(session)

        # For workflow tasks, we need to extract workflow info from the task payload
        # The payload should contain either workflow_id or workflow_definition
        payload = task.payload or {}
        workflow_id = payload.get("workflow_id")
        workflow_definition = payload.get("workflow_definition")

        plan, event = engine.plan_workflow(
            run_id=run_id,
            workflow_id=workflow_id,
            workflow_definition=workflow_definition,
            actor="workflow_engine",
        )

        # Mark the task as completed after planning
        task.status = "completed"
        session.commit()
        session.refresh(task)

        return {
            "status": "dispatched",
            "task_id": str(task_id),
            "owner": owner,
            "event_type": event.event_type,
            "event_id": str(event.id),
            "workflow_id": plan.get("workflow_id"),
            "summary": f"Dispatched workflow task '{task.title}' to DbWorkflowEngine",
        }

    else:
        # Unknown owner - log warning but don't crash
        return {
            "status": "error",
            "task_id": str(task_id),
            "owner": owner,
            "summary": f"Unknown task owner '{owner}' for task {task_id}",
        }
