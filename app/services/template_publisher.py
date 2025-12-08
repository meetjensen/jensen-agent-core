"""
Workflow Template Publishing Engine (Phase F5).

This module implements the publishing workflow for workflow templates:
- Validates draft definitions
- Creates immutable published versions
- Enforces version immutability
- Emits publishing events
- Updates template metadata
"""
from __future__ import annotations

import copy
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.core_entities import WorkflowTemplate, TemplateVersion, AgentEvent
from app.services.workflow_templates import (
    get_template_by_id,
    get_latest_version,
    validate_workflow_definition,
)


def validate_and_publish_template(
    session: Session,
    *,
    template_id: Any,
    published_by: str,
    changelog: Optional[str] = None,
    force_validation: bool = True,
) -> tuple[TemplateVersion, AgentEvent]:
    """
    Validate a template's draft and publish it as a new immutable version.

    This is the main entry point for the publishing workflow. It:
    1. Validates the template exists and has a draft definition
    2. Validates the workflow definition schema
    3. Freezes the definition into an immutable version
    4. Creates a new TemplateVersion entry
    5. Updates the template status to 'published'
    6. Emits a publish event

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session.
    template_id : Any
        UUID of the template to publish.
    published_by : str
        Actor/user who is publishing this version.
    changelog : str | None
        Optional changelog describing what changed in this version.
    force_validation : bool, default True
        If True, validates the workflow definition before publishing.

    Returns
    -------
    tuple[TemplateVersion, AgentEvent]
        A tuple of (new_version, publish_event).

    Raises
    ------
    ValueError
        If template not found, no draft definition, or validation fails.
    RuntimeError
        If version creation fails due to immutability violation.
    """
    # 1. Fetch the template
    template = get_template_by_id(session, template_id)
    if template is None:
        raise ValueError(f"Template not found: {template_id}")

    if template.draft_definition is None:
        raise ValueError(
            f"Template {template_id} has no draft definition to publish"
        )

    # 2. Validate the workflow definition
    if force_validation:
        validate_workflow_definition(template.draft_definition)

    # 3. Freeze the definition (deep copy to ensure immutability)
    frozen_def = freeze_template_definition(template.draft_definition)

    # 4. Determine the next version number
    latest_version = get_latest_version(session, template_id)
    next_version_number = 1 if latest_version is None else latest_version.version_number + 1

    # 5. Create the published version entry
    new_version = create_published_version_entry(
        session,
        template_id=template_id,
        version_number=next_version_number,
        frozen_definition=frozen_def,
        published_by=published_by,
        changelog=changelog,
    )

    # 6. Update template metadata
    update_template_metadata(
        session,
        template=template,
        new_status="published",
    )

    # 7. Emit publish event
    event = emit_publish_event(
        session,
        template=template,
        version=new_version,
        actor=published_by,
    )

    return new_version, event


def publish_workflow_template(
    session: Session,
    *,
    template_id: Any,
    published_by: str,
    changelog: Optional[str] = None,
) -> dict[str, Any]:
    """
    High-level publish workflow that wraps validate_and_publish_template.

    This function provides a simpler interface for publishing templates
    and returns a summary dict instead of the raw database objects.

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session.
    template_id : Any
        UUID of the template to publish.
    published_by : str
        Actor/user who is publishing this version.
    changelog : str | None
        Optional changelog describing what changed in this version.

    Returns
    -------
    dict[str, Any]
        A summary dict containing:
        - template_id: The template UUID
        - template_name: The template name
        - version_id: The new version UUID
        - version_number: The new version number
        - published_by: The publishing actor
        - published_at: ISO timestamp
        - event_id: The publish event UUID
        - status: 'published'
    """
    version, event = validate_and_publish_template(
        session,
        template_id=template_id,
        published_by=published_by,
        changelog=changelog,
    )

    return {
        "template_id": str(version.template_id),
        "template_name": version.template.name,
        "version_id": str(version.id),
        "version_number": version.version_number,
        "published_by": version.published_by,
        "published_at": version.published_at.isoformat(),
        "event_id": str(event.id),
        "status": "published",
    }


def freeze_template_definition(definition: dict[str, Any]) -> dict[str, Any]:
    """
    Create an immutable frozen copy of a template definition.

    This function deep-copies the definition to ensure the published
    version cannot be modified by mutations to the original draft.

    Parameters
    ----------
    definition : dict[str, Any]
        The draft workflow definition to freeze.

    Returns
    -------
    dict[str, Any]
        A deep copy of the definition, ready for immutable storage.
    """
    return copy.deepcopy(definition)


def create_published_version_entry(
    session: Session,
    *,
    template_id: Any,
    version_number: int,
    frozen_definition: dict[str, Any],
    published_by: str,
    changelog: Optional[str] = None,
) -> TemplateVersion:
    """
    Create a new immutable TemplateVersion database entry.

    This function enforces the immutability contract:
    - Once created, a TemplateVersion cannot be modified
    - Version numbers are sequential and unique per template

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session.
    template_id : Any
        UUID of the parent template.
    version_number : int
        The sequential version number (must be unique per template).
    frozen_definition : dict[str, Any]
        The immutable frozen workflow definition.
    published_by : str
        Actor/user who published this version.
    changelog : str | None
        Optional changelog for this version.

    Returns
    -------
    TemplateVersion
        The newly created version instance.

    Raises
    ------
    RuntimeError
        If a version with this number already exists (immutability violation).
    """
    # Check for existing version with this number (enforce immutability)
    existing = session.query(TemplateVersion).filter(
        TemplateVersion.template_id == template_id,
        TemplateVersion.version_number == version_number,
    ).first()

    if existing is not None:
        raise RuntimeError(
            f"Version {version_number} already exists for template {template_id}. "
            "Template versions are immutable and cannot be replaced."
        )

    version = TemplateVersion(
        template_id=template_id,
        version_number=version_number,
        frozen_definition=frozen_definition,
        changelog=changelog,
        published_by=published_by,
    )

    session.add(version)
    session.commit()
    session.refresh(version)

    return version


def update_template_metadata(
    session: Session,
    *,
    template: WorkflowTemplate,
    new_status: str,
) -> WorkflowTemplate:
    """
    Update template metadata after publishing.

    This function updates the template's status and updated_at timestamp.
    It does NOT modify the draft_definition (drafts remain editable).

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session.
    template : WorkflowTemplate
        The template instance to update.
    new_status : str
        The new status (typically 'published').

    Returns
    -------
    WorkflowTemplate
        The updated template instance.
    """
    template.status = new_status
    template.updated_at = func.now()

    session.commit()
    session.refresh(template)

    return template


def emit_publish_event(
    session: Session,
    *,
    template: WorkflowTemplate,
    version: TemplateVersion,
    actor: str,
) -> AgentEvent:
    """
    Emit an AgentEvent to record the template publication.

    This event provides an audit trail for template publishing operations.

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session.
    template : WorkflowTemplate
        The template that was published.
    version : TemplateVersion
        The newly created version.
    actor : str
        The actor/user who published the template.

    Returns
    -------
    AgentEvent
        The newly created event instance.

    Notes
    -----
    Since template publishing is not tied to a specific Run, we create
    a synthetic Run entry or use a system-wide "publishing" run.
    For Phase F5, we'll use a placeholder run_id approach.
    """
    from app.services.core_runs import create_run

    # Create a synthetic run for this publishing event
    # In production, you might have a dedicated "system" tenant and run
    run = create_run(
        session,
        tenant_id=template.tenant_id,
        workspace_id=None,
        kind="template_publish",
        label=f"Publish template '{template.name}' v{version.version_number}",
        initiator=actor,
        notes=f"Published version {version.version_number} of template {template.id}",
    )

    event = AgentEvent(
        run_id=run.id,
        task_id=None,
        actor=actor,
        event_type="template_published",
        summary=f"Published template '{template.name}' version {version.version_number}",
        details={
            "template_id": str(template.id),
            "template_name": template.name,
            "version_id": str(version.id),
            "version_number": version.version_number,
            "changelog": version.changelog,
        },
        step=None,
    )

    session.add(event)
    session.commit()
    session.refresh(event)

    return event


def enforce_immutability_rules(
    session: Session,
    version_id: Any,
) -> bool:
    """
    Verify that a published version remains immutable.

    This is a validation/audit function that checks whether a version's
    frozen_definition has been modified since creation.

    Parameters
    ----------
    session : Session
        An active SQLAlchemy session.
    version_id : Any
        UUID of the version to check.

    Returns
    -------
    bool
        True if the version is properly immutable (no modifications detected).

    Notes
    -----
    In a production system, you might implement additional checks:
    - Checksums/hashes of the frozen_definition
    - Database-level constraints preventing updates
    - Audit log review
    """
    version = session.query(TemplateVersion).filter(
        TemplateVersion.id == version_id
    ).first()

    if version is None:
        raise ValueError(f"Version not found: {version_id}")

    # Basic check: frozen_definition should never be None
    if version.frozen_definition is None:
        return False

    # In a more sophisticated system, you could:
    # - Compare checksums
    # - Verify database-level write locks
    # - Check audit logs for modification attempts

    return True
