from __future__ import annotations

from typing import Any, Optional, List

from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.models.core_entities import WorkflowTemplate


def create_workflow_template(
    session: Session,
    *,
    name: str,
    definition: Any,
    description: Optional[str] = None,
    version: str = "1.0.0",
    status: str = "active",
) -> WorkflowTemplate:
    """
    Create a new WorkflowTemplate row in the database.

    Parameters
    ----------
    session : Session
        An existing SQLAlchemy session.
    name : str
        Unique name for the workflow template.
    definition : Any
        JSON-serializable workflow definition (steps, config, etc.).
    description : str | None
        Optional human-readable description.
    version : str, default '1.0.0'
        Version identifier for the template.
    status : str, default 'active'
        Status of the template ('active', 'inactive', 'deprecated', etc.).

    Returns
    -------
    WorkflowTemplate
        The newly created WorkflowTemplate instance, refreshed from the database.
    """
    template = WorkflowTemplate(
        name=name,
        description=description,
        definition=definition,
        version=version,
        status=status,
        # created_at and updated_at rely on DB defaults
    )

    session.add(template)
    session.commit()
    session.refresh(template)

    return template


def get_workflow_template_by_id(
    session: Session,
    template_id: Any,
) -> Optional[WorkflowTemplate]:
    """
    Fetch a WorkflowTemplate by its primary key.

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session.
    template_id : Any
        UUID (or compatible type) of the template.

    Returns
    -------
    WorkflowTemplate | None
        The WorkflowTemplate instance if found, otherwise None.
    """
    return (
        session.query(WorkflowTemplate)
        .filter(WorkflowTemplate.id == template_id)
        .first()
    )


def get_workflow_template_by_name(
    session: Session,
    name: str,
) -> Optional[WorkflowTemplate]:
    """
    Fetch a WorkflowTemplate by its unique name.

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session.
    name : str
        The unique name of the template.

    Returns
    -------
    WorkflowTemplate | None
        The WorkflowTemplate instance if found, otherwise None.
    """
    return (
        session.query(WorkflowTemplate)
        .filter(WorkflowTemplate.name == name)
        .first()
    )


def list_workflow_templates(
    session: Session,
    *,
    status: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[WorkflowTemplate]:
    """
    List workflow templates with optional filtering.

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session.
    status : str | None
        If provided, filter templates by status (e.g., 'active').
    limit : int | None
        If provided, limit the number of results returned.

    Returns
    -------
    List[WorkflowTemplate]
        List of WorkflowTemplate instances, ordered by created_at descending.
    """
    query = session.query(WorkflowTemplate)

    if status is not None:
        query = query.filter(WorkflowTemplate.status == status)

    query = query.order_by(WorkflowTemplate.created_at.desc())

    if limit is not None:
        query = query.limit(limit)

    return query.all()


def update_workflow_template(
    session: Session,
    template_id: Any,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    definition: Optional[Any] = None,
    version: Optional[str] = None,
    status: Optional[str] = None,
) -> WorkflowTemplate:
    """
    Update an existing WorkflowTemplate.

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session.
    template_id : Any
        UUID (or compatible type) of the template to update.
    name : str | None
        New name for the template (must be unique).
    description : str | None
        New description.
    definition : Any | None
        New workflow definition.
    version : str | None
        New version identifier.
    status : str | None
        New status.

    Returns
    -------
    WorkflowTemplate
        The updated WorkflowTemplate instance, refreshed from the database.

    Raises
    ------
    ValueError
        If the template is not found.
    """
    template = get_workflow_template_by_id(session, template_id)
    if template is None:
        raise ValueError(f"WorkflowTemplate not found for id={template_id}")

    # Update fields if provided
    if name is not None:
        template.name = name
    if description is not None:
        template.description = description
    if definition is not None:
        template.definition = definition
    if version is not None:
        template.version = version
    if status is not None:
        template.status = status

    # Update the updated_at timestamp
    template.updated_at = func.now()

    session.commit()
    session.refresh(template)

    return template


def delete_workflow_template(
    session: Session,
    template_id: Any,
) -> bool:
    """
    Delete a WorkflowTemplate by its primary key.

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session.
    template_id : Any
        UUID (or compatible type) of the template to delete.

    Returns
    -------
    bool
        True if the template was deleted, False if not found.
    """
    template = get_workflow_template_by_id(session, template_id)
    if template is None:
        return False

    session.delete(template)
    session.commit()

    return True
