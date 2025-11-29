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
