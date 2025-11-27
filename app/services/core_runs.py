from __future__ import annotations

from typing import Any, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.models.core_entities import Run, Task, AgentEvent


def create_run(
    session: Session,
    *,
    tenant_id: Any,
    workspace_id: Optional[Any] = None,
    kind: str,
    label: str,
    initiator: str,
    notes: Optional[str] = None,
) -> Run:
    """
    Create a new Run row in the database.

    This helper assumes:
    - The Run model is mapped to the 'runs' table.
    - Defaults for created_at and status are handled by the database.

    Parameters
    ----------
    session : Session
        An existing SQLAlchemy session.
    tenant_id : Any
        UUID (or compatible type) of the tenant.
    workspace_id : Any | None
        UUID (or compatible type) of the workspace, or None.
    kind : str
        Type of run (e.g., 'workflow_execution', 'infra_change').
    label : str
        Human-readable label for the run.
    initiator : str
        Who or what started the run (e.g., 'operator:jensen').
    notes : str | None
        Optional free-form notes.

    Returns
    -------
    Run
        The newly created Run instance, refreshed from the database.
    """
    run = Run(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        kind=kind,
        label=label,
        initiator=initiator,
        notes=notes,
        # status and timestamps rely on DB defaults
    )

    session.add(run)
    session.commit()
    session.refresh(run)

    return run


def create_task(
    session: Session,
    *,
    run_id: Any,
    owner: str,
    title: str,
    payload: Any,
    priority: str = "normal",
    status: str = "pending",
    result_ref: Optional[str] = None,
) -> Task:
    """
    Create a new Task row associated with an existing Run.

    This helper assumes:
    - The Task model is mapped to the 'tasks' table.
    - Defaults for created_at and updated_at are handled by the database.

    Parameters
    ----------
    session : Session
        An existing SQLAlchemy session.
    run_id : Any
        UUID (or compatible type) of the Run this task belongs to.
    owner : str
        Logical owner of the task (e.g., 'platform', 'workflow', 'orchestrator').
    title : str
        Short human-readable title for the task.
    payload : Any
        JSON-serializable structure representing the task brief / context.
    priority : str, default 'normal'
        Priority indicator (e.g., 'low', 'normal', 'high').
    status : str, default 'pending'
        Initial status of the task.
    result_ref : str | None
        Optional reference to a result artifact (path, document ID, etc.).

    Returns
    -------
    Task
        The newly created Task instance, refreshed from the database.
    """
    task = Task(
        run_id=run_id,
        owner=owner,
        title=title,
        payload=payload,
        priority=priority,
        status=status,
        result_ref=result_ref,
        # created_at and updated_at rely on DB defaults
    )

    session.add(task)
    session.commit()
    session.refresh(task)

    return task


def log_agent_event(
    session: Session,
    *,
    run_id: Any,
    actor: str,
    event_type: str,
    summary: str,
    task_id: Optional[Any] = None,
    details: Any = None,
    step: Optional[int] = None,
) -> AgentEvent:
    """
    Create a new AgentEvent row to record what happened during a run/task.

    This helper assumes:
    - The AgentEvent model is mapped to the 'agent_events' table.
    - created_at is handled by the database.

    Parameters
    ----------
    session : Session
        An existing SQLAlchemy session.
    run_id : Any
        UUID (or compatible type) of the Run this event belongs to.
    actor : str
        Who or what produced this event (e.g., 'orchestrator', 'platform',
        'workflow', 'operator:jensen').
    event_type : str
        Logical type of the event (e.g., 'task_created', 'task_routed').
    summary : str
        Short human-readable summary of the event.
    task_id : Any | None
        Optional UUID (or compatible type) of an associated Task.
    details : Any
        Optional JSON-serializable structured details payload.
    step : int | None
        Optional step index within the run/task sequence.

    Returns
    -------
    AgentEvent
        The newly created AgentEvent instance, refreshed from the database.
    """
    event = AgentEvent(
        run_id=run_id,
        task_id=task_id,
        actor=actor,
        event_type=event_type,
        summary=summary,
        details=details,
        step=step,
        # created_at relies on DB default
    )

    session.add(event)
    session.commit()
    session.refresh(event)

    return event


def get_task_by_id(session: Session, task_id: Any) -> Optional[Task]:
    """
    Fetch a Task by its primary key.

    Returns the Task instance if found, otherwise None.
    """
    return session.query(Task).filter(Task.id == task_id).first()


def update_task_status_and_log_event(
    session: Session,
    *,
    task_id: Any,
    new_status: str,
    result_ref: Optional[str] = None,
    actor: str = "orchestrator",
    event_type: str = "task_updated",
    summary: str = "",
    details: Optional[dict] = None,
) -> Tuple[Task, AgentEvent]:
    """
    Update a Task's status (and optional result_ref) and log a corresponding AgentEvent.

    Behavior:
    - Look up the Task by id; if not found, raise ValueError.
    - Set task.status = new_status.
    - If result_ref is provided, set task.result_ref = result_ref.
    - If the Task model has an updated_at column, set it to func.now().
    - Commit and refresh the Task.
    - Use log_agent_event(...) to create an AgentEvent:
      - run_id = task.run_id
      - task_id = task.id
      - actor, event_type from parameters
      - summary from parameter if provided, otherwise default text
      - details from parameter if provided, otherwise a small dict
      - step = None
    - Return (task, event).
    """
    task = get_task_by_id(session, task_id=task_id)
    if task is None:
        raise ValueError(f"Task not found for id={task_id}")

    # Update core fields
    task.status = new_status
    if result_ref is not None:
        task.result_ref = result_ref

    # Update updated_at if present on the model
    if hasattr(task, "updated_at"):
        # This assumes updated_at is a SQLAlchemy Column; assign a SQL expression.
        task.updated_at = func.now()

    session.commit()
    session.refresh(task)

    if not summary:
        summary = f"Task {task.id} status updated to {new_status}"

    default_details = {
        "status": new_status,
        "result_ref": result_ref,
    }
    event_details = details if details is not None else default_details

    event = log_agent_event(
        session,
        run_id=task.run_id,
        task_id=task.id,
        actor=actor,
        event_type=event_type,
        summary=summary,
        details=event_details,
        step=None,
    )

    return task, event
