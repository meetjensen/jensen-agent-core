"""
Phase G: Template Catalog Schemas

Pydantic models for template catalog API requests and responses.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.workflows.compatibility import TemplateStatus, CompatibilityLevel


# ============================================================================
# Template Creation & Management
# ============================================================================


class CreateTemplateRequest(BaseModel):
    """Request to create a new workflow template."""

    template_key: str = Field(..., description="Unique template identifier")
    name: str = Field(..., description="Human-readable template name")
    description: Optional[str] = Field(None, description="Template description")
    owner: str = Field(..., description="Owner of the template")


class TemplateResponse(BaseModel):
    """Response containing template information."""

    id: str
    template_key: str
    name: str
    description: Optional[str]
    owner: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Version Creation & Management
# ============================================================================


class CreateVersionRequest(BaseModel):
    """Request to create a new template version."""

    template_key: str = Field(..., description="Template identifier")
    version_major: int = Field(..., description="Major version number", ge=0)
    version_minor: int = Field(..., description="Minor version number", ge=0)
    definition: Dict[str, Any] = Field(..., description="Workflow definition")
    status: TemplateStatus = Field(
        TemplateStatus.DRAFT,
        description="Version status (active/deprecated/draft)",
    )
    compatibility_level: Optional[CompatibilityLevel] = Field(
        None,
        description="Compatibility level (breaking/additive/internal)",
    )


class VersionResponse(BaseModel):
    """Response containing version information."""

    id: str
    template_id: str
    version_major: int
    version_minor: int
    status: str
    compatibility_level: str
    structural_hash: Optional[str]
    definition: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Version Resolution
# ============================================================================


class ResolveVersionRequest(BaseModel):
    """Request to resolve the best version for a template."""

    template_key: str = Field(..., description="Template identifier")
    version_major: Optional[int] = Field(
        None,
        description="Required major version (None = latest)",
    )
    version_minor: Optional[int] = Field(
        None,
        description="Required minor version (None = latest)",
    )
    allow_breaking: bool = Field(
        False,
        description="Allow breaking changes",
    )
    allow_deprecated: bool = Field(
        False,
        description="Allow deprecated versions",
    )
    allow_draft: bool = Field(
        False,
        description="Allow draft versions",
    )


class ResolvedVersionResponse(BaseModel):
    """Response containing the resolved version."""

    template_key: str
    version_major: int
    version_minor: int
    version_id: str
    status: str
    compatibility_level: str
    definition: Dict[str, Any]
    resolution_reason: str = Field(
        ...,
        description="Explanation of why this version was selected",
    )


# ============================================================================
# List Operations
# ============================================================================


class ListTemplatesResponse(BaseModel):
    """Response containing list of templates."""

    templates: List[TemplateResponse]
    total: int


class ListVersionsResponse(BaseModel):
    """Response containing list of versions for a template."""

    template_key: str
    versions: List[VersionResponse]
    total: int


# ============================================================================
# Version Update
# ============================================================================


class UpdateVersionStatusRequest(BaseModel):
    """Request to update a version's status."""

    status: TemplateStatus = Field(..., description="New status")
