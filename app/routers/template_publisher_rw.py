"""
Template Publishing Router (Phase F5).

Provides REST API endpoints for:
- Publishing workflow templates
- Listing templates and versions
- Viewing published versions
- Managing template drafts
"""
from __future__ import annotations

from typing import Any, Generator, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app._db import DB_URL
from app.services.template_publisher import (
    publish_workflow_template,
    validate_and_publish_template,
    enforce_immutability_rules,
)
from app.services.workflow_templates import (
    create_template,
    get_template_by_id,
    update_template_draft,
    list_templates,
    get_latest_version,
    get_version_by_number,
    list_versions,
)


# Router setup
router = APIRouter(prefix="/api/templates", tags=["templates"])


# Database session factory
if not DB_URL:
    raise RuntimeError("DATABASE_URL is not set; cannot use template_publisher_rw router")

_engine = create_engine(DB_URL, pool_pre_ping=True, future=True)
_SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB Session."""
    session: Session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


# Request/Response Models
class CreateTemplateRequest(BaseModel):
    tenant_id: UUID
    name: str
    description: Optional[str] = None
    category: str = "general"
    draft_definition: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None


class CreateTemplateResponse(BaseModel):
    template_id: str
    name: str
    status: str
    created_at: str


class UpdateTemplateDraftRequest(BaseModel):
    draft_definition: dict[str, Any]
    description: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class UpdateTemplateDraftResponse(BaseModel):
    template_id: str
    name: str
    status: str
    updated_at: str


class PublishTemplateRequest(BaseModel):
    published_by: str
    changelog: Optional[str] = None


class PublishTemplateResponse(BaseModel):
    template_id: str
    template_name: str
    version_id: str
    version_number: int
    published_by: str
    published_at: str
    event_id: str
    status: str


class TemplateListItem(BaseModel):
    id: str
    name: str
    description: Optional[str]
    category: str
    status: str
    created_at: str
    updated_at: str
    latest_version_number: Optional[int] = None


class TemplateVersionDetail(BaseModel):
    id: str
    template_id: str
    version_number: int
    frozen_definition: dict[str, Any]
    changelog: Optional[str]
    published_by: str
    published_at: str


class TemplateDetail(BaseModel):
    id: str
    name: str
    description: Optional[str]
    category: str
    status: str
    draft_definition: Optional[dict[str, Any]]
    metadata: Optional[dict[str, Any]]
    created_at: str
    updated_at: str
    versions: list[TemplateVersionDetail]


# Endpoints

@router.post("/", response_model=CreateTemplateResponse)
def create_new_template(
    req: CreateTemplateRequest,
    session: Session = Depends(get_session),
):
    """
    Create a new workflow template in draft status.

    This endpoint creates a new template with an optional draft definition.
    Templates start in 'draft' status and must be published to create
    immutable versions.
    """
    template = create_template(
        session,
        tenant_id=req.tenant_id,
        name=req.name,
        description=req.description,
        category=req.category,
        draft_definition=req.draft_definition,
        metadata=req.metadata,
    )

    return CreateTemplateResponse(
        template_id=str(template.id),
        name=template.name,
        status=template.status,
        created_at=template.created_at.isoformat(),
    )


@router.get("/", response_model=list[TemplateListItem])
def list_all_templates(
    tenant_id: Optional[UUID] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """
    List workflow templates with optional filters.

    Query Parameters:
    - tenant_id: Filter by tenant UUID
    - status: Filter by status (draft, published, deprecated)
    - category: Filter by category
    """
    templates = list_templates(
        session,
        tenant_id=tenant_id,
        status=status,
        category=category,
    )

    result = []
    for template in templates:
        latest_version = get_latest_version(session, template.id)
        result.append(TemplateListItem(
            id=str(template.id),
            name=template.name,
            description=template.description,
            category=template.category,
            status=template.status,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat(),
            latest_version_number=latest_version.version_number if latest_version else None,
        ))

    return result


@router.get("/{template_id}", response_model=TemplateDetail)
def get_template_details(
    template_id: UUID,
    session: Session = Depends(get_session),
):
    """
    Get detailed information about a template, including all versions.
    """
    template = get_template_by_id(session, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    versions = list_versions(session, template_id)
    version_details = [
        TemplateVersionDetail(
            id=str(v.id),
            template_id=str(v.template_id),
            version_number=v.version_number,
            frozen_definition=v.frozen_definition,
            changelog=v.changelog,
            published_by=v.published_by,
            published_at=v.published_at.isoformat(),
        )
        for v in versions
    ]

    return TemplateDetail(
        id=str(template.id),
        name=template.name,
        description=template.description,
        category=template.category,
        status=template.status,
        draft_definition=template.draft_definition,
        metadata=template.metadata,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
        versions=version_details,
    )


@router.put("/{template_id}/draft", response_model=UpdateTemplateDraftResponse)
def update_draft(
    template_id: UUID,
    req: UpdateTemplateDraftRequest,
    session: Session = Depends(get_session),
):
    """
    Update a template's draft definition.

    This endpoint modifies the working draft without creating a published version.
    Use the publish endpoint to create an immutable version.
    """
    try:
        template = update_template_draft(
            session,
            template_id=template_id,
            draft_definition=req.draft_definition,
            description=req.description,
            metadata=req.metadata,
        )

        return UpdateTemplateDraftResponse(
            template_id=str(template.id),
            name=template.name,
            status=template.status,
            updated_at=template.updated_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{template_id}/publish", response_model=PublishTemplateResponse)
def publish_template(
    template_id: UUID,
    req: PublishTemplateRequest,
    session: Session = Depends(get_session),
):
    """
    Publish a template's draft as a new immutable version.

    This endpoint:
    1. Validates the draft definition
    2. Creates a frozen immutable copy
    3. Increments the version number
    4. Updates template status to 'published'
    5. Emits a publish event

    Once published, versions cannot be modified (immutability).
    """
    try:
        result = publish_workflow_template(
            session,
            template_id=template_id,
            published_by=req.published_by,
            changelog=req.changelog,
        )

        return PublishTemplateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{template_id}/versions/{version_number}", response_model=TemplateVersionDetail)
def get_specific_version(
    template_id: UUID,
    version_number: int,
    session: Session = Depends(get_session),
):
    """
    Get a specific published version of a template.

    Returns the immutable frozen definition for the specified version.
    """
    version = get_version_by_number(session, template_id, version_number)
    if version is None:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version_number} not found for template {template_id}"
        )

    return TemplateVersionDetail(
        id=str(version.id),
        template_id=str(version.template_id),
        version_number=version.version_number,
        frozen_definition=version.frozen_definition,
        changelog=version.changelog,
        published_by=version.published_by,
        published_at=version.published_at.isoformat(),
    )


@router.get("/{template_id}/versions", response_model=list[TemplateVersionDetail])
def list_template_versions(
    template_id: UUID,
    session: Session = Depends(get_session),
):
    """
    List all published versions of a template.

    Returns versions in descending order (newest first).
    """
    versions = list_versions(session, template_id)

    return [
        TemplateVersionDetail(
            id=str(v.id),
            template_id=str(v.template_id),
            version_number=v.version_number,
            frozen_definition=v.frozen_definition,
            changelog=v.changelog,
            published_by=v.published_by,
            published_at=v.published_at.isoformat(),
        )
        for v in versions
    ]


@router.get("/{template_id}/latest", response_model=TemplateVersionDetail)
def get_latest_template_version(
    template_id: UUID,
    session: Session = Depends(get_session),
):
    """
    Get the latest published version of a template.

    This is a convenience endpoint for retrieving the most recent version
    without knowing the version number.
    """
    version = get_latest_version(session, template_id)
    if version is None:
        raise HTTPException(
            status_code=404,
            detail=f"No published versions found for template {template_id}"
        )

    return TemplateVersionDetail(
        id=str(version.id),
        template_id=str(version.template_id),
        version_number=version.version_number,
        frozen_definition=version.frozen_definition,
        changelog=version.changelog,
        published_by=version.published_by,
        published_at=version.published_at.isoformat(),
    )


@router.post("/{template_id}/versions/{version_id}/validate-immutability")
def validate_version_immutability(
    template_id: UUID,
    version_id: UUID,
    session: Session = Depends(get_session),
):
    """
    Validate that a published version remains immutable.

    This endpoint checks whether a version's frozen definition
    has been modified since creation (which should never happen).
    """
    try:
        is_immutable = enforce_immutability_rules(session, version_id)

        return {
            "version_id": str(version_id),
            "template_id": str(template_id),
            "is_immutable": is_immutable,
            "status": "valid" if is_immutable else "violation_detected",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
