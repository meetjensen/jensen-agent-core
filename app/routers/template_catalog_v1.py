"""
Phase G: Template Catalog API

REST API endpoints for workflow template catalog and version resolution.
"""
from __future__ import annotations

from typing import Generator, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app._db import DB_URL
from app.services import template_service
from app.workflows.compatibility import TemplateStatus, CompatibilityLevel
from app.workflows.template_schemas import (
    CreateTemplateRequest,
    CreateVersionRequest,
    ListTemplatesResponse,
    ListVersionsResponse,
    ResolveVersionRequest,
    ResolvedVersionResponse,
    TemplateResponse,
    UpdateVersionStatusRequest,
    VersionResponse,
)


# Database session setup
if not DB_URL:
    raise RuntimeError("DATABASE_URL is not set; template catalog cannot initialize")

_engine = create_engine(DB_URL, pool_pre_ping=True, future=True)
_SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    session: Session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


# Router setup
router = APIRouter(
    prefix="/internal/templates",
    tags=["templates"],
)


# ============================================================================
# Template Management Endpoints
# ============================================================================


@router.post("/", response_model=TemplateResponse, status_code=201)
def create_template(
    request: CreateTemplateRequest,
    session: Session = Depends(get_session),
):
    """
    Create a new workflow template.

    The template is a container for multiple versions of a workflow.
    """
    # Check if template_key already exists
    existing = template_service.get_template_by_key(session, request.template_key)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Template with key '{request.template_key}' already exists",
        )

    template = template_service.create_template(
        session,
        template_key=request.template_key,
        name=request.name,
        description=request.description,
        owner=request.owner,
    )

    return TemplateResponse(
        id=str(template.id),
        template_key=template.template_key,
        name=template.name,
        description=template.description,
        owner=template.owner,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.get("/", response_model=ListTemplatesResponse)
def list_templates(
    owner: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    """List all workflow templates."""
    templates, total = template_service.list_templates(
        session,
        owner=owner,
        limit=limit,
        offset=offset,
    )

    return ListTemplatesResponse(
        templates=[
            TemplateResponse(
                id=str(t.id),
                template_key=t.template_key,
                name=t.name,
                description=t.description,
                owner=t.owner,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in templates
        ],
        total=total,
    )


@router.get("/{template_key}", response_model=TemplateResponse)
def get_template(
    template_key: str,
    session: Session = Depends(get_session),
):
    """Get a specific template by key."""
    template = template_service.get_template_by_key(session, template_key)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return TemplateResponse(
        id=str(template.id),
        template_key=template.template_key,
        name=template.name,
        description=template.description,
        owner=template.owner,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


# ============================================================================
# Version Management Endpoints
# ============================================================================


@router.post("/versions", response_model=VersionResponse, status_code=201)
def create_version(
    request: CreateVersionRequest,
    session: Session = Depends(get_session),
):
    """
    Create a new version for a template.

    The compatibility level is auto-determined by comparing with
    the previous version unless explicitly provided.
    """
    # Get template
    template = template_service.get_template_by_key(session, request.template_key)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{request.template_key}' not found",
        )

    # Check if version already exists
    existing = template_service.get_version(
        session,
        template_key=request.template_key,
        version_major=request.version_major,
        version_minor=request.version_minor,
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Version {request.version_major}.{request.version_minor} already exists",
        )

    version = template_service.create_version(
        session,
        template_id=template.id,
        version_major=request.version_major,
        version_minor=request.version_minor,
        definition=request.definition,
        status=request.status,
        compatibility_level=request.compatibility_level,
    )

    return VersionResponse(
        id=str(version.id),
        template_id=str(version.template_id),
        version_major=version.version_major,
        version_minor=version.version_minor,
        status=version.status,
        compatibility_level=version.compatibility_level,
        structural_hash=version.structural_hash,
        definition=version.definition,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


@router.get("/{template_key}/versions", response_model=ListVersionsResponse)
def list_versions(
    template_key: str,
    status: Optional[TemplateStatus] = None,
    session: Session = Depends(get_session),
):
    """List all versions for a template."""
    # Verify template exists
    template = template_service.get_template_by_key(session, template_key)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    versions = template_service.list_versions(
        session,
        template_key=template_key,
        status=status,
    )

    return ListVersionsResponse(
        template_key=template_key,
        versions=[
            VersionResponse(
                id=str(v.id),
                template_id=str(v.template_id),
                version_major=v.version_major,
                version_minor=v.version_minor,
                status=v.status,
                compatibility_level=v.compatibility_level,
                structural_hash=v.structural_hash,
                definition=v.definition,
                created_at=v.created_at,
                updated_at=v.updated_at,
            )
            for v in versions
        ],
        total=len(versions),
    )


@router.get("/{template_key}/versions/{version_major}.{version_minor}", response_model=VersionResponse)
def get_version(
    template_key: str,
    version_major: int,
    version_minor: int,
    session: Session = Depends(get_session),
):
    """Get a specific version."""
    version = template_service.get_version(
        session,
        template_key=template_key,
        version_major=version_major,
        version_minor=version_minor,
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return VersionResponse(
        id=str(version.id),
        template_id=str(version.template_id),
        version_major=version.version_major,
        version_minor=version.version_minor,
        status=version.status,
        compatibility_level=version.compatibility_level,
        structural_hash=version.structural_hash,
        definition=version.definition,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


@router.patch("/versions/{version_id}/status", response_model=VersionResponse)
def update_version_status(
    version_id: UUID,
    request: UpdateVersionStatusRequest,
    session: Session = Depends(get_session),
):
    """Update the status of a version (e.g., promote draft to active)."""
    version = template_service.update_version_status(
        session,
        version_id=version_id,
        status=request.status,
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return VersionResponse(
        id=str(version.id),
        template_id=str(version.template_id),
        version_major=version.version_major,
        version_minor=version.version_minor,
        status=version.status,
        compatibility_level=version.compatibility_level,
        structural_hash=version.structural_hash,
        definition=version.definition,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


# ============================================================================
# Phase G: Version Resolution Endpoint
# ============================================================================


@router.post("/{template_key}/resolve", response_model=ResolvedVersionResponse)
def resolve_version(
    template_key: str,
    request: ResolveVersionRequest,
    session: Session = Depends(get_session),
):
    """
    Resolve the best version for a template using Phase G rules.

    Phase G Default Rules:
    - Select latest ACTIVE version
    - NOT breaking (exclude breaking compatibility level)
    - Allowed: additive + internal
    - Exclude: deprecated, draft (unless explicitly requested)

    If allow_breaking=True, breaking versions may be included.
    """
    # Override template_key from path if different in request
    if request.template_key != template_key:
        raise HTTPException(
            status_code=400,
            detail="Template key in path and request body must match",
        )

    result = template_service.resolve_version(
        session,
        template_key=template_key,
        version_major=request.version_major,
        version_minor=request.version_minor,
        allow_breaking=request.allow_breaking,
        allow_deprecated=request.allow_deprecated,
        allow_draft=request.allow_draft,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No suitable version found for template '{template_key}' with given constraints",
        )

    version, resolution_reason = result

    return ResolvedVersionResponse(
        template_key=template_key,
        version_major=version.version_major,
        version_minor=version.version_minor,
        version_id=str(version.id),
        status=version.status,
        compatibility_level=version.compatibility_level,
        definition=version.definition,
        resolution_reason=resolution_reason,
    )


@router.get("/{template_key}/resolve", response_model=ResolvedVersionResponse)
def resolve_version_get(
    template_key: str,
    version_major: Optional[int] = None,
    version_minor: Optional[int] = None,
    allow_breaking: bool = False,
    allow_deprecated: bool = False,
    allow_draft: bool = False,
    session: Session = Depends(get_session),
):
    """
    Resolve the best version for a template (GET variant).

    This is a convenience endpoint for simple version resolution without a request body.
    """
    result = template_service.resolve_version(
        session,
        template_key=template_key,
        version_major=version_major,
        version_minor=version_minor,
        allow_breaking=allow_breaking,
        allow_deprecated=allow_deprecated,
        allow_draft=allow_draft,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No suitable version found for template '{template_key}' with given constraints",
        )

    version, resolution_reason = result

    return ResolvedVersionResponse(
        template_key=template_key,
        version_major=version.version_major,
        version_minor=version.version_minor,
        version_id=str(version.id),
        status=version.status,
        compatibility_level=version.compatibility_level,
        definition=version.definition,
        resolution_reason=resolution_reason,
    )
