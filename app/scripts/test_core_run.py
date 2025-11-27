from __future__ import annotations

import sys
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app._db import DB_URL
from app.models.core_entities import Tenant, Workspace
from app.services.core_runs import create_run, create_task, log_agent_event


def get_session() -> Session:
    """
    Obtain a SQLAlchemy Session using the same DATABASE_URL the app uses.

    We import DB_URL from app._db and create a one-off engine + SessionLocal
    for this smoke test. This does NOT change the main app's DB behavior.
    """
    if not DB_URL:
        raise RuntimeError("DATABASE_URL is not set; cannot create Session")

    engine = create_engine(DB_URL, pool_pre_ping=True, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return SessionLocal()


def get_or_create_tenant(session: Session, name: str = "Jensen") -> tuple[Tenant, bool]:
    """
    Ensure a Tenant with the given name exists.

    Returns (tenant, created_flag).
    """
    tenant = session.query(Tenant).filter(Tenant.name == name).first()
    created = False

    if tenant is None:
        tenant = Tenant(
            name=name,
            type="internal",
            status="active",
        )
        session.add(tenant)
        session.commit()
        session.refresh(tenant)
        created = True

    return tenant, created


def get_or_create_workspace(
    session: Session,
    tenant: Tenant,
    name: str = "Core Test Workspace",
    category: str = "test",
) -> tuple[Workspace, bool]:
    """
    Ensure a Workspace with the given name exists for the given tenant.

    Returns (workspace, created_flag).
    """
    workspace = (
        session.query(Workspace)
        .filter(
            Workspace.tenant_id == tenant.id,
            Workspace.name == name,
        )
        .first()
    )
    created = False

    if workspace is None:
        workspace = Workspace(
            tenant_id=tenant.id,
            name=name,
            category=category,
            config_ref={},
        )
        session.add(workspace)
        session.commit()
        session.refresh(workspace)
        created = True

    return workspace, created


def main(argv: Optional[list[str]] = None) -> int:
    """
    Core OS smoke test:

    - Ensure Tenant 'Jensen' exists.
    - Ensure Workspace 'Core Test Workspace' exists for that tenant.
    - Create a Run, Task, and AgentEvent using the core_runs helpers.
    - Print the IDs and whether tenant/workspace were newly created.
    """
    if argv is None:
        argv = sys.argv[1:]

    session: Optional[Session] = None

    try:
        session = get_session()

        # 1) Tenant
        tenant, tenant_created = get_or_create_tenant(session, name="Jensen")

        # 2) Workspace
        workspace, workspace_created = get_or_create_workspace(
            session,
            tenant=tenant,
            name="Core Test Workspace",
            category="test",
        )

        # 3) Run
        run = create_run(
            session,
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            kind="test_run",
            label="Core OS smoke test",
            initiator="operator:jensen",
            notes="Created via scripts/test_core_run.py",
        )

        # 4) Task
        task = create_task(
            session,
            run_id=run.id,
            owner="platform",
            title="Core OS smoke test task",
            payload={"info": "test payload from test_core_run"},
            priority="normal",
            status="pending",
            result_ref=None,
        )

        # 5) AgentEvent
        event = log_agent_event(
            session,
            run_id=run.id,
            task_id=task.id,
            actor="orchestrator",
            event_type="smoke_test",
            summary="Created test run/task/event via test_core_run.py",
            details={"note": "smoke test"},
            step=1,
        )

        # 6) Print results
        tenant_state = "new" if tenant_created else "existing"
        workspace_state = "new" if workspace_created else "existing"

        print(f"Created Tenant: {tenant.id} ({tenant_state})")
        print(f"Created Workspace: {workspace.id} ({workspace_state})")
        print(f"Created Run: {run.id}")
        print(f"Created Task: {task.id}")
        print(f"Created AgentEvent: {event.id}")

        return 0

    except Exception as exc:
        print("ERROR: test_core_run.py failed:", exc, file=sys.stderr)
        return 1

    finally:
        if session is not None:
            session.close()


if __name__ == "__main__":
    raise SystemExit(main())
