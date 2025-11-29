"""
Minimal PlatformEngine implementation for Jensen Core AI OS.

This module provides a stub platform engine that:
- Consumes pending platform-owned tasks from the database
- Creates stub AgentEvents to record platform task handling
- Does NOT execute real platform operations (that's for future phases)

The engine follows the same minimal, DB-backed style as other core services.
"""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.core_entities import AgentEvent, Task
from app.services.core_runs import log_agent_event, update_task_status_and_log_event


class DbPlatformEngine:
    """
    Minimal platform engine that handles platform-owned tasks.

    This is a stub implementation. It accepts platform tasks from the database,
    marks them as handled, and creates stub AgentEvents indicating the task
    was "seen" or "handled".

    No actual platform operations occur in this phase.
    """

    def __init__(self, session: Session):
        """
        Initialize the platform engine with a database session.

        Parameters
        ----------
        session : Session
            An active SQLAlchemy session for database operations.
        """
        self.session = session

    def consume_task(
        self,
        *,
        task: Task,
        actor: str = "platform_engine",
    ) -> AgentEvent:
        """
        Consume a platform task and log a stub event.

        This method represents the "handling" of a platform task.
        For this stub implementation, it:
        1. Marks the task as 'in_progress' or 'completed'
        2. Logs a stub AgentEvent of type 'platform_stub_handled'

        No actual platform operations happen.

        Parameters
        ----------
        task : Task
            The Task instance to consume.
        actor : str, default 'platform_engine'
            The actor name to record in the AgentEvent.

        Returns
        -------
        AgentEvent
            The logged stub event.
        """
        # Update task status and log event
        summary = f"Platform task '{task.title}' handled (stub implementation)"

        _, event = update_task_status_and_log_event(
            self.session,
            task_id=task.id,
            new_status="completed",
            actor=actor,
            event_type="platform_stub_handled",
            summary=summary,
            details={
                "task_title": task.title,
                "task_owner": task.owner,
                "phase": "E7",
                "stub": True,
            },
        )

        return event
