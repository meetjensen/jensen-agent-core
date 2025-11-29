"""
Minimal WorkflowEngine implementation for Jensen Core AI OS (Phase E6).

This module provides a stub workflow engine that:
- Accepts workflow identifiers or pre-loaded workflow definitions
- Creates stub AgentEvents to record workflow planning
- Does NOT execute real workflows (that's for future phases)

The engine follows the same minimal, DB-backed style as other core services.
"""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.core_entities import AgentEvent, Run, Task
from app.services.core_runs import (
    log_agent_event,
    create_workflow_plan,
    create_workflow_step_task,
    log_workflow_planned,
    get_task_by_id,
)
from app.workflows.loader import load_workflow_definition


class DbWorkflowEngine:
    """
    Minimal workflow engine that logs workflow planning events to the database.

    This is a Phase E6 stub implementation. It accepts workflow identifiers or
    definitions, optionally loads them via the workflow loader, and creates
    stub AgentEvents indicating the workflow was "seen" or "planned".

    No actual workflow execution occurs in this phase.
    """

    def __init__(self, session: Session):
        """
        Initialize the workflow engine with a database session.

        Parameters
        ----------
        session : Session
            An active SQLAlchemy session for database operations.
        """
        self.session = session
        self._in_memory_plans: dict[str, Any] = {}

    def plan_workflow(
        self,
        *,
        run_id: UUID | Any,
        workflow_id: Optional[str] = None,
        workflow_definition: Optional[dict[str, Any]] = None,
        actor: str = "workflow_engine",
    ) -> tuple[dict[str, Any], list[Task], AgentEvent]:
        """
        Create a database-backed plan for a workflow and generate step tasks.

        This method represents the "planning" phase of workflow execution.
        For Phase E8.B, it:
        1. Loads or uses the provided workflow definition
        2. Checks if the workflow is already planned (idempotent)
        3. Creates a plan record in the database
        4. Creates tasks for each workflow step
        5. Logs a workflow_planned event

        No actual execution happens here - that's handled elsewhere.

        Parameters
        ----------
        run_id : UUID | Any
            The ID of the Run this workflow belongs to.
        workflow_id : str | None
            Identifier to load the workflow definition via the loader.
            Either this or workflow_definition must be provided.
        workflow_definition : dict[str, Any] | None
            Pre-loaded workflow definition dict.
            If provided, workflow_id is ignored.
        actor : str, default 'workflow_engine'
            The actor name to record in the AgentEvent.

        Returns
        -------
        tuple[dict[str, Any], list[Task], AgentEvent]
            A tuple of (plan_summary, step_tasks, agent_event).
            - plan_summary: Dict with workflow metadata
            - step_tasks: List of created Task instances for each step
            - agent_event: The logged workflow_planned event

        Raises
        ------
        ValueError
            If neither workflow_id nor workflow_definition is provided.
        """
        # Resolve the workflow definition
        if workflow_definition is not None:
            wf_def = workflow_definition
        elif workflow_id is not None:
            wf_def = load_workflow_definition(workflow_id)
            if wf_def is None:
                raise ValueError(f"Could not load workflow: {workflow_id}")
        else:
            raise ValueError(
                "Must provide either workflow_id or workflow_definition"
            )

        wf_id = wf_def.get("id", "unknown")
        wf_name = wf_def.get("name", "Unnamed Workflow")
        steps = wf_def.get("steps", [])
        step_count = len(steps)

        # Check for idempotency: look for existing plan task
        existing_plan = (
            self.session.query(Task)
            .filter(
                Task.run_id == run_id,
                Task.owner == "workflow",
                Task.payload["is_plan"].astext == "true",
                Task.payload["workflow_id"].astext == wf_id,
            )
            .first()
        )

        if existing_plan:
            # Workflow already planned, return existing plan
            existing_step_tasks = (
                self.session.query(Task)
                .filter(
                    Task.run_id == run_id,
                    Task.owner == "workflow",
                    Task.payload["plan_task_id"].astext == str(existing_plan.id),
                )
                .all()
            )

            # Get the original planning event
            existing_event = (
                self.session.query(AgentEvent)
                .filter(
                    AgentEvent.run_id == run_id,
                    AgentEvent.task_id == existing_plan.id,
                    AgentEvent.event_type == "workflow_planned",
                )
                .first()
            )

            plan_summary = {
                "workflow_id": wf_id,
                "workflow_name": wf_name,
                "step_count": step_count,
                "status": "already_planned",
                "run_id": str(run_id),
                "plan_task_id": str(existing_plan.id),
            }

            return plan_summary, existing_step_tasks, existing_event

        # Create the plan record
        plan_task = create_workflow_plan(
            self.session,
            run_id=run_id,
            workflow_id=wf_id,
            workflow_name=wf_name,
            step_count=step_count,
        )

        # Create tasks for each workflow step
        step_tasks = []
        for idx, step_def in enumerate(steps):
            step_task = create_workflow_step_task(
                self.session,
                run_id=run_id,
                workflow_id=wf_id,
                step_definition=step_def,
                step_index=idx,
                plan_task_id=plan_task.id,
            )
            step_tasks.append(step_task)

        # Log the workflow_planned event
        event = log_workflow_planned(
            self.session,
            run_id=run_id,
            workflow_id=wf_id,
            workflow_name=wf_name,
            step_count=step_count,
            plan_task_id=plan_task.id,
            actor=actor,
        )

        # Create plan summary
        plan_summary = {
            "workflow_id": wf_id,
            "workflow_name": wf_name,
            "step_count": step_count,
            "status": "planned",
            "run_id": str(run_id),
            "plan_task_id": str(plan_task.id),
        }

        return plan_summary, step_tasks, event

    def get_plan(self, run_id: UUID | Any, workflow_id: str) -> Optional[dict[str, Any]]:
        """
        Retrieve an in-memory workflow plan if it exists.

        Parameters
        ----------
        run_id : UUID | Any
            The Run ID.
        workflow_id : str
            The workflow identifier.

        Returns
        -------
        dict[str, Any] | None
            The plan dict if found, otherwise None.
        """
        plan_key = f"{run_id}:{workflow_id}"
        return self._in_memory_plans.get(plan_key)

    def list_plans(self) -> list[dict[str, Any]]:
        """
        List all in-memory workflow plans.

        Returns
        -------
        list[dict[str, Any]]
            A list of all currently stored plans.
        """
        return list(self._in_memory_plans.values())
