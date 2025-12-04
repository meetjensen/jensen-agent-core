"""
Phase F6: Workflow Template Catalog Service

This service manages workflow templates and their versions with compatibility metadata.
It provides functions for:
- Creating and managing templates
- Publishing new versions with automatic compatibility inference
- Assessing compatibility of proposed changes
- Updating version metadata
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.core_entities import WorkflowTemplate, WorkflowTemplateVersion
from app.workflows.diff import (
    compute_structural_hash,
    diff_definitions,
    generate_change_summary,
    is_likely_breaking_change,
)


class TemplateNotFoundError(Exception):
    """Raised when a template is not found."""

    pass


class VersionNotFoundError(Exception):
    """Raised when a version is not found."""

    pass


class DuplicateVersionError(Exception):
    """Raised when trying to create a duplicate version."""

    pass


def get_or_create_template(
    db: Session,
    key: str,
    name: str,
    description: Optional[str] = None,
) -> WorkflowTemplate:
    """
    Get an existing template by key, or create a new one if it doesn't exist.

    Args:
        db: Database session
        key: Unique template key (e.g., 'approval.basic')
        name: Human-readable name
        description: Optional description

    Returns:
        The WorkflowTemplate instance
    """
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.key == key).first()

    if not template:
        template = WorkflowTemplate(
            key=key,
            name=name,
            description=description,
        )
        db.add(template)
        db.flush()

    return template


def get_template(db: Session, key: str) -> Optional[WorkflowTemplate]:
    """
    Get a template by key.

    Args:
        db: Database session
        key: Template key

    Returns:
        WorkflowTemplate or None if not found
    """
    return db.query(WorkflowTemplate).filter(WorkflowTemplate.key == key).first()


def list_templates(db: Session) -> List[WorkflowTemplate]:
    """
    List all templates.

    Args:
        db: Database session

    Returns:
        List of WorkflowTemplate instances
    """
    return db.query(WorkflowTemplate).order_by(WorkflowTemplate.created_at.desc()).all()


def get_version(
    db: Session,
    template_key: str,
    version: str,
) -> Optional[WorkflowTemplateVersion]:
    """
    Get a specific version of a template.

    Args:
        db: Database session
        template_key: Template key
        version: Version string (e.g., '1.0.0')

    Returns:
        WorkflowTemplateVersion or None if not found
    """
    return (
        db.query(WorkflowTemplateVersion)
        .join(WorkflowTemplate)
        .filter(
            WorkflowTemplate.key == template_key,
            WorkflowTemplateVersion.version == version,
        )
        .first()
    )


def get_version_by_id(
    db: Session,
    version_id: UUID,
) -> Optional[WorkflowTemplateVersion]:
    """
    Get a version by its ID.

    Args:
        db: Database session
        version_id: Version UUID

    Returns:
        WorkflowTemplateVersion or None if not found
    """
    return db.query(WorkflowTemplateVersion).filter(WorkflowTemplateVersion.id == version_id).first()


def list_versions(
    db: Session,
    template_key: str,
    status: Optional[str] = None,
) -> List[WorkflowTemplateVersion]:
    """
    List all versions of a template.

    Args:
        db: Database session
        template_key: Template key
        status: Optional status filter ('draft', 'published', 'deprecated')

    Returns:
        List of WorkflowTemplateVersion instances, ordered by creation date (newest first)
    """
    query = (
        db.query(WorkflowTemplateVersion)
        .join(WorkflowTemplate)
        .filter(WorkflowTemplate.key == template_key)
    )

    if status:
        query = query.filter(WorkflowTemplateVersion.status == status)

    return query.order_by(desc(WorkflowTemplateVersion.created_at)).all()


def get_latest_published_version(
    db: Session,
    template_key: str,
) -> Optional[WorkflowTemplateVersion]:
    """
    Get the latest published version of a template.

    Args:
        db: Database session
        template_key: Template key

    Returns:
        Latest published WorkflowTemplateVersion or None
    """
    return (
        db.query(WorkflowTemplateVersion)
        .join(WorkflowTemplate)
        .filter(
            WorkflowTemplate.key == template_key,
            WorkflowTemplateVersion.status == "published",
        )
        .order_by(desc(WorkflowTemplateVersion.published_at))
        .first()
    )


def assess_compatibility(
    db: Session,
    template_key: str,
    new_definition: dict,
) -> dict:
    """
    Assess the compatibility of a new definition against the latest published version.

    This function:
    1. Finds the latest published version
    2. Computes structural hash of new definition
    3. Compares definitions and generates a diff
    4. Infers compatibility level based on the diff

    Args:
        db: Database session
        template_key: Template key
        new_definition: The proposed new workflow definition

    Returns:
        Dictionary containing:
        - inferred_level: 'breaking', 'additive', or 'unknown' (if no previous version)
        - structural_hash: SHA-256 hash of new definition
        - diff: Dictionary of structural differences (None if no previous version)
        - change_summary: Human-readable summary of changes
        - previous_version: The version string of the previous version (None if first version)
    """
    # Compute structural hash
    structural_hash = compute_structural_hash(new_definition)

    # Get latest published version
    latest_version = get_latest_published_version(db, template_key)

    if not latest_version:
        # No previous version, this is the first version
        return {
            "inferred_level": "unknown",
            "structural_hash": structural_hash,
            "diff": None,
            "change_summary": "Initial version",
            "previous_version": None,
        }

    # Compare with previous version
    diff = diff_definitions(latest_version.definition, new_definition)
    is_breaking = is_likely_breaking_change(diff)
    change_summary = generate_change_summary(diff)

    inferred_level = "breaking" if is_breaking else "additive"

    return {
        "inferred_level": inferred_level,
        "structural_hash": structural_hash,
        "diff": diff,
        "change_summary": change_summary,
        "previous_version": latest_version.version,
    }


def publish_version(
    db: Session,
    template_key: str,
    version: str,
    definition: dict,
    name: str,
    description: Optional[str] = None,
    compatibility_level: Optional[str] = None,
    change_summary: Optional[str] = None,
    auto_publish: bool = True,
) -> WorkflowTemplateVersion:
    """
    Create and optionally publish a new version of a workflow template.

    This function:
    1. Gets or creates the template
    2. Assesses compatibility automatically
    3. Uses provided compatibility_level or infers it
    4. Uses provided change_summary or generates it
    5. Creates the version record
    6. Optionally publishes it immediately

    Args:
        db: Database session
        template_key: Template key
        version: Version string (e.g., '1.0.0')
        definition: Workflow definition dictionary
        name: Template name (used if creating new template)
        description: Template description (used if creating new template)
        compatibility_level: Optional manual override for compatibility level
        change_summary: Optional manual change summary
        auto_publish: If True, publish immediately; if False, create as draft

    Returns:
        The created WorkflowTemplateVersion

    Raises:
        DuplicateVersionError: If the version already exists
    """
    # Get or create template
    template = get_or_create_template(db, template_key, name, description)

    # Check for duplicate version
    existing = get_version(db, template_key, version)
    if existing:
        raise DuplicateVersionError(
            f"Version {version} already exists for template {template_key}"
        )

    # Assess compatibility
    assessment = assess_compatibility(db, template_key, definition)

    # Use provided values or fall back to assessed values
    final_compatibility_level = compatibility_level or assessment["inferred_level"]
    final_change_summary = change_summary or assessment["change_summary"]

    # Create version
    new_version = WorkflowTemplateVersion(
        template_id=template.id,
        version=version,
        definition=definition,
        status="published" if auto_publish else "draft",
        compatibility_level=final_compatibility_level,
        change_summary=final_change_summary,
        structural_hash=assessment["structural_hash"],
        published_at=datetime.utcnow() if auto_publish else None,
    )

    db.add(new_version)
    db.flush()

    return new_version


def update_version_metadata(
    db: Session,
    version_id: UUID,
    compatibility_level: Optional[str] = None,
    change_summary: Optional[str] = None,
) -> WorkflowTemplateVersion:
    """
    Update the metadata of a template version.

    This allows manual correction of automatically inferred compatibility data.
    Note: Cannot modify published versions' definitions (immutability rule),
    but metadata can be updated.

    Args:
        db: Database session
        version_id: Version UUID
        compatibility_level: New compatibility level
        change_summary: New change summary

    Returns:
        The updated WorkflowTemplateVersion

    Raises:
        VersionNotFoundError: If version doesn't exist
    """
    version = get_version_by_id(db, version_id)
    if not version:
        raise VersionNotFoundError(f"Version {version_id} not found")

    if compatibility_level:
        version.compatibility_level = compatibility_level

    if change_summary:
        version.change_summary = change_summary

    db.flush()
    return version


def deprecate_version(
    db: Session,
    version_id: UUID,
) -> WorkflowTemplateVersion:
    """
    Mark a version as deprecated.

    Args:
        db: Database session
        version_id: Version UUID

    Returns:
        The updated WorkflowTemplateVersion

    Raises:
        VersionNotFoundError: If version doesn't exist
    """
    version = get_version_by_id(db, version_id)
    if not version:
        raise VersionNotFoundError(f"Version {version_id} not found")

    version.status = "deprecated"
    db.flush()
    return version
