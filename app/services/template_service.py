"""
Phase G: Template Catalog Service

Provides CRUD operations and version resolution logic for workflow templates.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import desc, and_
from sqlalchemy.orm import Session

from app.models.core_entities import WorkflowTemplate, WorkflowTemplateVersion
from app.workflows.compatibility import (
    TemplateStatus,
    CompatibilityLevel,
    compute_structural_hash,
    determine_compatibility_level,
)


logger = logging.getLogger(__name__)


# ============================================================================
# Template CRUD Operations
# ============================================================================


def create_template(
    session: Session,
    *,
    template_key: str,
    name: str,
    description: Optional[str] = None,
    owner: str,
) -> WorkflowTemplate:
    """Create a new workflow template."""
    template = WorkflowTemplate(
        template_key=template_key,
        name=name,
        description=description,
        owner=owner,
    )
    session.add(template)
    session.commit()
    session.refresh(template)
    return template


def get_template_by_key(
    session: Session,
    template_key: str,
) -> Optional[WorkflowTemplate]:
    """Get a template by its unique key."""
    return (
        session.query(WorkflowTemplate)
        .filter(WorkflowTemplate.template_key == template_key)
        .first()
    )


def get_template_by_id(
    session: Session,
    template_id: UUID,
) -> Optional[WorkflowTemplate]:
    """Get a template by its ID."""
    return session.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()


def list_templates(
    session: Session,
    *,
    owner: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Tuple[List[WorkflowTemplate], int]:
    """
    List all templates.

    Returns (templates, total_count).
    """
    query = session.query(WorkflowTemplate)

    if owner:
        query = query.filter(WorkflowTemplate.owner == owner)

    total = query.count()
    templates = query.order_by(WorkflowTemplate.created_at.desc()).limit(limit).offset(offset).all()

    return templates, total


# ============================================================================
# Version CRUD Operations
# ============================================================================


def create_version(
    session: Session,
    *,
    template_id: UUID,
    version_major: int,
    version_minor: int,
    definition: Dict[str, Any],
    status: TemplateStatus = TemplateStatus.DRAFT,
    compatibility_level: Optional[CompatibilityLevel] = None,
) -> WorkflowTemplateVersion:
    """
    Create a new version for a template.

    If compatibility_level is not provided, it will be auto-determined
    by comparing with the previous version.
    """
    # Compute structural hash
    structural_hash = compute_structural_hash(definition)

    # Auto-determine compatibility level if not provided
    if compatibility_level is None:
        # Find the most recent previous version
        prev_version = (
            session.query(WorkflowTemplateVersion)
            .filter(WorkflowTemplateVersion.template_id == template_id)
            .order_by(
                desc(WorkflowTemplateVersion.version_major),
                desc(WorkflowTemplateVersion.version_minor),
            )
            .first()
        )

        if prev_version:
            compatibility_level = determine_compatibility_level(
                prev_version.definition,
                definition,
            )
        else:
            # First version is always additive (creating something new)
            compatibility_level = CompatibilityLevel.ADDITIVE

    version = WorkflowTemplateVersion(
        template_id=template_id,
        version_major=version_major,
        version_minor=version_minor,
        definition=definition,
        status=status.value,
        compatibility_level=compatibility_level.value,
        structural_hash=structural_hash,
    )

    session.add(version)
    session.commit()
    session.refresh(version)

    return version


def get_version_by_id(
    session: Session,
    version_id: UUID,
) -> Optional[WorkflowTemplateVersion]:
    """Get a version by its ID."""
    return (
        session.query(WorkflowTemplateVersion)
        .filter(WorkflowTemplateVersion.id == version_id)
        .first()
    )


def get_version(
    session: Session,
    *,
    template_key: str,
    version_major: int,
    version_minor: int,
) -> Optional[WorkflowTemplateVersion]:
    """Get a specific version by template key and version numbers."""
    template = get_template_by_key(session, template_key)
    if not template:
        return None

    return (
        session.query(WorkflowTemplateVersion)
        .filter(
            and_(
                WorkflowTemplateVersion.template_id == template.id,
                WorkflowTemplateVersion.version_major == version_major,
                WorkflowTemplateVersion.version_minor == version_minor,
            )
        )
        .first()
    )


def list_versions(
    session: Session,
    *,
    template_key: str,
    status: Optional[TemplateStatus] = None,
) -> List[WorkflowTemplateVersion]:
    """List all versions for a template."""
    template = get_template_by_key(session, template_key)
    if not template:
        return []

    query = session.query(WorkflowTemplateVersion).filter(
        WorkflowTemplateVersion.template_id == template.id
    )

    if status:
        query = query.filter(WorkflowTemplateVersion.status == status.value)

    return query.order_by(
        desc(WorkflowTemplateVersion.version_major),
        desc(WorkflowTemplateVersion.version_minor),
    ).all()


def update_version_status(
    session: Session,
    *,
    version_id: UUID,
    status: TemplateStatus,
) -> Optional[WorkflowTemplateVersion]:
    """Update the status of a version."""
    version = get_version_by_id(session, version_id)
    if not version:
        return None

    version.status = status.value
    session.commit()
    session.refresh(version)

    return version


# ============================================================================
# Phase G: Version Resolution Logic
# ============================================================================


def resolve_version(
    session: Session,
    *,
    template_key: str,
    version_major: Optional[int] = None,
    version_minor: Optional[int] = None,
    allow_breaking: bool = False,
    allow_deprecated: bool = False,
    allow_draft: bool = False,
) -> Optional[Tuple[WorkflowTemplateVersion, str]]:
    """
    Resolve the best version for a template based on Phase G rules.

    Phase G Default Resolution Rules:
    - Always select the latest ACTIVE version that is NOT breaking
    - Allowed compatibility levels: additive + internal
    - Exclude: breaking, deprecated, draft (unless explicitly requested)
    - If allow_breaking=True, then breaking versions may be included

    Parameters
    ----------
    session : Session
        Database session
    template_key : str
        Template identifier
    version_major : int | None
        If provided, only consider this major version
    version_minor : int | None
        If provided, only consider this minor version (requires version_major)
    allow_breaking : bool
        If True, include versions with breaking compatibility level
    allow_deprecated : bool
        If True, include deprecated versions
    allow_draft : bool
        If True, include draft versions

    Returns
    -------
    tuple[WorkflowTemplateVersion, str] | None
        (resolved_version, resolution_reason) or None if no version found
    """
    template = get_template_by_key(session, template_key)
    if not template:
        logger.warning(
            "Version resolution failed: template not found",
            extra={
                "template_key": template_key,
                "reason": "template_not_found",
                "constraints": {
                    "version_major": version_major,
                    "version_minor": version_minor,
                    "allow_breaking": allow_breaking,
                    "allow_deprecated": allow_deprecated,
                    "allow_draft": allow_draft,
                },
            },
        )
        return None

    # Build query
    query = session.query(WorkflowTemplateVersion).filter(
        WorkflowTemplateVersion.template_id == template.id
    )

    # Filter by exact version if specified
    if version_major is not None and version_minor is not None:
        # Exact version request
        query = query.filter(
            and_(
                WorkflowTemplateVersion.version_major == version_major,
                WorkflowTemplateVersion.version_minor == version_minor,
            )
        )
        version = query.first()
        if version:
            logger.info(
                "Version resolved (exact match)",
                extra={
                    "template_key": template_key,
                    "resolved_version": f"{version.version_major}.{version.version_minor}",
                    "version_id": str(version.id),
                    "status": version.status,
                    "compatibility_level": version.compatibility_level,
                    "resolution_reason": f"Exact version {version_major}.{version_minor} requested",
                    "constraints": {
                        "version_major": version_major,
                        "version_minor": version_minor,
                        "allow_breaking": allow_breaking,
                        "allow_deprecated": allow_deprecated,
                        "allow_draft": allow_draft,
                    },
                },
            )
            return version, f"Exact version {version_major}.{version_minor} requested"

        logger.warning(
            "Version resolution failed: exact version not found",
            extra={
                "template_key": template_key,
                "reason": "version_not_found",
                "requested_version": f"{version_major}.{version_minor}",
                "constraints": {
                    "version_major": version_major,
                    "version_minor": version_minor,
                    "allow_breaking": allow_breaking,
                    "allow_deprecated": allow_deprecated,
                    "allow_draft": allow_draft,
                },
            },
        )
        return None

    if version_major is not None:
        # Major version constraint
        query = query.filter(WorkflowTemplateVersion.version_major == version_major)

    # Apply status filters (Phase G default rules)
    allowed_statuses = []
    if not allow_draft and not allow_deprecated:
        # Default: only active
        allowed_statuses = [TemplateStatus.ACTIVE.value]
    else:
        if not allow_draft:
            allowed_statuses.extend([TemplateStatus.ACTIVE.value])
        if allow_deprecated:
            allowed_statuses.append(TemplateStatus.DEPRECATED.value)
        if allow_draft:
            allowed_statuses.append(TemplateStatus.DRAFT.value)
        if not allowed_statuses:
            # If all flags are set, allow all statuses
            allowed_statuses = [s.value for s in TemplateStatus]

    query = query.filter(WorkflowTemplateVersion.status.in_(allowed_statuses))

    # Apply compatibility level filters (Phase G default rules)
    allowed_compat_levels = []
    if not allow_breaking:
        # Default: additive + internal only (exclude breaking)
        allowed_compat_levels = [
            CompatibilityLevel.ADDITIVE.value,
            CompatibilityLevel.INTERNAL.value,
            CompatibilityLevel.UNKNOWN.value,  # Include unknown to be safe
        ]
    else:
        # Include breaking changes
        allowed_compat_levels = [level.value for level in CompatibilityLevel]

    query = query.filter(WorkflowTemplateVersion.compatibility_level.in_(allowed_compat_levels))

    # Order by version (latest first)
    query = query.order_by(
        desc(WorkflowTemplateVersion.version_major),
        desc(WorkflowTemplateVersion.version_minor),
    )

    # Get the best match
    version = query.first()

    if not version:
        logger.warning(
            "Version resolution failed: no matching versions",
            extra={
                "template_key": template_key,
                "reason": "no_matching_versions",
                "constraints": {
                    "version_major": version_major,
                    "version_minor": version_minor,
                    "allow_breaking": allow_breaking,
                    "allow_deprecated": allow_deprecated,
                    "allow_draft": allow_draft,
                },
            },
        )
        return None

    # Build resolution reason
    reason_parts = []
    reason_parts.append(f"Latest version {version.version_major}.{version.version_minor}")
    reason_parts.append(f"status={version.status}")
    reason_parts.append(f"compatibility={version.compatibility_level}")
    if version_major is not None:
        reason_parts.append(f"major_constraint={version_major}")

    resolution_reason = ", ".join(reason_parts)

    logger.info(
        "Version resolved successfully",
        extra={
            "template_key": template_key,
            "resolved_version": f"{version.version_major}.{version.version_minor}",
            "version_id": str(version.id),
            "status": version.status,
            "compatibility_level": version.compatibility_level,
            "resolution_reason": resolution_reason,
            "constraints": {
                "version_major": version_major,
                "version_minor": version_minor,
                "allow_breaking": allow_breaking,
                "allow_deprecated": allow_deprecated,
                "allow_draft": allow_draft,
            },
        },
    )

    return version, resolution_reason
