"""
Minimal WorkflowRunner implementation for Jensen Core AI OS (Phase E8.A).

This module provides a basic workflow execution engine that:
- Executes workflow steps sequentially
- Supports only 'noop' step type in Phase E8.A
- Logs AgentEvents for each step execution
- Does NOT support branching, parallel steps, retries, or external tools

The runner follows the same minimal, DB-backed style as other core services.
"""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.core_entities import AgentEvent
from app.services.core_runs import log_agent_event


class WorkflowRunner:
    """
    Minimal workflow runner that executes steps sequentially.

    This is a Phase E8.A implementation that supports only 'noop' step types.
    Each step execution is logged to the database as an AgentEvent.

    Future phases will add support for:
    - Agent actions
    - Branching logic
    - Parallel execution
    - Retries and error handling
    - External tool integration
    """

    def __init__(self, session: Session):
        """
        Initialize the workflow runner with a database session.

        Parameters
        ----------
        session : Session
            An active SQLAlchemy session for database operations.
        """
        self.session = session
        self.events: list[AgentEvent] = []

    def run(
        self,
        workflow_def: dict[str, Any],
        *,
        run_id: UUID | Any,
        task_id: Optional[UUID | Any] = None,
        actor: str = "workflow_engine",
    ) -> dict[str, Any]:
        """
        Execute a workflow definition sequentially.

        This method:
        1. Iterates through steps in the workflow definition
        2. Executes each step based on its type
        3. Logs an AgentEvent for each step execution
        4. Returns a summary of execution results

        Parameters
        ----------
        workflow_def : dict[str, Any]
            The workflow definition containing 'steps' list.
            Each step should have 'id' and 'type' fields.
        run_id : UUID | Any
            The ID of the Run this workflow belongs to.
        task_id : UUID | Any | None
            Optional Task ID associated with this workflow execution.
        actor : str, default 'workflow_engine'
            The actor name to record in AgentEvents.

        Returns
        -------
        dict[str, Any]
            A summary dict containing:
            - workflow_id: The workflow identifier
            - workflow_name: The workflow name
            - steps_executed: Number of steps successfully executed
            - events: List of event types logged
            - status: 'completed' or 'failed'

        Raises
        ------
        ValueError
            If workflow_def is missing required fields or contains invalid step types.
        """
        workflow_id = workflow_def.get("id", "unknown")
        workflow_name = workflow_def.get("name", "Unnamed Workflow")
        steps = workflow_def.get("steps", [])

        if not isinstance(steps, list):
            raise ValueError("Workflow definition must contain 'steps' list")

        steps_executed = 0
        event_types: list[str] = []

        # Execute each step sequentially
        for step_index, step in enumerate(steps):
            if not isinstance(step, dict):
                raise ValueError(f"Step {step_index} must be a dict")

            step_id = step.get("id", f"step_{step_index}")
            step_type = step.get("type")

            if not step_type:
                raise ValueError(f"Step {step_id} missing 'type' field")

            # Execute the step based on its type
            step_event = self._execute_step(
                step=step,
                step_id=step_id,
                step_type=step_type,
                step_index=step_index,
                run_id=run_id,
                task_id=task_id,
                workflow_id=workflow_id,
                actor=actor,
            )

            self.events.append(step_event)
            event_types.append(step_event.event_type)
            steps_executed += 1

        return {
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "steps_executed": steps_executed,
            "events": event_types,
            "status": "completed",
        }

    def _execute_step(
        self,
        *,
        step: dict[str, Any],
        step_id: str,
        step_type: str,
        step_index: int,
        run_id: UUID | Any,
        task_id: Optional[UUID | Any],
        workflow_id: str,
        actor: str,
    ) -> AgentEvent:
        """
        Execute a single workflow step and log an event.

        For Phase E8.A, only 'noop' step type is supported.

        Parameters
        ----------
        step : dict[str, Any]
            The step definition dict.
        step_id : str
            The step identifier.
        step_type : str
            The step type (e.g., 'noop').
        step_index : int
            The zero-based index of this step in the workflow.
        run_id : UUID | Any
            The Run ID.
        task_id : UUID | Any | None
            Optional Task ID.
        workflow_id : str
            The workflow identifier.
        actor : str
            The actor name for the event.

        Returns
        -------
        AgentEvent
            The logged event for this step execution.

        Raises
        ------
        ValueError
            If step_type is not supported.
        """
        if step_type == "noop":
            return self._execute_noop_step(
                step_id=step_id,
                step_index=step_index,
                run_id=run_id,
                task_id=task_id,
                workflow_id=workflow_id,
                actor=actor,
            )
        else:
            raise ValueError(
                f"Unsupported step type '{step_type}' in Phase E8.A. "
                f"Only 'noop' is supported."
            )

    def _execute_noop_step(
        self,
        *,
        step_id: str,
        step_index: int,
        run_id: UUID | Any,
        task_id: Optional[UUID | Any],
        workflow_id: str,
        actor: str,
    ) -> AgentEvent:
        """
        Execute a 'noop' (no-operation) step.

        This simply logs an event indicating the step was executed.
        No actual work is performed.

        Parameters
        ----------
        step_id : str
            The step identifier.
        step_index : int
            The zero-based index of this step.
        run_id : UUID | Any
            The Run ID.
        task_id : UUID | Any | None
            Optional Task ID.
        workflow_id : str
            The workflow identifier.
        actor : str
            The actor name for the event.

        Returns
        -------
        AgentEvent
            The logged noop event.
        """
        summary = f"Workflow step '{step_id}' (noop) executed"

        event = log_agent_event(
            self.session,
            run_id=run_id,
            task_id=task_id,
            actor=actor,
            event_type="workflow_step_noop",
            summary=summary,
            details={
                "workflow_id": workflow_id,
                "step_id": step_id,
                "step_index": step_index,
                "step_type": "noop",
            },
            step=step_index,
        )

        return event
