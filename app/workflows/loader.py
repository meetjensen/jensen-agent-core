"""
Minimal workflow loader for Jensen Core AI OS.

This module provides basic functionality to load workflow definitions.
For E6, this is a stub implementation that returns placeholder workflow data.
"""
from __future__ import annotations

from typing import Any, Optional


def load_workflow_definition(workflow_id: str) -> Optional[dict[str, Any]]:
    """
    Load a workflow definition by its identifier.

    For Phase E8.A, this returns a minimal definition with a single noop step.
    In future phases, this will load from a registry, file system, or database.

    Parameters
    ----------
    workflow_id : str
        The identifier of the workflow to load.

    Returns
    -------
    dict[str, Any] | None
        A workflow definition dict if found, otherwise None.
        The dict has keys like 'id', 'name', 'steps', etc.
    """
    # Stub implementation: return a placeholder for any requested workflow_id
    # Updated for Phase E8.A to include a noop step for testing
    return {
        "id": workflow_id,
        "name": f"Workflow {workflow_id}",
        "steps": [
            {
                "id": "step1",
                "type": "noop",
                "description": "A no-operation step for testing",
            }
        ],
        "description": "Stub workflow definition (Phase E8.A)",
    }
