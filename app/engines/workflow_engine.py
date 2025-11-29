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

from app.models.core_entities import AgentEvent, Run
from app.services.core_runs import log_agent_event
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
    ) -> tuple[dict[str, Any], AgentEvent]:
        """
        Create an in-memory plan for a workflow and log a stub event.

        This method represents the "planning" phase of workflow execution.
        For Phase E6, it:
        1. Loads or uses the provided workflow definition
        2. Creates a minimal in-memory plan structure
        3. Logs a stub AgentEvent of type 'workflow_stub_planned'

        No actual execution happens.

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
        tuple[dict[str, Any], AgentEvent]
            A tuple of (plan_dict, agent_event).
            - plan_dict: The in-memory plan structure
            - agent_event: The logged stub event

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

        # Create a minimal in-memory plan
        plan = {
            "workflow_id": wf_def.get("id", "unknown"),
            "workflow_name": wf_def.get("name", "Unnamed Workflow"),
            "steps": wf_def.get("steps", []),
            "status": "planned",
            "run_id": str(run_id),
        }

        # Store in memory (ephemeral, for this session only)
        plan_key = f"{run_id}:{plan['workflow_id']}"
        self._in_memory_plans[plan_key] = plan

        # Log a stub event to the database
        summary = (
            f"Workflow '{plan['workflow_name']}' planned "
            f"(stub implementation, {len(plan['steps'])} steps)"
        )

        event = log_agent_event(
            self.session,
            run_id=run_id,
            actor=actor,
            event_type="workflow_stub_planned",
            summary=summary,
            details={
                "workflow_id": plan["workflow_id"],
                "workflow_name": plan["workflow_name"],
                "step_count": len(plan["steps"]),
                "phase": "E6",
            },
            task_id=None,
            step=None,
        )

        return plan, event

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
