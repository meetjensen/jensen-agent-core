"""
Platform Engine module for Jensen Core AI OS.

This module defines the abstract PlatformEngine interface and concrete implementations
for processing platform-owned tasks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict

from sqlalchemy.orm import Session

from app.services.core_runs import (
    get_next_pending_platform_task,
    mark_platform_task_handled_and_create_stub_event,
)


class PlatformEngine(ABC):
    """
    Abstract base class for Platform Engine implementations.

    The Platform Engine is responsible for consuming and processing tasks
    that are owned by the platform (as opposed to workflow-owned tasks).
    """

    @abstractmethod
    def process_next_task(self) -> Optional[Dict[str, Any]]:
        """
        Process the next pending platform task.

        This method should:
        1. Find the next unhandled platform task
        2. Process it (mark as handled, create events, etc.)
        3. Return a summary of what was done

        Returns
        -------
        Dict[str, Any] | None
            A dictionary containing summary information about the processed task,
            or None if no tasks were available to process.

            Expected keys in the result dictionary:
            - task_id: UUID of the processed task
            - task_title: Title of the task
            - status: New status of the task
            - event_id: UUID of the created AgentEvent
            - message: Human-readable summary message
        """
        pass


class DbPlatformEngine(PlatformEngine):
    """
    Database-backed concrete implementation of PlatformEngine.

    This implementation uses the core_runs service helpers to:
    - Query for pending platform tasks from the database
    - Mark them as handled
    - Create stub AgentEvent records for audit/tracking

    Parameters
    ----------
    session : Session
        An active SQLAlchemy database session.
    """

    def __init__(self, session: Session):
        """
        Initialize the DbPlatformEngine with a database session.

        Parameters
        ----------
        session : Session
            An active SQLAlchemy database session.
        """
        self.session = session

    def process_next_task(self) -> Optional[Dict[str, Any]]:
        """
        Process the next pending platform task from the database.

        This implementation:
        1. Fetches the next task where owner='platform' and status='pending'
        2. Marks it as 'handled' and creates a stub AgentEvent
        3. Returns a summary dictionary

        Returns
        -------
        Dict[str, Any] | None
            Summary of the processed task, or None if no pending tasks exist.
        """
        # Step 1: Fetch the next pending platform task
        task = get_next_pending_platform_task(self.session)

        if task is None:
            # No pending tasks available
            return None

        # Step 2: Mark task as handled and create stub event
        updated_task, event = mark_platform_task_handled_and_create_stub_event(
            self.session, task
        )

        # Step 3: Build and return summary
        summary = {
            "task_id": str(updated_task.id),
            "task_title": updated_task.title,
            "status": updated_task.status,
            "event_id": str(event.id),
            "message": (
                f"Platform Engine stub handled task {updated_task.id} "
                f"of type '{updated_task.title}'"
            ),
        }

        return summary
