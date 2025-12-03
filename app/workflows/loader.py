"""
Read-only loader for workflow definitions.

- Supports YAML (.yaml/.yml) and JSON (.json) files.
- Validates shape using the WorkflowDefinition schema.
- Returns a WorkflowDefinition instance (no DB / orchestrator / engine usage).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Union

from .schemas import WorkflowDefinition


def load_workflow_dict(data: Mapping[str, Any]) -> WorkflowDefinition:
    """
    Load a workflow definition from an in-memory dictionary.

    This is a thin wrapper that validates the structure using
    the WorkflowDefinition schema.
    """
    return WorkflowDefinition(**data)


def load_workflow_from_file(path: Union[str, Path]) -> WorkflowDefinition:
    """
    Load a workflow definition from a YAML or JSON file.

    This function is read-only:
    - No DB access.
    - No orchestrator calls.
    - No engine calls.

    :param path: Path to a .yaml/.yml or .json file.
    :return:     A validated WorkflowDefinition instance.
    """
    file_path = Path(path)
    suffix = file_path.suffix.lower()

    text = file_path.read_text(encoding="utf-8")

    if suffix in {".yaml", ".yml"}:
        # Import PyYAML lazily so that importing this module does not
        # require PyYAML unless YAML loading is actually used.
        try:
            import yaml  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "PyYAML is required to load YAML workflow definitions. "
                "Install it or use a JSON workflow file instead."
            ) from exc

        data: Dict[str, Any] = yaml.safe_load(text) or {}
    elif suffix == ".json":
        data = json.loads(text)
    else:
        raise ValueError(
            f"Unsupported workflow file extension '{suffix}'. "
            "Use .yaml, .yml, or .json."
        )

    return load_workflow_dict(data)


def load_workflow_definition(
    workflow_id: str, *, base_dir: Union[str, Path] | None = None
):
    """
    Load a workflow definition by ID from the workflow directory.

    Searches recursively for .yaml/.yml/.json workflow files and returns
    the first workflow definition that matches the given ID.

    :param workflow_id: The ID of the workflow to load.
    :param base_dir:    Optional base directory to search. If None, defaults to
                        app/workflows/examples.
    :return:            The workflow definition as a dictionary, or None if not found.
    """
    if base_dir is None:
        # Default to app/workflows/examples
        workflow_dir = Path(__file__).parent / "examples"
    else:
        workflow_dir = Path(base_dir)

    if not workflow_dir.exists():
        return None

    # Recursively search for workflow files
    for ext in ["*.yaml", "*.yml", "*.json"]:
        for file_path in workflow_dir.rglob(ext):
            try:
                wf_def = load_workflow_from_file(file_path)
                if wf_def.id == workflow_id:
                    return wf_def.model_dump()
            except Exception:
                # Skip files that can't be loaded
                continue

    return None


def discover_workflows(*, base_dir: Union[str, Path] | None = None):
    """
    Discover all workflow definitions in the workflow directory.

    Searches recursively for .yaml/.yml/.json workflow files and loads
    each one, returning a list of (WorkflowDefinition, Path) tuples.

    :param base_dir: Optional base directory to search. If None, defaults to
                     app/workflows/examples.
    :return:         List of (WorkflowDefinition, Path) tuples.
    """
    if base_dir is None:
        # Default to app/workflows/examples
        workflow_dir = Path(__file__).parent / "examples"
    else:
        workflow_dir = Path(base_dir)

    if not workflow_dir.exists():
        return []

    results = []
    # Recursively search for workflow files
    for ext in ["*.yaml", "*.yml", "*.json"]:
        for file_path in workflow_dir.rglob(ext):
            try:
                wf_def = load_workflow_from_file(file_path)
                results.append((wf_def, file_path))
            except Exception:
                # Skip files that can't be loaded
                continue

    return results
