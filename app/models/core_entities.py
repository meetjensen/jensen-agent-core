from __future__ import annotations

from uuid import UUID as PyUUID

from sqlalchemy import (
    Column,
    Text,
    DateTime,
    Integer,
    Boolean,
    ForeignKey,
    text,
)
from sqlalchemy.types import JSON, TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func


class UUID(TypeDecorator):
    """Platform-independent UUID type.

    Uses PostgreSQL's UUID type when available, otherwise uses
    CHAR(36) storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def __init__(self, as_uuid=True):
        """Accept as_uuid parameter for PostgreSQL compatibility."""
        super().__init__()
        self.as_uuid = as_uuid

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=self.as_uuid))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, PyUUID):
                return str(value)
            else:
                return str(PyUUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if isinstance(value, PyUUID):
                return value
            else:
                return PyUUID(value)

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


# Phase G: Workflow Template Catalog Models


class WorkflowTemplate(Base):
    """
    Workflow template catalog entry.
    Each template has a unique template_key and can have multiple versions.
class WorkflowTemplate(Base):
    """
    A workflow template catalog entry.
    Each template has a unique key (e.g., 'approval.basic') and multiple versions.
    """

    __tablename__ = "workflow_templates"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    key = Column(Text, nullable=False, unique=True)  # e.g., 'approval.basic'
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Text, nullable=False)
    tags = Column(JSONB, nullable=True)
    status = Column(Text, nullable=False, server_default=text("'draft'"))
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
        "WorkflowTemplateVersion",
        back_populates="template",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="WorkflowTemplateVersion.created_at.desc()",
    )


class WorkflowTemplateVersion(Base):
    """
    A specific version of a workflow template with F6 compatibility metadata.
    Includes semantic awareness fields: compatibility_level, change_summary, structural_hash.
    """

    __tablename__ = "workflow_template_versions"

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
    version_major = Column(Integer, nullable=False)
    version_minor = Column(Integer, nullable=False)
    status = Column(
        Text,
        nullable=False,
        server_default=text("'draft'"),
    )  # 'draft', 'published', 'deprecated'

    # F6 Compatibility Metadata Fields
    compatibility_level = Column(
        Text,
        nullable=False,
        server_default=text("'unknown'"),
    )  # 'breaking', 'additive', 'internal', 'unknown'
    structural_hash = Column(Text, nullable=True)
    definition = Column(JSONB, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    template = relationship("WorkflowTemplate", back_populates="versions")
