"""
Tests for the workflow catalog module.
"""

import json
import pytest
from pathlib import Path

from app.workflows import catalog
from app.workflows.schemas import WorkflowDefinition, WorkflowCatalogEntry


def test_list_workflows_with_temp_dir(tmp_path):
    """
    Test that list_workflows discovers workflow files in a temporary directory.
    """
    # Create a sample workflow file
    workflow_data = {
        "id": "test-workflow",
        "name": "Test Workflow",
        "description": "A test workflow for catalog testing",
        "metadata": {
            "category": "test",
            "tags": ["test", "catalog"]
        },
        "steps": [
            {
                "id": "step-1",
                "type": "test_step",
                "inputs": {"input1": "value1"},
                "outputs": {},
            }
        ],
    }

    workflow_file = tmp_path / "test_workflow.json"
    workflow_file.write_text(json.dumps(workflow_data))

    # List workflows in the temp directory
    workflows = catalog.list_workflows(base_dir=tmp_path)

    # Assert we found our workflow
    assert len(workflows) == 1
    assert isinstance(workflows[0], WorkflowCatalogEntry)
    assert workflows[0].id == "test-workflow"
    assert workflows[0].name == "Test Workflow"
    assert workflows[0].description == "A test workflow for catalog testing"
    assert workflows[0].tags == ["test", "catalog"]
    assert workflows[0].metadata["category"] == "test"


def test_get_workflow_round_trip(tmp_path):
    """
    Test that get_workflow loads and returns a WorkflowDefinition correctly.
    """
    # Create a sample workflow file
    workflow_data = {
        "id": "round-trip-workflow",
        "name": "Round Trip Workflow",
        "description": "Testing round trip loading",
        "metadata": {"version": "1.0"},
        "steps": [
            {
                "id": "step-1",
                "type": "test_step",
                "inputs": {"test": "data"},
                "outputs": {},
            }
        ],
    }

    workflow_file = tmp_path / "round_trip.json"
    workflow_file.write_text(json.dumps(workflow_data))

    # Get the workflow by ID
    workflow = catalog.get_workflow("round-trip-workflow", base_dir=tmp_path)

    # Assert we got the correct workflow
    assert isinstance(workflow, WorkflowDefinition)
    assert workflow.id == "round-trip-workflow"
    assert workflow.name == "Round Trip Workflow"
    assert workflow.description == "Testing round trip loading"
    assert workflow.metadata["version"] == "1.0"
    assert len(workflow.steps) == 1
    assert workflow.steps[0].id == "step-1"


def test_get_workflow_unknown_raises(tmp_path):
    """
    Test that get_workflow raises ValueError for unknown workflow IDs.
    """
    # Empty directory - no workflows
    with pytest.raises(ValueError, match="Unknown workflow_id: nonexistent-workflow"):
        catalog.get_workflow("nonexistent-workflow", base_dir=tmp_path)
