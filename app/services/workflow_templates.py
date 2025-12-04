from __future__ import annotations

from typing import Any, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from sqlalchemy import and_, desc

from app.models.core_entities import WorkflowTemplate, WorkflowTemplateVersion


def create_workflow_template(
    session: Session,
    *,
    tenant_id: Any,
    name: str,
    category: str,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    status: str = "draft",
) -> WorkflowTemplate:
    """
    Create a new WorkflowTemplate in the catalog.

    Parameters
    ----------
    session : Session
        An existing SQLAlchemy session.
    tenant_id : Any
        UUID (or compatible type) of the tenant.
    name : str
        Name of the workflow template (must be unique within tenant).
    category : str
        Category for organizing templates (e.g., 'automation', 'deployment', 'monitoring').
    description : str | None
        Optional human-readable description of the template.
    tags : List[str] | None
        Optional list of tags for searchability.
    status : str, default 'draft'
        Initial status of the template ('draft', 'published', 'deprecated').

    Returns
    -------
    WorkflowTemplate
        The newly created WorkflowTemplate instance, refreshed from the database.
    """
    template = WorkflowTemplate(
        tenant_id=tenant_id,
        name=name,
        category=category,
        description=description,
        tags=tags,
        status=status,
        # created_at and updated_at rely on DB defaults
    )

    session.add(template)
    session.commit()
    session.refresh(template)

    return template


def create_workflow_template_version(
    session: Session,
    *,
    template_id: Any,
    version_major: int,
    version_minor: int,
    definition: dict,
    changelog: Optional[str] = None,
    status: str = "draft",
) -> WorkflowTemplateVersion:
    """
    Create a new version of an existing WorkflowTemplate.

    Parameters
    ----------
    session : Session
        An existing SQLAlchemy session.
    template_id : Any
        UUID (or compatible type) of the WorkflowTemplate.
    version_major : int
        Major version number (e.g., 1 in version 1.2).
    version_minor : int
        Minor version number (e.g., 2 in version 1.2).
    definition : dict
        The workflow definition (JSONB-compatible dictionary).
    changelog : str | None
        Optional description of changes in this version.
    status : str, default 'draft'
        Initial status of the version ('draft', 'published', 'deprecated').

    Returns
    -------
    WorkflowTemplateVersion
        The newly created WorkflowTemplateVersion instance, refreshed from the database.

    Raises
    ------
    ValueError
        If a version with the same major.minor already exists for this template.
    """
    # Check if version already exists
    existing = session.query(WorkflowTemplateVersion).filter(
        and_(
            WorkflowTemplateVersion.template_id == template_id,
            WorkflowTemplateVersion.version_major == version_major,
            WorkflowTemplateVersion.version_minor == version_minor,
        )
    ).first()

    if existing:
        raise ValueError(
            f"Version {version_major}.{version_minor} already exists for template {template_id}"
        )

    version = WorkflowTemplateVersion(
        template_id=template_id,
        version_major=version_major,
        version_minor=version_minor,
        definition=definition,
        changelog=changelog,
        status=status,
        # created_at relies on DB default
    )

    session.add(version)
    session.commit()
    session.refresh(version)

    return version


def get_workflow_template_by_id(
    session: Session,
    template_id: Any,
) -> Optional[WorkflowTemplate]:
    """
    Fetch a WorkflowTemplate by its primary key.

    Parameters
    ----------
    session : Session
        An existing SQLAlchemy session.
    template_id : Any
        UUID (or compatible type) of the template.

    Returns
    -------
    WorkflowTemplate | None
        The WorkflowTemplate instance if found, otherwise None.
    """
    return session.query(WorkflowTemplate).filter(
        WorkflowTemplate.id == template_id
    ).first()


def get_workflow_template_by_name(
    session: Session,
    *,
    tenant_id: Any,
    name: str,
) -> Optional[WorkflowTemplate]:
    """
    Fetch a WorkflowTemplate by tenant and name.

    Parameters
    ----------
    session : Session
        An existing SQLAlchemy session.
    tenant_id : Any
        UUID (or compatible type) of the tenant.
    name : str
        Name of the workflow template.

    Returns
    -------
    WorkflowTemplate | None
        The WorkflowTemplate instance if found, otherwise None.
    """
    return session.query(WorkflowTemplate).filter(
        and_(
            WorkflowTemplate.tenant_id == tenant_id,
            WorkflowTemplate.name == name,
        )
    ).first()


def list_workflow_templates(
    session: Session,
    *,
    tenant_id: Any,
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[WorkflowTemplate]:
    """
    List WorkflowTemplates for a tenant with optional filtering.

    Parameters
    ----------
    session : Session
        An existing SQLAlchemy session.
    tenant_id : Any
        UUID (or compatible type) of the tenant.
    category : str | None
        Optional category filter.
    status : str | None
        Optional status filter ('draft', 'published', 'deprecated').
    limit : int, default 100
        Maximum number of templates to return.
    offset : int, default 0
        Number of templates to skip for pagination.

    Returns
    -------
    List[WorkflowTemplate]
        List of WorkflowTemplate instances matching the criteria.
    """
    query = session.query(WorkflowTemplate).filter(
        WorkflowTemplate.tenant_id == tenant_id
    )

    if category is not None:
        query = query.filter(WorkflowTemplate.category == category)

    if status is not None:
        query = query.filter(WorkflowTemplate.status == status)

    # Order by updated_at descending (most recently updated first)
    query = query.order_by(desc(WorkflowTemplate.updated_at))

    return query.limit(limit).offset(offset).all()


def get_workflow_template_version(
    session: Session,
    *,
    template_id: Any,
    version_major: int,
    version_minor: int,
) -> Optional[WorkflowTemplateVersion]:
    """
    Fetch a specific version of a WorkflowTemplate.

    Parameters
    ----------
    session : Session
        An existing SQLAlchemy session.
    template_id : Any
        UUID (or compatible type) of the template.
    version_major : int
        Major version number.
    version_minor : int
        Minor version number.

    Returns
    -------
    WorkflowTemplateVersion | None
        The WorkflowTemplateVersion instance if found, otherwise None.
    """
    return session.query(WorkflowTemplateVersion).filter(
        and_(
            WorkflowTemplateVersion.template_id == template_id,
            WorkflowTemplateVersion.version_major == version_major,
            WorkflowTemplateVersion.version_minor == version_minor,
        )
    ).first()


def get_latest_version(
    session: Session,
    *,
    template_id: Any,
    status: Optional[str] = None,
) -> Optional[WorkflowTemplateVersion]:
    """
    Fetch the latest version of a WorkflowTemplate.

    The latest version is determined by ordering by version_major descending,
    then version_minor descending.

    Parameters
    ----------
    session : Session
        An existing SQLAlchemy session.
    template_id : Any
        UUID (or compatible type) of the template.
    status : str | None
        Optional status filter. If provided, only return versions with this status.
        Common values: 'published', 'draft', 'deprecated'.

    Returns
    -------
    WorkflowTemplateVersion | None
        The latest WorkflowTemplateVersion instance if found, otherwise None.
    """
    query = session.query(WorkflowTemplateVersion).filter(
        WorkflowTemplateVersion.template_id == template_id
    )

    if status is not None:
        query = query.filter(WorkflowTemplateVersion.status == status)

    return query.order_by(
        desc(WorkflowTemplateVersion.version_major),
        desc(WorkflowTemplateVersion.version_minor),
    ).first()


def list_workflow_template_versions(
    session: Session,
    *,
    template_id: Any,
    status: Optional[str] = None,
) -> List[WorkflowTemplateVersion]:
    """
    List all versions of a WorkflowTemplate.

    Parameters
    ----------
    session : Session
        An existing SQLAlchemy session.
    template_id : Any
        UUID (or compatible type) of the template.
    status : str | None
        Optional status filter.

    Returns
    -------
    List[WorkflowTemplateVersion]
        List of WorkflowTemplateVersion instances ordered by version (descending).
    """
    query = session.query(WorkflowTemplateVersion).filter(
        WorkflowTemplateVersion.template_id == template_id
    )

    if status is not None:
        query = query.filter(WorkflowTemplateVersion.status == status)

    return query.order_by(
        desc(WorkflowTemplateVersion.version_major),
        desc(WorkflowTemplateVersion.version_minor),
    ).all()


def publish_workflow_template_version(
    session: Session,
    *,
    template_id: Any,
    version_major: int,
    version_minor: int,
) -> Tuple[WorkflowTemplateVersion, WorkflowTemplate]:
    """
    Publish a WorkflowTemplateVersion and update the parent template status.

    This function:
    1. Sets the version status to 'published'
    2. Sets the version published_at timestamp
    3. Updates the parent template status to 'published'
    4. Updates the parent template updated_at timestamp

    Parameters
    ----------
    session : Session
        An existing SQLAlchemy session.
    template_id : Any
        UUID (or compatible type) of the template.
    version_major : int
        Major version number.
    version_minor : int
        Minor version number.

    Returns
    -------
    Tuple[WorkflowTemplateVersion, WorkflowTemplate]
        A tuple containing the updated version and template instances.

    Raises
    ------
    ValueError
        If the version or template is not found.
    """
    version = get_workflow_template_version(
        session,
        template_id=template_id,
        version_major=version_major,
        version_minor=version_minor,
    )

    if version is None:
        raise ValueError(
            f"Version {version_major}.{version_minor} not found for template {template_id}"
        )

    template = get_workflow_template_by_id(session, template_id)
    if template is None:
        raise ValueError(f"Template {template_id} not found")

    # Update version
    version.status = "published"
    version.published_at = func.now()

    # Update template
    template.status = "published"
    template.updated_at = func.now()

    session.commit()
    session.refresh(version)
    session.refresh(template)

    return version, template


def update_workflow_template(
    session: Session,
    *,
    template_id: Any,
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    status: Optional[str] = None,
) -> WorkflowTemplate:
    """
    Update a WorkflowTemplate's metadata.

    Parameters
    ----------
    session : Session
        An existing SQLAlchemy session.
    template_id : Any
        UUID (or compatible type) of the template.
    name : str | None
        New name for the template.
    description : str | None
        New description for the template.
    category : str | None
        New category for the template.
    tags : List[str] | None
        New tags for the template.
    status : str | None
        New status for the template.

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
        raise ValueError(f"Template {template_id} not found")

    # Update only provided fields
    if name is not None:
        template.name = name
    if description is not None:
        template.description = description
    if category is not None:
        template.category = category
    if tags is not None:
        template.tags = tags
    if status is not None:
        template.status = status

    # Update timestamp
    template.updated_at = func.now()

    session.commit()
    session.refresh(template)

    return template


def delete_workflow_template(
    session: Session,
    template_id: Any,
) -> bool:
    """
    Delete a WorkflowTemplate and all its versions.

    This is a hard delete that removes the template and all associated versions
    from the database due to CASCADE delete on the relationship.

    Parameters
    ----------
    session : Session
        An existing SQLAlchemy session.
    template_id : Any
        UUID (or compatible type) of the template.

    Returns
    -------
    bool
        True if the template was deleted, False if it was not found.
    """
    template = get_workflow_template_by_id(session, template_id)
    if template is None:
        return False

    session.delete(template)
    session.commit()

    return True


def create_next_minor_version(
    session: Session,
    *,
    template_id: Any,
    definition: dict,
    changelog: Optional[str] = None,
) -> WorkflowTemplateVersion:
    """
    Create the next minor version of a WorkflowTemplate.

    This helper automatically determines the next minor version number by
    finding the latest version and incrementing the minor version.

    Parameters
    ----------
    session : Session
        An existing SQLAlchemy session.
    template_id : Any
        UUID (or compatible type) of the template.
    definition : dict
        The workflow definition for the new version.
    changelog : str | None
        Optional description of changes.

    Returns
    -------
    WorkflowTemplateVersion
        The newly created WorkflowTemplateVersion instance.

    Notes
    -----
    - If no versions exist, creates version 1.0
    - If versions exist, increments the minor version (e.g., 1.2 -> 1.3)
    """
    latest = get_latest_version(session, template_id=template_id)

    if latest is None:
        # First version
        version_major = 1
        version_minor = 0
    else:
        # Increment minor version
        version_major = latest.version_major
        version_minor = latest.version_minor + 1

    return create_workflow_template_version(
        session,
        template_id=template_id,
        version_major=version_major,
        version_minor=version_minor,
        definition=definition,
        changelog=changelog,
    )


def create_next_major_version(
    session: Session,
    *,
    template_id: Any,
    definition: dict,
    changelog: Optional[str] = None,
) -> WorkflowTemplateVersion:
    """
    Create the next major version of a WorkflowTemplate.

    This helper automatically determines the next major version number by
    finding the latest version and incrementing the major version while
    resetting the minor version to 0.

    Parameters
    ----------
    session : Session
        An existing SQLAlchemy session.
    template_id : Any
        UUID (or compatible type) of the template.
    definition : dict
        The workflow definition for the new version.
    changelog : str | None
        Optional description of changes.

    Returns
    -------
    WorkflowTemplateVersion
        The newly created WorkflowTemplateVersion instance.

    Notes
    -----
    - If no versions exist, creates version 1.0
    - If versions exist, increments the major version and resets minor to 0
      (e.g., 1.2 -> 2.0)
    """
    latest = get_latest_version(session, template_id=template_id)

    if latest is None:
        # First version
        version_major = 1
        version_minor = 0
    else:
        # Increment major version, reset minor
        version_major = latest.version_major + 1
        version_minor = 0

    return create_workflow_template_version(
        session,
        template_id=template_id,
        version_major=version_major,
        version_minor=version_minor,
        definition=definition,
        changelog=changelog,
    )
