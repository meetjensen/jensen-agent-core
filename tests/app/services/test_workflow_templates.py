from __future__ import annotations

import pytest
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.core_entities import Base, WorkflowTemplate
from app.services.workflow_templates import (
    create_workflow_template,
    get_workflow_template_by_id,
    get_workflow_template_by_name,
    list_workflow_templates,
    update_workflow_template,
    delete_workflow_template,
)


@pytest.fixture
def db_session():
    """
    Create an in-memory SQLite database for testing.

    This fixture creates a fresh database for each test, sets up all tables,
    and provides a session. After the test completes, the session is closed
    and all data is discarded.
    """
    # Create an in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")

    # Create all tables
    Base.metadata.create_all(engine)

    # Create a session factory
    SessionLocal = sessionmaker(bind=engine)

    # Create a session
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


def test_create_workflow_template(db_session: Session):
    """Test creating a new workflow template."""
    template = create_workflow_template(
        db_session,
        name="test_workflow",
        description="A test workflow template",
        definition={"steps": [{"type": "action", "name": "step1"}]},
        version="1.0.0",
        status="active",
    )

    assert template.id is not None
    assert template.name == "test_workflow"
    assert template.description == "A test workflow template"
    assert template.definition == {"steps": [{"type": "action", "name": "step1"}]}
    assert template.version == "1.0.0"
    assert template.status == "active"
    assert template.created_at is not None
    assert template.updated_at is not None


def test_get_workflow_template_by_id(db_session: Session):
    """Test fetching a workflow template by ID."""
    # Create a template
    template = create_workflow_template(
        db_session,
        name="test_workflow",
        definition={"steps": []},
    )

    # Fetch it back by ID
    fetched = get_workflow_template_by_id(db_session, template.id)

    assert fetched is not None
    assert fetched.id == template.id
    assert fetched.name == template.name


def test_get_workflow_template_by_id_not_found(db_session: Session):
    """Test fetching a non-existent workflow template returns None."""
    result = get_workflow_template_by_id(db_session, uuid4())
    assert result is None


def test_get_workflow_template_by_name(db_session: Session):
    """Test fetching a workflow template by name."""
    # Create a template
    template = create_workflow_template(
        db_session,
        name="unique_workflow",
        definition={"steps": []},
    )

    # Fetch it back by name
    fetched = get_workflow_template_by_name(db_session, "unique_workflow")

    assert fetched is not None
    assert fetched.id == template.id
    assert fetched.name == "unique_workflow"


def test_get_workflow_template_by_name_not_found(db_session: Session):
    """Test fetching a non-existent workflow template by name returns None."""
    result = get_workflow_template_by_name(db_session, "nonexistent")
    assert result is None


def test_list_workflow_templates(db_session: Session):
    """Test listing workflow templates."""
    # Create multiple templates
    create_workflow_template(
        db_session,
        name="workflow_1",
        definition={"steps": []},
        status="active",
    )
    create_workflow_template(
        db_session,
        name="workflow_2",
        definition={"steps": []},
        status="active",
    )
    create_workflow_template(
        db_session,
        name="workflow_3",
        definition={"steps": []},
        status="inactive",
    )

    # List all templates
    all_templates = list_workflow_templates(db_session)
    assert len(all_templates) == 3

    # List only active templates
    active_templates = list_workflow_templates(db_session, status="active")
    assert len(active_templates) == 2

    # List with limit
    limited_templates = list_workflow_templates(db_session, limit=2)
    assert len(limited_templates) == 2


def test_update_workflow_template(db_session: Session):
    """Test updating a workflow template."""
    # Create a template
    template = create_workflow_template(
        db_session,
        name="original_name",
        description="Original description",
        definition={"steps": []},
        version="1.0.0",
        status="active",
    )

    original_id = template.id

    # Update the template
    updated = update_workflow_template(
        db_session,
        template.id,
        name="updated_name",
        description="Updated description",
        definition={"steps": [{"type": "action"}]},
        version="2.0.0",
        status="inactive",
    )

    assert updated.id == original_id
    assert updated.name == "updated_name"
    assert updated.description == "Updated description"
    assert updated.definition == {"steps": [{"type": "action"}]}
    assert updated.version == "2.0.0"
    assert updated.status == "inactive"


def test_update_workflow_template_partial(db_session: Session):
    """Test updating only some fields of a workflow template."""
    # Create a template
    template = create_workflow_template(
        db_session,
        name="test_workflow",
        description="Original description",
        definition={"steps": []},
        version="1.0.0",
        status="active",
    )

    # Update only the description
    updated = update_workflow_template(
        db_session,
        template.id,
        description="New description",
    )

    assert updated.name == "test_workflow"  # Unchanged
    assert updated.description == "New description"  # Changed
    assert updated.version == "1.0.0"  # Unchanged
    assert updated.status == "active"  # Unchanged


def test_update_workflow_template_not_found(db_session: Session):
    """Test updating a non-existent workflow template raises ValueError."""
    with pytest.raises(ValueError, match="WorkflowTemplate not found"):
        update_workflow_template(
            db_session,
            uuid4(),
            name="new_name",
        )


def test_delete_workflow_template(db_session: Session):
    """Test deleting a workflow template."""
    # Create a template
    template = create_workflow_template(
        db_session,
        name="to_delete",
        definition={"steps": []},
    )

    template_id = template.id

    # Delete the template
    result = delete_workflow_template(db_session, template_id)
    assert result is True

    # Verify it's gone
    fetched = get_workflow_template_by_id(db_session, template_id)
    assert fetched is None


def test_delete_workflow_template_not_found(db_session: Session):
    """Test deleting a non-existent workflow template returns False."""
    result = delete_workflow_template(db_session, uuid4())
    assert result is False


def test_workflow_template_unique_name_constraint(db_session: Session):
    """Test that workflow template names must be unique."""
    # Create first template
    create_workflow_template(
        db_session,
        name="duplicate_name",
        definition={"steps": []},
    )

    # Attempt to create another with the same name should raise an error
    with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
        create_workflow_template(
            db_session,
            name="duplicate_name",
            definition={"steps": []},
        )
