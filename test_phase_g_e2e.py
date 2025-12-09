#!/usr/bin/env python3
"""
Phase G End-to-End API Tests

Tests the complete Phase G Template Catalog API via HTTP endpoints.
Validates REST API behavior, request/response formats, and integration
with the underlying service layer.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app._db import DB_URL
from app.main import app
from app.models.core_entities import Base


@pytest.fixture(scope="module")
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(scope="module")
def setup_database():
    """Ensure database tables exist before running tests."""
    if not DB_URL:
        pytest.skip("DATABASE_URL not configured")

    engine = create_engine(DB_URL, pool_pre_ping=True, future=True)
    Base.metadata.create_all(engine, checkfirst=True)
    yield
    # Don't drop tables - let them persist for inspection


def test_create_template(test_client, setup_database):
    """Test POST /internal/templates/ - Create a new template."""
    response = test_client.post(
        "/internal/templates/",
        json={
            "template_key": "test-e2e-workflow",
            "name": "E2E Test Workflow",
            "description": "End-to-end test template",
            "owner": "test_e2e",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["template_key"] == "test-e2e-workflow"
    assert data["name"] == "E2E Test Workflow"
    assert data["owner"] == "test_e2e"
    assert "id" in data
    assert "created_at" in data


def test_create_duplicate_template(test_client, setup_database):
    """Test POST /internal/templates/ - Reject duplicate template_key."""
    # Try to create the same template again
    response = test_client.post(
        "/internal/templates/",
        json={
            "template_key": "test-e2e-workflow",
            "name": "Duplicate Template",
            "owner": "test_e2e",
        },
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_list_templates(test_client, setup_database):
    """Test GET /internal/templates/ - List all templates."""
    response = test_client.get("/internal/templates/")

    assert response.status_code == 200
    data = response.json()
    assert "templates" in data
    assert "total" in data
    assert data["total"] >= 1

    # Find our test template
    template_keys = [t["template_key"] for t in data["templates"]]
    assert "test-e2e-workflow" in template_keys


def test_get_template(test_client, setup_database):
    """Test GET /internal/templates/{template_key} - Get specific template."""
    response = test_client.get("/internal/templates/test-e2e-workflow")

    assert response.status_code == 200
    data = response.json()
    assert data["template_key"] == "test-e2e-workflow"
    assert data["name"] == "E2E Test Workflow"


def test_get_nonexistent_template(test_client, setup_database):
    """Test GET /internal/templates/{template_key} - 404 for missing template."""
    response = test_client.get("/internal/templates/does-not-exist")

    assert response.status_code == 404
    assert response.status_code == 404  # Template not found


def test_create_version_1_0(test_client, setup_database):
    """Test POST /internal/templates/versions - Create version 1.0 (draft)."""
    response = test_client.post(
        "/internal/templates/versions",
        json={
            "template_key": "test-e2e-workflow",
            "version_major": 1,
            "version_minor": 0,
            "definition": {
                "steps": [
                    {
                        "id": "step-1",
                        "type": "noop",
                        "inputs": {"message": "Hello"},
                        "outputs": {},
                    }
                ]
            },
            "status": "draft",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["version_major"] == 1
    assert data["version_minor"] == 0
    assert data["status"] == "draft"
    assert data["compatibility_level"] == "additive"  # First version
    assert "structural_hash" in data


def test_create_version_1_1(test_client, setup_database):
    """Test POST /internal/templates/versions - Create version 1.1 (active, internal)."""
    response = test_client.post(
        "/internal/templates/versions",
        json={
            "template_key": "test-e2e-workflow",
            "version_major": 1,
            "version_minor": 1,
            "definition": {
                "steps": [
                    {
                        "id": "step-1",
                        "type": "noop",
                        "inputs": {"message": "Hello World"},  # Metadata change only
                        "outputs": {},
                    }
                ]
            },
            "status": "active",
            "compatibility_level": "internal",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["version_major"] == 1
    assert data["version_minor"] == 1
    assert data["status"] == "active"
    assert data["compatibility_level"] == "internal"


def test_create_version_1_2(test_client, setup_database):
    """Test POST /internal/templates/versions - Create version 1.2 (active, additive)."""
    response = test_client.post(
        "/internal/templates/versions",
        json={
            "template_key": "test-e2e-workflow",
            "version_major": 1,
            "version_minor": 2,
            "definition": {
                "steps": [
                    {
                        "id": "step-1",
                        "type": "noop",
                        "inputs": {"message": "Hello"},
                        "outputs": {},
                    },
                    {
                        "id": "step-2",  # New step added
                        "type": "noop",
                        "inputs": {"message": "World"},
                        "outputs": {},
                    },
                ]
            },
            "status": "active",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["version_major"] == 1
    assert data["version_minor"] == 2
    assert data["status"] == "active"
    assert data["compatibility_level"] == "additive"  # Auto-determined


def test_create_version_2_0(test_client, setup_database):
    """Test POST /internal/templates/versions - Create version 2.0 (active, breaking)."""
    response = test_client.post(
        "/internal/templates/versions",
        json={
            "template_key": "test-e2e-workflow",
            "version_major": 2,
            "version_minor": 0,
            "definition": {
                "steps": [
                    {
                        "id": "step-1",
                        "type": "different_type",  # Changed type = breaking
                        "inputs": {"message": "Hello"},
                        "outputs": {},
                    }
                ]
            },
            "status": "active",
            "compatibility_level": "breaking",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["version_major"] == 2
    assert data["version_minor"] == 0
    assert data["status"] == "active"
    assert data["compatibility_level"] == "breaking"


def test_create_duplicate_version(test_client, setup_database):
    """Test POST /internal/templates/versions - Reject duplicate version."""
    response = test_client.post(
        "/internal/templates/versions",
        json={
            "template_key": "test-e2e-workflow",
            "version_major": 1,
            "version_minor": 1,
            "definition": {"steps": []},
            "status": "active",
        },
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_list_versions(test_client, setup_database):
    """Test GET /internal/templates/{template_key}/versions - List all versions."""
    response = test_client.get("/internal/templates/test-e2e-workflow/versions")

    assert response.status_code == 200
    data = response.json()
    assert data["template_key"] == "test-e2e-workflow"
    assert "versions" in data
    assert data["total"] == 4  # 1.0, 1.1, 1.2, 2.0

    # Versions should be ordered by version DESC
    versions = data["versions"]
    assert versions[0]["version_major"] == 2
    assert versions[1]["version_major"] == 1 and versions[1]["version_minor"] == 2


def test_list_versions_filtered_by_status(test_client, setup_database):
    """Test GET /internal/templates/{template_key}/versions?status=active - Filter by status."""
    response = test_client.get(
        "/internal/templates/test-e2e-workflow/versions",
        params={"status": "active"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3  # 1.1, 1.2, 2.0 are active

    for version in data["versions"]:
        assert version["status"] == "active"


def test_get_specific_version(test_client, setup_database):
    """Test GET /internal/templates/{template_key}/versions/{major}.{minor} - Get specific version."""
    response = test_client.get("/internal/templates/test-e2e-workflow/versions/1.2")

    assert response.status_code == 200
    data = response.json()
    assert data["version_major"] == 1
    assert data["version_minor"] == 2
    assert data["status"] == "active"
    assert data["compatibility_level"] == "additive"


def test_get_nonexistent_version(test_client, setup_database):
    """Test GET /internal/templates/{template_key}/versions/{major}.{minor} - 404 for missing version."""
    response = test_client.get("/internal/templates/test-e2e-workflow/versions/99.99")

    assert response.status_code == 404
    assert response.status_code == 404  # Template not found


def test_resolve_version_default(test_client, setup_database):
    """Test GET /internal/templates/{template_key}/resolve - Default resolution (latest active, non-breaking)."""
    response = test_client.get("/internal/templates/test-e2e-workflow/resolve")

    assert response.status_code == 200
    data = response.json()

    # Should resolve to 1.2 (latest active, non-breaking)
    assert data["template_key"] == "test-e2e-workflow"
    assert data["version_major"] == 1
    assert data["version_minor"] == 2
    assert data["status"] == "active"
    assert data["compatibility_level"] == "additive"
    assert "resolution_reason" in data


def test_resolve_version_allow_breaking(test_client, setup_database):
    """Test GET /internal/templates/{template_key}/resolve?allow_breaking=true - Include breaking versions."""
    response = test_client.get(
        "/internal/templates/test-e2e-workflow/resolve",
        params={"allow_breaking": True},
    )

    assert response.status_code == 200
    data = response.json()

    # Should resolve to 2.0 (latest active including breaking)
    assert data["version_major"] == 2
    assert data["version_minor"] == 0
    assert data["compatibility_level"] == "breaking"


def test_resolve_version_major_constraint(test_client, setup_database):
    """Test GET /internal/templates/{template_key}/resolve?version_major=1 - Constrain to major version."""
    response = test_client.get(
        "/internal/templates/test-e2e-workflow/resolve",
        params={"version_major": 1},
    )

    assert response.status_code == 200
    data = response.json()

    # Should resolve to 1.2 (latest in v1.x)
    assert data["version_major"] == 1
    assert data["version_minor"] == 2


def test_resolve_version_exact(test_client, setup_database):
    """Test GET /internal/templates/{template_key}/resolve?version_major=1&version_minor=1 - Exact version."""
    response = test_client.get(
        "/internal/templates/test-e2e-workflow/resolve",
        params={"version_major": 1, "version_minor": 1},
    )

    assert response.status_code == 200
    data = response.json()

    # Should resolve to exactly 1.1
    assert data["version_major"] == 1
    assert data["version_minor"] == 1
    assert "Exact version" in data["resolution_reason"]


def test_resolve_version_post(test_client, setup_database):
    """Test POST /internal/templates/{template_key}/resolve - Resolution via POST."""
    response = test_client.post(
        "/internal/templates/test-e2e-workflow/resolve",
        json={
            "template_key": "test-e2e-workflow",
            "allow_breaking": True,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should resolve to 2.0 with allow_breaking=True
    assert data["version_major"] == 2
    assert data["version_minor"] == 0


def test_resolve_nonexistent_template(test_client, setup_database):
    """Test GET /internal/templates/{template_key}/resolve - 404 for missing template."""
    response = test_client.get("/internal/templates/does-not-exist/resolve")

    assert response.status_code == 404
    assert response.status_code == 404  # Template not found


def test_resolve_no_matching_versions(test_client, setup_database):
    """Test resolution when no versions match constraints."""
    # Create a template with only breaking versions
    test_client.post(
        "/internal/templates/",
        json={
            "template_key": "test-breaking-only",
            "name": "Breaking Only Template",
            "owner": "test_e2e",
        },
    )

    test_client.post(
        "/internal/templates/versions",
        json={
            "template_key": "test-breaking-only",
            "version_major": 1,
            "version_minor": 0,
            "definition": {"steps": []},
            "status": "active",
            "compatibility_level": "breaking",
        },
    )

    # Try to resolve without allow_breaking
    response = test_client.get("/internal/templates/test-breaking-only/resolve")

    assert response.status_code == 404
    assert "No suitable version" in response.json()["detail"]


def test_update_version_status(test_client, setup_database):
    """Test PATCH /internal/templates/versions/{version_id}/status - Update version status."""
    # First, get version 1.0 to get its ID
    list_response = test_client.get("/internal/templates/test-e2e-workflow/versions")
    versions = list_response.json()["versions"]
    version_1_0 = next(v for v in versions if v["version_major"] == 1 and v["version_minor"] == 0)
    version_id = version_1_0["id"]

    # Update status from draft to active
    response = test_client.patch(
        f"/internal/templates/versions/{version_id}/status",
        json={"status": "active"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == version_id
    assert data["status"] == "active"

    # Verify the update persisted
    get_response = test_client.get("/internal/templates/test-e2e-workflow/versions/1.0")
    assert get_response.json()["status"] == "active"


def test_api_error_handling(test_client, setup_database):
    """Test API error handling for various invalid requests."""
    # Missing required field
    response = test_client.post(
        "/internal/templates/",
        json={
            "template_key": "incomplete-template",
            # Missing 'name' and 'owner'
        },
    )
    assert response.status_code == 422  # Pydantic validation error

    # Invalid status value
    response = test_client.post(
        "/internal/templates/versions",
        json={
            "template_key": "test-e2e-workflow",
            "version_major": 99,
            "version_minor": 99,
            "definition": {"steps": []},
            "status": "invalid_status",  # Not a valid TemplateStatus
        },
    )
    assert response.status_code == 422


if __name__ == "__main__":
    # Run with: pytest test_phase_g_e2e.py -v
    pytest.main([__file__, "-v"])
