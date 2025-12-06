"""
Phase F6: Structural Diff Utilities for Workflow Templates

This module provides utilities for comparing workflow definitions and detecting
structural changes that may indicate breaking changes.

Key Features:
- Compute stable structural hash of workflow definitions
- Diff two workflow definitions to detect changes
- Identify likely breaking changes based on structural analysis
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Set


def compute_structural_hash(definition: dict) -> str:
    """
    Compute a SHA-256 hash of the normalized workflow definition.

    The definition is normalized by:
    1. Sorting all dictionary keys recursively
    2. Converting to compact JSON (no whitespace)
    3. Hashing the resulting string

    Args:
        definition: The workflow definition dictionary

    Returns:
        Hexadecimal SHA-256 hash string
    """
    # Normalize by sorting keys recursively
    normalized = _normalize_dict(definition)
    # Convert to stable JSON string
    json_str = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    # Compute SHA-256 hash
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def _normalize_dict(obj: Any) -> Any:
    """Recursively normalize a dict by sorting keys."""
    if isinstance(obj, dict):
        return {k: _normalize_dict(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        return [_normalize_dict(item) for item in obj]
    else:
        return obj


def diff_definitions(old: dict, new: dict) -> dict:
    """
    Compare two workflow definitions and return a summary of structural changes.

    The diff focuses on:
    - Steps added/removed/modified
    - Inputs added/removed/modified (with required flag tracking)
    - Outputs added/removed/modified

    Args:
        old: The old workflow definition
        new: The new workflow definition

    Returns:
        A dictionary containing:
        - steps_added: List[str] - IDs of added steps
        - steps_removed: List[str] - IDs of removed steps
        - steps_modified: List[str] - IDs of modified steps
        - inputs_added: List[str] - Keys of added inputs
        - inputs_removed: List[str] - Keys of removed inputs
        - inputs_modified: List[str] - Keys of modified inputs
        - outputs_added: List[str] - Keys of added outputs
        - outputs_removed: List[str] - Keys of removed outputs
        - outputs_modified: List[str] - Keys of modified outputs
        - metadata_changed: bool - Whether top-level metadata changed
    """
    # Extract step information
    old_steps = {step.get("id"): step for step in old.get("steps", [])}
    new_steps = {step.get("id"): step for step in new.get("steps", [])}

    old_step_ids = set(old_steps.keys())
    new_step_ids = set(new_steps.keys())

    steps_added = list(new_step_ids - old_step_ids)
    steps_removed = list(old_step_ids - new_step_ids)
    steps_modified = []

    # Check for modified steps
    for step_id in old_step_ids & new_step_ids:
        if old_steps[step_id] != new_steps[step_id]:
            steps_modified.append(step_id)

    # Extract input/output information from metadata
    old_meta = old.get("metadata", {})
    new_meta = new.get("metadata", {})

    # Compare inputs
    old_inputs = old_meta.get("inputs", {})
    new_inputs = new_meta.get("inputs", {})

    old_input_keys = set(old_inputs.keys())
    new_input_keys = set(new_inputs.keys())

    inputs_added = list(new_input_keys - old_input_keys)
    inputs_removed = list(old_input_keys - new_input_keys)
    inputs_modified = []

    for key in old_input_keys & new_input_keys:
        if old_inputs[key] != new_inputs[key]:
            inputs_modified.append(key)

    # Compare outputs
    old_outputs = old_meta.get("outputs", {})
    new_outputs = new_meta.get("outputs", {})

    old_output_keys = set(old_outputs.keys())
    new_output_keys = set(new_outputs.keys())

    outputs_added = list(new_output_keys - old_output_keys)
    outputs_removed = list(old_output_keys - new_output_keys)
    outputs_modified = []

    for key in old_output_keys & new_output_keys:
        if old_outputs[key] != new_outputs[key]:
            outputs_modified.append(key)

    # Check if metadata changed (excluding inputs/outputs which we already compared)
    old_meta_without_io = {k: v for k, v in old_meta.items() if k not in ["inputs", "outputs"]}
    new_meta_without_io = {k: v for k, v in new_meta.items() if k not in ["inputs", "outputs"]}
    metadata_changed = old_meta_without_io != new_meta_without_io

    return {
        "steps_added": steps_added,
        "steps_removed": steps_removed,
        "steps_modified": steps_modified,
        "inputs_added": inputs_added,
        "inputs_removed": inputs_removed,
        "inputs_modified": inputs_modified,
        "outputs_added": outputs_added,
        "outputs_removed": outputs_removed,
        "outputs_modified": outputs_modified,
        "metadata_changed": metadata_changed,
    }


def is_likely_breaking_change(diff: dict) -> bool:
    """
    Determine if a diff represents a likely breaking change.

    A change is considered likely breaking if:
    - Any steps are removed
    - Any required inputs are removed
    - Any outputs are removed (consumers may depend on them)

    Note: This is a heuristic and may not catch all breaking changes.
    It errs on the side of caution.

    Args:
        diff: The diff dictionary from diff_definitions()

    Returns:
        True if the change is likely breaking, False otherwise
    """
    # Steps removed is always breaking
    if diff.get("steps_removed"):
        return True

    # Inputs removed is likely breaking (may be required by consumers)
    if diff.get("inputs_removed"):
        return True

    # Outputs removed is breaking (consumers may depend on them)
    if diff.get("outputs_removed"):
        return True

    return False


def generate_change_summary(diff: dict) -> str:
    """
    Generate a human-readable summary of changes from a diff.

    Args:
        diff: The diff dictionary from diff_definitions()

    Returns:
        A human-readable string describing the changes
    """
    summary_parts = []

    if diff.get("steps_added"):
        summary_parts.append(f"Added {len(diff['steps_added'])} step(s)")

    if diff.get("steps_removed"):
        summary_parts.append(f"Removed {len(diff['steps_removed'])} step(s)")

    if diff.get("steps_modified"):
        summary_parts.append(f"Modified {len(diff['steps_modified'])} step(s)")

    if diff.get("inputs_added"):
        summary_parts.append(f"Added {len(diff['inputs_added'])} input(s)")

    if diff.get("inputs_removed"):
        summary_parts.append(f"Removed {len(diff['inputs_removed'])} input(s)")

    if diff.get("inputs_modified"):
        summary_parts.append(f"Modified {len(diff['inputs_modified'])} input(s)")

    if diff.get("outputs_added"):
        summary_parts.append(f"Added {len(diff['outputs_added'])} output(s)")

    if diff.get("outputs_removed"):
        summary_parts.append(f"Removed {len(diff['outputs_removed'])} output(s)")

    if diff.get("outputs_modified"):
        summary_parts.append(f"Modified {len(diff['outputs_modified'])} output(s)")

    if diff.get("metadata_changed"):
        summary_parts.append("Metadata changed")

    if not summary_parts:
        return "No structural changes detected"

    return "; ".join(summary_parts)
