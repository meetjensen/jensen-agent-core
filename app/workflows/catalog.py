"""
Workflow catalog utilities for Jensen Core.

Provides read-only catalog functions to list and retrieve workflow definitions:
- list_workflows(): Returns a list of WorkflowCatalogEntry objects
- get_workflow(): Returns a WorkflowDefinition by ID
"""

from pathlib import Path
from typing import List, Optional

from .schemas import WorkflowDefinition, WorkflowCatalogEntry
from .loader import discover_workflows, load_workflow_definition


def list_workflows(*, base_dir: Optional[Path] = None) -> List[WorkflowCatalogEntry]:
    """
    List all available workflows in the workflow directory.

    Discovers all workflow files and returns a list of catalog entries
    containing metadata about each workflow.

    :param base_dir: Optional base directory to search. If None, defaults to
                     app/workflows/examples.
    :return:         List of WorkflowCatalogEntry objects.
    """
    workflows = discover_workflows(base_dir=base_dir)
    catalog_entries = []

    for wf_def, path in workflows:
        # Extract tags from metadata if available
        tags = None
        if wf_def.metadata and "tags" in wf_def.metadata:
            tags_value = wf_def.metadata["tags"]
            if isinstance(tags_value, list):
                tags = tags_value

        entry = WorkflowCatalogEntry(
            id=wf_def.id,
            name=wf_def.name,
            description=wf_def.description,
            path=str(path),
            tags=tags,
            metadata=wf_def.metadata,
        )
        catalog_entries.append(entry)

    return catalog_entries


def get_workflow(
    workflow_id: str, *, base_dir: Optional[Path] = None
) -> WorkflowDefinition:
    """
    Get a workflow definition by ID.

    Loads and returns the full workflow definition for the given ID.

    :param workflow_id: The ID of the workflow to retrieve.
    :param base_dir:    Optional base directory to search. If None, defaults to
                        app/workflows/examples.
    :return:            The WorkflowDefinition object.
    :raises ValueError: If the workflow ID is not found.
    """
    wf_dict = load_workflow_definition(workflow_id, base_dir=base_dir)

    if wf_dict is None:
        raise ValueError(f"Unknown workflow_id: {workflow_id}")

    return WorkflowDefinition(**wf_dict)
