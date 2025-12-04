"""
Service layer for workspace workflow mapping CRUD operations.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.core_entities import WorkspaceWorkflowMapping


def create_mapping(
    session: Session,
    *,
    tenant_id: UUID,
    workspace_id: UUID,
    template_id: UUID,
    enabled: bool = True,
    config: dict[str, Any] | None = None,
) -> WorkspaceWorkflowMapping:
    """
    Create a new workspace workflow mapping.

    Args:
        session: SQLAlchemy session
        tenant_id: Tenant UUID
        workspace_id: Workspace UUID
        template_id: Workflow template UUID
        enabled: Whether the mapping is enabled (default: True)
        config: Optional JSONB configuration

    Returns:
        The created WorkspaceWorkflowMapping instance
    """
    mapping = WorkspaceWorkflowMapping(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        template_id=template_id,
        enabled=enabled,
        config=config,
    )
    session.add(mapping)
    session.flush()
    return mapping


def get_mapping_by_id(
    session: Session,
    mapping_id: UUID,
) -> WorkspaceWorkflowMapping | None:
    """
    Retrieve a mapping by its ID.

    Args:
        session: SQLAlchemy session
        mapping_id: Mapping UUID

    Returns:
        The WorkspaceWorkflowMapping instance or None if not found
    """
    return session.query(WorkspaceWorkflowMapping).filter(
        WorkspaceWorkflowMapping.id == mapping_id
    ).first()


def list_mappings_for_workspace(
    session: Session,
    *,
    tenant_id: UUID,
    workspace_id: UUID,
) -> list[WorkspaceWorkflowMapping]:
    """
    List all workflow mappings for a specific workspace.

    Args:
        session: SQLAlchemy session
        tenant_id: Tenant UUID
        workspace_id: Workspace UUID

    Returns:
        List of WorkspaceWorkflowMapping instances, ordered by created_at
    """
    return (
        session.query(WorkspaceWorkflowMapping)
        .filter(
            WorkspaceWorkflowMapping.tenant_id == tenant_id,
            WorkspaceWorkflowMapping.workspace_id == workspace_id,
        )
        .order_by(WorkspaceWorkflowMapping.created_at)
        .all()
    )


def delete_mapping(
    session: Session,
    mapping_id: UUID,
) -> None:
    """
    Delete a mapping by its ID.

    Args:
        session: SQLAlchemy session
        mapping_id: Mapping UUID
    """
    mapping = session.query(WorkspaceWorkflowMapping).filter(
        WorkspaceWorkflowMapping.id == mapping_id
    ).first()
    if mapping:
        session.delete(mapping)
        session.flush()
