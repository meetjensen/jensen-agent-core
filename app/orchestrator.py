"""
Orchestrator for Jensen Core AI OS (Phase E8.B).

This module provides orchestration logic that handles workflow planning tasks.
When a task with owner="workflow" and workflow metadata arrives, the orchestrator
delegates to the workflow engine to create a plan and generate step tasks.
"""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.engines.workflow_engine import DbWorkflowEngine
from app.services.core_runs import update_task_status_and_log_event


def handle_workflow_planning_task(
    session: Session,
    *,
    task_id: UUID | Any,
    run_id: UUID | Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Handle a workflow planning task.

    When a task with owner="workflow" arrives that contains workflow metadata
    (workflow_id and/or workflow_definition), this function:
    1. Creates a DbWorkflowEngine instance
    2. Calls plan_workflow to generate the plan and step tasks
    3. Marks the planning task as completed
    4. Returns a summary including the number of tasks generated

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session for database operations.
    task_id : UUID | Any
        The ID of the planning task to handle.
    run_id : UUID | Any
        The ID of the Run this task belongs to.
    payload : dict[str, Any]
        The task payload, which should contain workflow_id and/or workflow_definition.

    Returns
    -------
    dict[str, Any]
        A summary dict containing:
        - workflow_id: str
        - workflow_name: str
        - step_count: int
        - plan_task_id: str
        - step_task_ids: list[str]
        - status: str

    Raises
    ------
    ValueError
        If the payload doesn't contain workflow_id or workflow_definition.
    """
    # Extract workflow metadata from payload
    workflow_id = payload.get("workflow_id")
    workflow_definition = payload.get("workflow_definition")

    if not workflow_id and not workflow_definition:
        raise ValueError(
            "Task payload must contain 'workflow_id' or 'workflow_definition' "
            "for workflow planning"
        )

    # Create workflow engine and plan the workflow
    engine = DbWorkflowEngine(session)

    plan_summary, step_tasks, event = engine.plan_workflow(
        run_id=run_id,
        workflow_id=workflow_id,
        workflow_definition=workflow_definition,
        actor="orchestrator",
    )

    # Extract step task IDs
    step_task_ids = [str(task.id) for task in step_tasks]

    # Mark the planning task as completed
    summary = (
        f"Workflow '{plan_summary['workflow_name']}' planned: "
        f"{len(step_tasks)} task(s) generated"
    )

    update_task_status_and_log_event(
        session,
        task_id=task_id,
        new_status="completed",
        result_ref=None,
        actor="orchestrator",
        event_type="workflow_planning_completed",
        summary=summary,
        details={
            "workflow_id": plan_summary["workflow_id"],
            "workflow_name": plan_summary["workflow_name"],
            "step_count": len(step_tasks),
            "plan_task_id": plan_summary["plan_task_id"],
            "step_task_ids": step_task_ids,
        },
    )

    # Return the summary
    return {
        "workflow_id": plan_summary["workflow_id"],
        "workflow_name": plan_summary["workflow_name"],
        "step_count": len(step_tasks),
        "plan_task_id": plan_summary["plan_task_id"],
        "step_task_ids": step_task_ids,
        "status": plan_summary["status"],
    }


def process_task(
    session: Session,
    *,
    task_id: UUID | Any,
) -> Optional[dict[str, Any]]:
    """
    Process a single task by routing it to the appropriate handler.

    This is the main entry point for task processing. It examines the task
    and routes it to the appropriate handler based on the task's owner and payload.

    For Phase E8.B, this handles:
    - Tasks with owner="workflow" containing workflow_id/workflow_definition
      -> Delegates to handle_workflow_planning_task

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
