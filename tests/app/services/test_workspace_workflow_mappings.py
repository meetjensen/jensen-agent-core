"""
Tests for workspace workflow mapping CRUD operations.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.models.core_entities import Base, WorkspaceWorkflowMapping
from app.services.workspace_workflow_mappings import (
    create_mapping,
    get_mapping_by_id,
    list_mappings_for_workspace,
    delete_mapping,
)


@pytest.fixture
def session() -> Session:
    """Create an in-memory SQLite session for testing."""
    # Create in-memory SQLite engine
    engine = create_engine("sqlite:///:memory:", future=True)

    # Register uuid_generate_v4() function for SQLite
    @event.listens_for(engine, "connect")
    def register_uuid(dbapi_conn, connection_record):
        def uuid_generate_v4():
            return str(uuid4())
        dbapi_conn.create_function("uuid_generate_v4", 0, uuid_generate_v4)

    # Trigger the connect event to register the function
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    # Create only the WorkspaceWorkflowMapping table
    WorkspaceWorkflowMapping.__table__.create(engine)

    # Create session
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session = SessionLocal()

    yield session

    session.close()


def test_create_mapping(session: Session) -> None:
    """Test creating a workspace workflow mapping."""
    tenant_id = uuid4()
    workspace_id = uuid4()
    template_id = uuid4()
    config = {"key": "value", "setting": 123}

    # Create mapping
    mapping = create_mapping(
        session,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        template_id=template_id,
        enabled=True,
        config=config,
    )

    # Assert fields match
    assert mapping.id is not None
    assert mapping.tenant_id == tenant_id
    assert mapping.workspace_id == workspace_id
    assert mapping.template_id == template_id
    assert mapping.enabled is True
    assert mapping.config == config
    assert mapping.created_at is not None
    assert mapping.updated_at is not None

    # Test default enabled value
    mapping2 = create_mapping(
        session,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        template_id=uuid4(),
    )
    assert mapping2.enabled is True
    assert mapping2.config is None


def test_list_mappings_for_workspace(session: Session) -> None:
    """Test listing mappings for a specific workspace."""
    tenant1_id = uuid4()
    tenant2_id = uuid4()
    workspace1_id = uuid4()
    workspace2_id = uuid4()

    # Create several mappings across tenants/workspaces
    mapping1 = create_mapping(
        session,
        tenant_id=tenant1_id,
        workspace_id=workspace1_id,
        template_id=uuid4(),
    )

    mapping2 = create_mapping(
        session,
        tenant_id=tenant1_id,
        workspace_id=workspace1_id,
        template_id=uuid4(),
    )

    # Different workspace, same tenant
    mapping3 = create_mapping(
        session,
        tenant_id=tenant1_id,
        workspace_id=workspace2_id,
        template_id=uuid4(),
    )

    # Different tenant
    mapping4 = create_mapping(
        session,
        tenant_id=tenant2_id,
        workspace_id=workspace1_id,
        template_id=uuid4(),
    )

    session.commit()

    # List mappings for tenant1/workspace1
    mappings = list_mappings_for_workspace(
        session,
        tenant_id=tenant1_id,
        workspace_id=workspace1_id,
    )

    # Should only return mappings for tenant1/workspace1
    assert len(mappings) == 2
    mapping_ids = {m.id for m in mappings}
    assert mapping1.id in mapping_ids
    assert mapping2.id in mapping_ids
    assert mapping3.id not in mapping_ids
    assert mapping4.id not in mapping_ids

    # Verify ordering by created_at
    assert mappings[0].created_at <= mappings[1].created_at

    # List mappings for tenant1/workspace2
    mappings_ws2 = list_mappings_for_workspace(
        session,
        tenant_id=tenant1_id,
        workspace_id=workspace2_id,
    )
    assert len(mappings_ws2) == 1
    assert mappings_ws2[0].id == mapping3.id

    # List mappings for non-existent workspace
    mappings_empty = list_mappings_for_workspace(
        session,
        tenant_id=uuid4(),
        workspace_id=uuid4(),
    )
    assert len(mappings_empty) == 0


def test_get_mapping_by_id(session: Session) -> None:
    """Test retrieving a mapping by ID."""
    tenant_id = uuid4()
    workspace_id = uuid4()
    template_id = uuid4()
    config = {"test": "data"}

    # Create mapping
    created_mapping = create_mapping(
        session,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        template_id=template_id,
        enabled=False,
        config=config,
    )
    session.commit()

    # Retrieve mapping
    retrieved_mapping = get_mapping_by_id(session, created_mapping.id)

    # Validate
    assert retrieved_mapping is not None
    assert retrieved_mapping.id == created_mapping.id
    assert retrieved_mapping.tenant_id == tenant_id
    assert retrieved_mapping.workspace_id == workspace_id
    assert retrieved_mapping.template_id == template_id
    assert retrieved_mapping.enabled is False
    assert retrieved_mapping.config == config

    # Test non-existent ID
    non_existent = get_mapping_by_id(session, uuid4())
    assert non_existent is None


def test_delete_mapping(session: Session) -> None:
    """Test deleting a mapping."""
    tenant_id = uuid4()
    workspace_id = uuid4()
    template_id = uuid4()

    # Create mapping
    mapping = create_mapping(
        session,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        template_id=template_id,
    )
    session.commit()
    mapping_id = mapping.id

    # Verify it exists
    assert get_mapping_by_id(session, mapping_id) is not None

    # Delete mapping
    delete_mapping(session, mapping_id)
    session.commit()

    # Assert not found
    assert get_mapping_by_id(session, mapping_id) is None

    # Test deleting non-existent mapping (should not raise error)
    delete_mapping(session, uuid4())
    session.commit()  # Should complete without error
