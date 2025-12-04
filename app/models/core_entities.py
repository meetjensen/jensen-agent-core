from __future__ import annotations

from sqlalchemy import (
    Column,
    Text,
    DateTime,
    Integer,
    ForeignKey,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

# Try to reuse a shared Base from app._db if it exists.
# If that import fails (e.g., different structure), fall back to a local Base.
try:
    # If your project exposes a Base in app._db, this will reuse it.
    from app._db import Base  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    Base = declarative_base()  # type: ignore[assignment]


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    name = Column(Text, nullable=False, unique=True)
    type = Column(Text, nullable=False, server_default=text("'internal'"))
    status = Column(Text, nullable=False, server_default=text("'active'"))
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    workspaces = relationship(
        "Workspace",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    runs = relationship(
        "Run",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(Text, nullable=False)
    category = Column(Text, nullable=False)
    config_ref = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="workspaces")
    runs = relationship(
        "Run",
        back_populates="workspace",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Run(Base):
    __tablename__ = "runs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    kind = Column(Text, nullable=False)
    label = Column(Text, nullable=False)
    status = Column(Text, nullable=False, server_default=text("'pending'"))
    initiator = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="runs")
    workspace = relationship("Workspace", back_populates="runs")
    tasks = relationship(
        "Task",
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    agent_events = relationship(
        "AgentEvent",
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Task(Base):
    __tablename__ = "tasks"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    owner = Column(Text, nullable=False)  # 'platform' or 'workflow'
    title = Column(Text, nullable=False)
    status = Column(Text, nullable=False, server_default=text("'pending'"))
    priority = Column(Text, nullable=False, server_default=text("'normal'"))
    payload = Column(JSONB, nullable=False)
    result_ref = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    run = relationship("Run", back_populates="tasks")
    agent_events = relationship(
        "AgentEvent",
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AgentEvent(Base):
    __tablename__ = "agent_events"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor = Column(Text, nullable=False)
    step = Column(Integer, nullable=True)
    event_type = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    details = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    run = relationship("Run", back_populates="agent_events")
    task = relationship("Task", back_populates="agent_events")


class WorkflowTemplate(Base):
    """Workflow template metadata and draft definitions."""
    __tablename__ = "workflow_templates"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Text, nullable=False, server_default=text("'general'"))
    status = Column(Text, nullable=False, server_default=text("'draft'"))  # draft, published, deprecated
    draft_definition = Column(JSONB, nullable=True)  # Working draft
    metadata = Column(JSONB, nullable=True)  # Tags, author, etc.
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    tenant = relationship("Tenant")
    versions = relationship(
        "TemplateVersion",
        back_populates="template",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class TemplateVersion(Base):
    """Immutable published versions of workflow templates."""
    __tablename__ = "template_versions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number = Column(Integer, nullable=False)
    frozen_definition = Column(JSONB, nullable=False)  # Immutable snapshot
    changelog = Column(Text, nullable=True)  # What changed in this version
    published_by = Column(Text, nullable=False)  # User/actor who published
    published_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    template = relationship("WorkflowTemplate", back_populates="versions")
