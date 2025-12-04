"""
Workflow Template Management Service.

Provides CRUD operations for workflow templates and their versions.
Supports draft management, validation, and querying published templates.
"""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.core_entities import WorkflowTemplate, TemplateVersion
from app.workflows.schemas import WorkflowDefinition


def create_template(
    session: Session,
    *,
    tenant_id: Any,
    name: str,
    description: Optional[str] = None,
    category: str = "general",
    draft_definition: Optional[dict[str, Any]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> WorkflowTemplate:
    """
    Create a new workflow template in draft status.

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session.
    tenant_id : Any
        UUID of the tenant owning this template.
    name : str
        Human-readable name for the template.
    description : str | None
        Optional description of what this template does.
    category : str, default 'general'
        Category/classification for the template.
    draft_definition : dict[str, Any] | None
        Optional initial workflow definition (not yet published).
    metadata : dict[str, Any] | None
        Optional metadata (tags, author, etc.).

    Returns
    -------
    WorkflowTemplate
        The newly created template instance.
    """
    template = WorkflowTemplate(
        tenant_id=tenant_id,
        name=name,
        description=description,
        category=category,
        status="draft",
        draft_definition=draft_definition,
        metadata=metadata,
    )

    session.add(template)
    session.commit()
    session.refresh(template)

    return template


def get_template_by_id(
    session: Session,
    template_id: Any,
) -> Optional[WorkflowTemplate]:
    """
    Fetch a template by its ID.

    Returns
    -------
    WorkflowTemplate | None
        The template if found, otherwise None.
    """
    return session.query(WorkflowTemplate).filter(
        WorkflowTemplate.id == template_id
    ).first()


def update_template_draft(
    session: Session,
    *,
    template_id: Any,
    draft_definition: dict[str, Any],
    description: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> WorkflowTemplate:
    """
    Update a template's draft definition and metadata.

    This does NOT create a published version - it only modifies the working draft.

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session.
    template_id : Any
        UUID of the template to update.
    draft_definition : dict[str, Any]
        The updated workflow definition.
    description : str | None
        Optional updated description.
    metadata : dict[str, Any] | None
        Optional updated metadata.

    Returns
    -------
    WorkflowTemplate
        The updated template instance.

    Raises
    ------
    ValueError
        If the template does not exist.
    """
    template = get_template_by_id(session, template_id)
    if template is None:
        raise ValueError(f"Template not found: {template_id}")

    template.draft_definition = draft_definition
    if description is not None:
        template.description = description
    if metadata is not None:
        template.metadata = metadata

    template.updated_at = func.now()

    session.commit()
    session.refresh(template)

    return template


def list_templates(
    session: Session,
    *,
    tenant_id: Optional[Any] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
) -> list[WorkflowTemplate]:
    """
    List workflow templates with optional filters.

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session.
    tenant_id : Any | None
        If provided, filter by tenant.
    status : str | None
        If provided, filter by status (e.g., 'draft', 'published').
    category : str | None
        If provided, filter by category.

    Returns
    -------
    list[WorkflowTemplate]
        List of matching templates, ordered by created_at descending.
    """
    query = session.query(WorkflowTemplate)

    if tenant_id is not None:
        query = query.filter(WorkflowTemplate.tenant_id == tenant_id)

    if status is not None:
        query = query.filter(WorkflowTemplate.status == status)

    if category is not None:
        query = query.filter(WorkflowTemplate.category == category)

    query = query.order_by(WorkflowTemplate.created_at.desc())

    return query.all()


def get_latest_version(
    session: Session,
    template_id: Any,
) -> Optional[TemplateVersion]:
    """
    Get the latest published version of a template.

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session.
    template_id : Any
        UUID of the template.

    Returns
    -------
    TemplateVersion | None
        The latest version if any exist, otherwise None.
    """
    return session.query(TemplateVersion).filter(
        TemplateVersion.template_id == template_id
    ).order_by(
        TemplateVersion.version_number.desc()
    ).first()


def get_version_by_number(
    session: Session,
    template_id: Any,
    version_number: int,
) -> Optional[TemplateVersion]:
    """
    Get a specific version of a template.

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session.
    template_id : Any
        UUID of the template.
    version_number : int
        The version number to retrieve.

    Returns
    -------
    TemplateVersion | None
        The version if found, otherwise None.
    """
    return session.query(TemplateVersion).filter(
        TemplateVersion.template_id == template_id,
        TemplateVersion.version_number == version_number,
    ).first()


def list_versions(
    session: Session,
    template_id: Any,
) -> list[TemplateVersion]:
    """
    List all published versions of a template.

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session.
    template_id : Any
        UUID of the template.

    Returns
    -------
    list[TemplateVersion]
        All versions, ordered by version_number descending.
    """
    return session.query(TemplateVersion).filter(
        TemplateVersion.template_id == template_id
    ).order_by(
        TemplateVersion.version_number.desc()
    ).all()


def validate_workflow_definition(definition: dict[str, Any]) -> bool:
    """
    Validate a workflow definition against the schema.

    Parameters
    ----------
    definition : dict[str, Any]
        The workflow definition to validate.

    Returns
    -------
    bool
        True if valid.

    Raises
    ------
    ValueError
        If validation fails.
    """
    try:
        WorkflowDefinition(**definition)
        return True
    except Exception as e:
        raise ValueError(f"Invalid workflow definition: {e}")
