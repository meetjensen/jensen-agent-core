"""
Phase G: Compatibility Framework

Provides tools for workflow version compatibility checking and structural hashing.
"""
from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Dict


class TemplateStatus(str, Enum):
    """Status of a workflow template version."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DRAFT = "draft"


class CompatibilityLevel(str, Enum):
    """
    Semantic compatibility level for workflow versions.

    - BREAKING: Changes that break backward compatibility (major version bump)
    - ADDITIVE: Backward-compatible additions (minor version bump)
    - INTERNAL: Internal implementation changes, no API changes (patch bump)
    - UNKNOWN: Compatibility level not yet determined
    """

    BREAKING = "breaking"
    ADDITIVE = "additive"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


def compute_structural_hash(definition: Dict[str, Any]) -> str:
    """
    Compute a structural hash of a workflow definition.

    This hash is used to detect changes in the workflow structure.
    It focuses on the workflow steps, types, and connections, ignoring
    metadata like descriptions, timestamps, etc.

    Parameters
    ----------
    definition : dict
        The workflow definition (WorkflowDefinition as dict)

    Returns
    -------
    str
        SHA256 hash of the structural elements (first 16 chars)
    """
    # Extract structural elements (ignore metadata, descriptions, etc.)
    structural_parts = {
        "steps": [],
    }

    # Extract step structure
    steps = definition.get("steps", [])
    for step in steps:
        step_structure = {
            "id": step.get("id"),
            "type": step.get("type"),
            # Include input/output keys but not values
            "input_keys": sorted(step.get("inputs", {}).keys()),
            "output_keys": sorted(step.get("outputs", {}).keys()),
        }
        structural_parts["steps"].append(step_structure)

    # Sort steps by ID for consistent hashing
    structural_parts["steps"] = sorted(
        structural_parts["steps"],
        key=lambda x: x.get("id", ""),
    )

    # Serialize to JSON and compute hash
    json_str = json.dumps(structural_parts, sort_keys=True)
    hash_full = hashlib.sha256(json_str.encode()).hexdigest()

    # Return first 16 characters for brevity
    return hash_full[:16]


def determine_compatibility_level(
    old_definition: Dict[str, Any],
    new_definition: Dict[str, Any],
) -> CompatibilityLevel:
    """
    Determine the compatibility level between two workflow definitions.

    Logic:
    - If structural hashes differ → check what changed
    - If step types changed or steps removed → BREAKING
    - If new steps added or new outputs → ADDITIVE
    - If only metadata changed → INTERNAL

    Parameters
    ----------
    old_definition : dict
        The previous workflow definition
    new_definition : dict
        The new workflow definition

    Returns
    -------
    CompatibilityLevel
        The compatibility level (BREAKING, ADDITIVE, or INTERNAL)
    """
    old_hash = compute_structural_hash(old_definition)
    new_hash = compute_structural_hash(new_definition)

    # If hashes are the same, it's an internal change only
    if old_hash == new_hash:
        return CompatibilityLevel.INTERNAL

    # Extract step information
    old_steps = {s.get("id"): s for s in old_definition.get("steps", [])}
    new_steps = {s.get("id"): s for s in new_definition.get("steps", [])}

    old_step_ids = set(old_steps.keys())
    new_step_ids = set(new_steps.keys())

    # Check for removed steps (BREAKING)
    if old_step_ids - new_step_ids:
        return CompatibilityLevel.BREAKING

    # Check for changed step types (BREAKING)
    for step_id in old_step_ids & new_step_ids:
        old_type = old_steps[step_id].get("type")
        new_type = new_steps[step_id].get("type")
        if old_type != new_type:
            return CompatibilityLevel.BREAKING

    # Check for removed outputs (BREAKING)
    for step_id in old_step_ids & new_step_ids:
        old_outputs = set(old_steps[step_id].get("outputs", {}).keys())
        new_outputs = set(new_steps[step_id].get("outputs", {}).keys())
        if old_outputs - new_outputs:  # outputs were removed
            return CompatibilityLevel.BREAKING

    # If we reach here, changes are additive (new steps or new outputs)
    if new_step_ids - old_step_ids:  # new steps added
        return CompatibilityLevel.ADDITIVE

    # Check for new outputs (ADDITIVE)
    for step_id in old_step_ids & new_step_ids:
        old_outputs = set(old_steps[step_id].get("outputs", {}).keys())
        new_outputs = set(new_steps[step_id].get("outputs", {}).keys())
        if new_outputs - old_outputs:  # new outputs added
            return CompatibilityLevel.ADDITIVE

    # Default to INTERNAL if we can't determine
    return CompatibilityLevel.INTERNAL
