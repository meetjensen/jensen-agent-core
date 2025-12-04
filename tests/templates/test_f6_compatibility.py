"""
Phase F6: Comprehensive Test Suite for Compatibility Metadata

Tests cover:
- Structural hash stability
- Diff detection
- Breaking vs additive change detection
- Manual override behavior
- Metadata update behavior
- Publishing workflow
- Catalog service functions
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from app.workflows.diff import (
    compute_structural_hash,
    diff_definitions,
    is_likely_breaking_change,
    generate_change_summary,
)
from app.workflows import catalog_service
from app.workflows.catalog_service import (
    DuplicateVersionError,
    VersionNotFoundError,
)


# ==================== Test Fixtures ====================


@pytest.fixture
def sample_workflow_v1():
    """Sample workflow definition v1."""
    return {
        "id": "approval.basic",
        "name": "Basic Approval",
        "description": "Simple approval workflow",
        "steps": [
            {
                "id": "request",
                "type": "approval_request",
                "inputs": {"message": "string"},
                "outputs": {"request_id": "string"},
            },
            {
                "id": "approve",
                "type": "approval_decision",
                "inputs": {"request_id": "string"},
                "outputs": {"approved": "boolean"},
            },
        ],
        "metadata": {
            "inputs": {
                "message": {"type": "string", "required": True},
            },
            "outputs": {
                "approved": {"type": "boolean"},
            },
        },
    }


@pytest.fixture
def sample_workflow_v2_additive(sample_workflow_v1):
    """Sample workflow v2 with additive changes (new step)."""
    workflow = sample_workflow_v1.copy()
    workflow["steps"] = workflow["steps"] + [
        {
            "id": "notify",
            "type": "notification",
            "inputs": {"approved": "boolean"},
            "outputs": {"notification_sent": "boolean"},
        }
    ]
    workflow["metadata"]["outputs"]["notification_sent"] = {"type": "boolean"}
    return workflow


@pytest.fixture
def sample_workflow_v3_breaking(sample_workflow_v1):
    """Sample workflow v3 with breaking changes (removed step)."""
    workflow = sample_workflow_v1.copy()
    # Remove the second step
    workflow["steps"] = [workflow["steps"][0]]
    return workflow


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    session.query = MagicMock()
    session.add = MagicMock()
    session.flush = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    return session


# ==================== Structural Hash Tests ====================


def test_structural_hash_stability(sample_workflow_v1):
    """Test that structural hash is stable for the same definition."""
    hash1 = compute_structural_hash(sample_workflow_v1)
    hash2 = compute_structural_hash(sample_workflow_v1)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 produces 64 hex chars


def test_structural_hash_order_independence():
    """Test that key order doesn't affect hash."""
    workflow1 = {"id": "test", "name": "Test", "steps": []}
    workflow2 = {"name": "Test", "steps": [], "id": "test"}

    hash1 = compute_structural_hash(workflow1)
    hash2 = compute_structural_hash(workflow2)

    assert hash1 == hash2


def test_structural_hash_detects_changes(sample_workflow_v1, sample_workflow_v2_additive):
    """Test that structural hash changes when definition changes."""
    hash1 = compute_structural_hash(sample_workflow_v1)
    hash2 = compute_structural_hash(sample_workflow_v2_additive)

    assert hash1 != hash2


# ==================== Diff Detection Tests ====================


def test_diff_detects_added_steps(sample_workflow_v1, sample_workflow_v2_additive):
    """Test diff detection of added steps."""
    diff = diff_definitions(sample_workflow_v1, sample_workflow_v2_additive)

    assert "notify" in diff["steps_added"]
    assert len(diff["steps_removed"]) == 0
    assert not is_likely_breaking_change(diff)


def test_diff_detects_removed_steps(sample_workflow_v1, sample_workflow_v3_breaking):
    """Test diff detection of removed steps."""
    diff = diff_definitions(sample_workflow_v1, sample_workflow_v3_breaking)

    assert "approve" in diff["steps_removed"]
    assert len(diff["steps_added"]) == 0
    assert is_likely_breaking_change(diff)


def test_diff_detects_modified_steps():
    """Test diff detection of modified steps."""
    workflow1 = {
        "steps": [
            {"id": "step1", "type": "typeA", "inputs": {}}
        ],
        "metadata": {},
    }
    workflow2 = {
        "steps": [
            {"id": "step1", "type": "typeB", "inputs": {}}
        ],
        "metadata": {},
    }

    diff = diff_definitions(workflow1, workflow2)

    assert "step1" in diff["steps_modified"]


def test_diff_detects_input_changes():
    """Test diff detection of input changes."""
    workflow1 = {
        "steps": [],
        "metadata": {
            "inputs": {
                "field1": {"type": "string"},
                "field2": {"type": "number"},
            }
        },
    }
    workflow2 = {
        "steps": [],
        "metadata": {
            "inputs": {
                "field1": {"type": "string"},
                "field3": {"type": "boolean"},
            }
        },
    }

    diff = diff_definitions(workflow1, workflow2)

    assert "field2" in diff["inputs_removed"]
    assert "field3" in diff["inputs_added"]
    assert is_likely_breaking_change(diff)  # Removed input is breaking


def test_diff_detects_output_changes():
    """Test diff detection of output changes."""
    workflow1 = {
        "steps": [],
        "metadata": {
            "outputs": {
                "result": {"type": "string"},
            }
        },
    }
    workflow2 = {
        "steps": [],
        "metadata": {
            "outputs": {
                "result": {"type": "string"},
                "extra": {"type": "number"},
            }
        },
    }

    diff = diff_definitions(workflow1, workflow2)

    assert "extra" in diff["outputs_added"]
    assert len(diff["outputs_removed"]) == 0
    assert not is_likely_breaking_change(diff)  # Added output is not breaking


# ==================== Breaking Change Detection Tests ====================


def test_is_likely_breaking_removed_step():
    """Test that removed step is detected as breaking."""
    diff = {
        "steps_removed": ["step1"],
        "steps_added": [],
        "inputs_removed": [],
        "outputs_removed": [],
    }

    assert is_likely_breaking_change(diff)


def test_is_likely_breaking_removed_input():
    """Test that removed input is detected as breaking."""
    diff = {
        "steps_removed": [],
        "steps_added": [],
        "inputs_removed": ["field1"],
        "outputs_removed": [],
    }

    assert is_likely_breaking_change(diff)


def test_is_likely_breaking_removed_output():
    """Test that removed output is detected as breaking."""
    diff = {
        "steps_removed": [],
        "steps_added": [],
        "inputs_removed": [],
        "outputs_removed": ["result"],
    }

    assert is_likely_breaking_change(diff)


def test_is_not_breaking_additive_changes():
    """Test that additive changes are not breaking."""
    diff = {
        "steps_removed": [],
        "steps_added": ["step2"],
        "inputs_removed": [],
        "outputs_removed": [],
        "inputs_added": ["field2"],
        "outputs_added": ["extra_result"],
    }

    assert not is_likely_breaking_change(diff)


# ==================== Change Summary Tests ====================


def test_generate_change_summary_comprehensive():
    """Test comprehensive change summary generation."""
    diff = {
        "steps_added": ["step2"],
        "steps_removed": ["step1"],
        "steps_modified": [],
        "inputs_added": ["field2"],
        "inputs_removed": [],
        "inputs_modified": [],
        "outputs_added": [],
        "outputs_removed": [],
        "outputs_modified": [],
        "metadata_changed": False,
    }

    summary = generate_change_summary(diff)

    assert "Added 1 step(s)" in summary
    assert "Removed 1 step(s)" in summary
    assert "Added 1 input(s)" in summary


def test_generate_change_summary_no_changes():
    """Test change summary with no changes."""
    diff = {
        "steps_added": [],
        "steps_removed": [],
        "steps_modified": [],
        "inputs_added": [],
        "inputs_removed": [],
        "inputs_modified": [],
        "outputs_added": [],
        "outputs_removed": [],
        "outputs_modified": [],
        "metadata_changed": False,
    }

    summary = generate_change_summary(diff)

    assert summary == "No structural changes detected"


# ==================== Catalog Service Tests ====================


def test_get_or_create_template_creates_new(mock_db_session):
    """Test that get_or_create_template creates a new template."""
    # Mock query to return None (no existing template)
    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=None)
    mock_db_session.query = Mock(return_value=mock_query)

    template = catalog_service.get_or_create_template(
        mock_db_session,
        key="test.workflow",
        name="Test Workflow",
        description="A test workflow",
    )

    assert template.key == "test.workflow"
    assert template.name == "Test Workflow"
    mock_db_session.add.assert_called_once()
    mock_db_session.flush.assert_called_once()


def test_assess_compatibility_first_version(mock_db_session, sample_workflow_v1):
    """Test compatibility assessment for the first version."""
    # Mock no existing version
    mock_query = Mock()
    mock_query.join = Mock(return_value=mock_query)
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.order_by = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=None)
    mock_db_session.query = Mock(return_value=mock_query)

    assessment = catalog_service.assess_compatibility(
        mock_db_session,
        "test.workflow",
        sample_workflow_v1,
    )

    assert assessment["inferred_level"] == "unknown"
    assert assessment["structural_hash"] is not None
    assert assessment["diff"] is None
    assert assessment["change_summary"] == "Initial version"
    assert assessment["previous_version"] is None


def test_assess_compatibility_additive_change(
    mock_db_session, sample_workflow_v1, sample_workflow_v2_additive
):
    """Test compatibility assessment for additive changes."""
    # Mock existing version
    mock_version = Mock()
    mock_version.definition = sample_workflow_v1
    mock_version.version = "1.0.0"

    mock_query = Mock()
    mock_query.join = Mock(return_value=mock_query)
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.order_by = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_version)
    mock_db_session.query = Mock(return_value=mock_query)

    assessment = catalog_service.assess_compatibility(
        mock_db_session,
        "test.workflow",
        sample_workflow_v2_additive,
    )

    assert assessment["inferred_level"] == "additive"
    assert assessment["structural_hash"] is not None
    assert assessment["diff"] is not None
    assert "Added" in assessment["change_summary"]
    assert assessment["previous_version"] == "1.0.0"


def test_assess_compatibility_breaking_change(
    mock_db_session, sample_workflow_v1, sample_workflow_v3_breaking
):
    """Test compatibility assessment for breaking changes."""
    # Mock existing version
    mock_version = Mock()
    mock_version.definition = sample_workflow_v1
    mock_version.version = "1.0.0"

    mock_query = Mock()
    mock_query.join = Mock(return_value=mock_query)
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.order_by = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_version)
    mock_db_session.query = Mock(return_value=mock_query)

    assessment = catalog_service.assess_compatibility(
        mock_db_session,
        "test.workflow",
        sample_workflow_v3_breaking,
    )

    assert assessment["inferred_level"] == "breaking"
    assert assessment["structural_hash"] is not None
    assert assessment["diff"] is not None
    assert "Removed" in assessment["change_summary"]
    assert assessment["previous_version"] == "1.0.0"


# ==================== Manual Override Tests ====================


def test_update_version_metadata_compatibility_level(mock_db_session):
    """Test manual update of compatibility level."""
    from uuid import uuid4

    version_id = uuid4()
    mock_version = Mock()
    mock_version.id = version_id
    mock_version.compatibility_level = "unknown"

    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_version)
    mock_db_session.query = Mock(return_value=mock_query)

    updated = catalog_service.update_version_metadata(
        mock_db_session,
        version_id=version_id,
        compatibility_level="internal",
    )

    assert updated.compatibility_level == "internal"
    mock_db_session.flush.assert_called_once()


def test_update_version_metadata_change_summary(mock_db_session):
    """Test manual update of change summary."""
    from uuid import uuid4

    version_id = uuid4()
    mock_version = Mock()
    mock_version.id = version_id
    mock_version.change_summary = "Auto-generated summary"

    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_version)
    mock_db_session.query = Mock(return_value=mock_query)

    updated = catalog_service.update_version_metadata(
        mock_db_session,
        version_id=version_id,
        change_summary="Manual summary: Fixed bug",
    )

    assert updated.change_summary == "Manual summary: Fixed bug"
    mock_db_session.flush.assert_called_once()


def test_update_version_metadata_not_found(mock_db_session):
    """Test update_version_metadata with non-existent version."""
    from uuid import uuid4

    version_id = uuid4()

    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=None)
    mock_db_session.query = Mock(return_value=mock_query)

    with pytest.raises(VersionNotFoundError):
        catalog_service.update_version_metadata(
            mock_db_session,
            version_id=version_id,
            compatibility_level="breaking",
        )


# ==================== Integration Tests ====================


def test_full_publishing_workflow_with_manual_override(
    mock_db_session, sample_workflow_v1
):
    """Test full publishing workflow with manual compatibility override."""
    # Mock template creation
    mock_template = Mock()
    mock_template.id = "template-id"
    mock_template.key = "test.workflow"

    # Mock queries
    def mock_query_side_effect(model):
        query = Mock()
        query.filter = Mock(return_value=query)
        query.join = Mock(return_value=query)
        query.order_by = Mock(return_value=query)

        # For template queries, return the mock template
        if hasattr(model, "__tablename__") and model.__tablename__ == "workflow_templates":
            query.first = Mock(return_value=mock_template)
        # For version queries (existing version check), return None
        else:
            query.first = Mock(return_value=None)

        return query

    mock_db_session.query = Mock(side_effect=mock_query_side_effect)

    # Publish with manual override
    version = catalog_service.publish_version(
        mock_db_session,
        template_key="test.workflow",
        version="1.0.0",
        definition=sample_workflow_v1,
        name="Test Workflow",
        compatibility_level="internal",  # Manual override
        change_summary="Initial internal release",
        auto_publish=True,
    )

    # Verify manual override took effect
    assert version.compatibility_level == "internal"
    assert version.change_summary == "Initial internal release"
    assert version.status == "published"
    mock_db_session.add.assert_called()
    mock_db_session.flush.assert_called()


# ==================== Edge Cases ====================


def test_structural_hash_with_nested_structures():
    """Test structural hash with deeply nested structures."""
    workflow = {
        "id": "complex",
        "steps": [
            {
                "id": "step1",
                "config": {
                    "nested": {
                        "deeply": {
                            "value": 42,
                            "array": [1, 2, 3],
                        }
                    }
                },
            }
        ],
        "metadata": {},
    }

    hash1 = compute_structural_hash(workflow)
    hash2 = compute_structural_hash(workflow)

    assert hash1 == hash2
    assert len(hash1) == 64


def test_diff_with_empty_definitions():
    """Test diff with empty workflow definitions."""
    workflow1 = {"steps": [], "metadata": {}}
    workflow2 = {"steps": [], "metadata": {}}

    diff = diff_definitions(workflow1, workflow2)

    assert len(diff["steps_added"]) == 0
    assert len(diff["steps_removed"]) == 0
    assert not is_likely_breaking_change(diff)


def test_deprecate_version(mock_db_session):
    """Test version deprecation."""
    from uuid import uuid4

    version_id = uuid4()
    mock_version = Mock()
    mock_version.id = version_id
    mock_version.status = "published"

    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.first = Mock(return_value=mock_version)
    mock_db_session.query = Mock(return_value=mock_query)

    deprecated = catalog_service.deprecate_version(mock_db_session, version_id)

    assert deprecated.status == "deprecated"
    mock_db_session.flush.assert_called_once()
