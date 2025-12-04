"""
Phase F6: Workflow Template API Router

API endpoints for managing workflow templates with compatibility metadata.
"""

from __future__ import annotations

from typing import Generator, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app._db import DB_URL
from app.workflows import catalog_service
from app.workflows.catalog_service import (
    DuplicateVersionError,
    TemplateNotFoundError,
    VersionNotFoundError,
)

if not DB_URL:
    raise RuntimeError("DATABASE_URL (DB_URL) is not set; cannot use templates router")

_engine = create_engine(DB_URL, pool_pre_ping=True, future=True)
_SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB Session and closes it afterwards."""
    session: Session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


router = APIRouter(
    prefix="/api/templates",
    tags=["templates"],
)


# ==================== Pydantic Models ====================


class TemplateResponse(BaseModel):
    id: str
    key: str
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str
    version_count: int


class VersionResponse(BaseModel):
    id: str
    template_id: str
    version: str
    status: str
    compatibility_level: str
    change_summary: Optional[str]
    structural_hash: Optional[str]
    published_at: Optional[str]
    created_at: str


class VersionDetailResponse(VersionResponse):
    definition: dict


class PublishVersionRequest(BaseModel):
    template_key: str
    version: str
    definition: dict
    name: str
    description: Optional[str] = None
    compatibility_level: Optional[str] = None
    change_summary: Optional[str] = None
    auto_publish: bool = True


class AssessCompatibilityRequest(BaseModel):
    template_key: str
    definition: dict


class AssessCompatibilityResponse(BaseModel):
    inferred_level: str
    structural_hash: str
    diff: Optional[dict]
    change_summary: str
    previous_version: Optional[str]


class UpdateMetadataRequest(BaseModel):
    compatibility_level: Optional[str] = None
    change_summary: Optional[str] = None


# ==================== Endpoints ====================


@router.get("/", response_model=List[TemplateResponse])
def list_templates(
    session: Session = Depends(get_session),
):
    """List all workflow templates."""
    templates = catalog_service.list_templates(session)

    return [
        TemplateResponse(
            id=str(template.id),
            key=template.key,
            name=template.name,
            description=template.description,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat(),
            version_count=len(template.versions) if template.versions else 0,
        )
        for template in templates
    ]


@router.get("/{template_key}", response_model=TemplateResponse)
def get_template(
    template_key: str,
    session: Session = Depends(get_session),
):
    """Get a specific template by key."""
    template = catalog_service.get_template(session, template_key)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_key} not found")

    return TemplateResponse(
        id=str(template.id),
        key=template.key,
        name=template.name,
        description=template.description,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
        version_count=len(template.versions) if template.versions else 0,
    )


@router.get("/{template_key}/versions", response_model=List[VersionResponse])
def list_versions(
    template_key: str,
    status: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """List all versions of a template."""
    # Verify template exists
    template = catalog_service.get_template(session, template_key)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_key} not found")

    versions = catalog_service.list_versions(session, template_key, status)

    return [
        VersionResponse(
            id=str(version.id),
            template_id=str(version.template_id),
            version=version.version,
            status=version.status,
            compatibility_level=version.compatibility_level,
            change_summary=version.change_summary,
            structural_hash=version.structural_hash,
            published_at=version.published_at.isoformat() if version.published_at else None,
            created_at=version.created_at.isoformat(),
        )
        for version in versions
    ]


@router.get("/{template_key}/versions/{version}", response_model=VersionDetailResponse)
def get_version(
    template_key: str,
    version: str,
    session: Session = Depends(get_session),
):
    """Get a specific version of a template including its definition."""
    version_obj = catalog_service.get_version(session, template_key, version)
    if not version_obj:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version} not found for template {template_key}",
        )

    return VersionDetailResponse(
        id=str(version_obj.id),
        template_id=str(version_obj.template_id),
        version=version_obj.version,
        definition=version_obj.definition,
        status=version_obj.status,
        compatibility_level=version_obj.compatibility_level,
        change_summary=version_obj.change_summary,
        structural_hash=version_obj.structural_hash,
        published_at=version_obj.published_at.isoformat() if version_obj.published_at else None,
        created_at=version_obj.created_at.isoformat(),
    )


@router.post("/versions", response_model=VersionResponse)
def publish_version(
    request: PublishVersionRequest,
    session: Session = Depends(get_session),
):
    """
    Create and optionally publish a new version of a workflow template.

    If the template doesn't exist, it will be created.
    Compatibility assessment is performed automatically.
    """
    try:
        version = catalog_service.publish_version(
            session,
            template_key=request.template_key,
            version=request.version,
            definition=request.definition,
            name=request.name,
            description=request.description,
            compatibility_level=request.compatibility_level,
            change_summary=request.change_summary,
            auto_publish=request.auto_publish,
        )
        session.commit()

        return VersionResponse(
            id=str(version.id),
            template_id=str(version.template_id),
            version=version.version,
            status=version.status,
            compatibility_level=version.compatibility_level,
            change_summary=version.change_summary,
            structural_hash=version.structural_hash,
            published_at=version.published_at.isoformat() if version.published_at else None,
            created_at=version.created_at.isoformat(),
        )
    except DuplicateVersionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to publish version: {str(e)}")


@router.post("/versions/assess", response_model=AssessCompatibilityResponse)
def assess_compatibility(
    request: AssessCompatibilityRequest,
    session: Session = Depends(get_session),
):
    """
    Assess the compatibility of a proposed workflow definition.

    Returns compatibility analysis without creating a version.
    """
    assessment = catalog_service.assess_compatibility(
        session,
        template_key=request.template_key,
        new_definition=request.definition,
    )

    return AssessCompatibilityResponse(
        inferred_level=assessment["inferred_level"],
        structural_hash=assessment["structural_hash"],
        diff=assessment["diff"],
        change_summary=assessment["change_summary"],
        previous_version=assessment["previous_version"],
    )


@router.patch("/versions/{version_id}/metadata", response_model=VersionResponse)
def update_version_metadata(
    version_id: str,
    request: UpdateMetadataRequest,
    session: Session = Depends(get_session),
):
    """
    Update the metadata of a template version.

    Allows manual correction of automatically inferred compatibility data.
    """
    try:
        version_uuid = UUID(version_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid version_id format")

    try:
        version = catalog_service.update_version_metadata(
            session,
            version_id=version_uuid,
            compatibility_level=request.compatibility_level,
            change_summary=request.change_summary,
        )
        session.commit()

        return VersionResponse(
            id=str(version.id),
            template_id=str(version.template_id),
            version=version.version,
            status=version.status,
            compatibility_level=version.compatibility_level,
            change_summary=version.change_summary,
            structural_hash=version.structural_hash,
            published_at=version.published_at.isoformat() if version.published_at else None,
            created_at=version.created_at.isoformat(),
        )
    except VersionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update metadata: {str(e)}")
