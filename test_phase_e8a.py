#!/usr/bin/env python3
"""
Test script for Phase E8.A - Minimal Full Workflow Runner.

This script:
1. Creates a test run and workflow task
2. Calls orchestrate_single_cycle
3. Verifies the expected results
"""
from __future__ import annotations

import sys
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app._db import DB_URL
from app.models.core_entities import Tenant, Workspace, Run, Task, AgentEvent
from app.services.core_runs import create_run, create_task
from app.orchestrator import orchestrate_single_cycle


def test_workflow_execution():
    """Test the minimal workflow execution."""
    print("=" * 80)
    print("Phase E8.A - Minimal Full Workflow Runner Test")
    print("=" * 80)
    print()

    if not DB_URL:
        print("ERROR: DATABASE_URL (DB_URL) is not set")
        return False

    # Create engine and session
    engine = create_engine(DB_URL, pool_pre_ping=True, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()

    try:
        # Step 1: Get or create tenant
        print("Step 1: Getting or creating tenant...")
        tenant = session.query(Tenant).filter(Tenant.name == "Jensen").first()
        if tenant is None:
            tenant = Tenant(name="Jensen", type="internal", status="active")
            session.add(tenant)
            session.commit()
            session.refresh(tenant)
            print(f"  ✓ Created tenant: {tenant.id}")
        else:
            print(f"  ✓ Found existing tenant: {tenant.id}")
        print()

        # Step 2: Get or create workspace
        print("Step 2: Getting or creating workspace...")
        workspace = (
            session.query(Workspace)
            .filter(
                Workspace.tenant_id == tenant.id,
                Workspace.name == "E8A Test Workspace",
            )
            .first()
        )
        if workspace is None:
            workspace = Workspace(
                tenant_id=tenant.id,
                name="E8A Test Workspace",
                category="test",
                config_ref={},
            )
            session.add(workspace)
            session.commit()
            session.refresh(workspace)
            print(f"  ✓ Created workspace: {workspace.id}")
        else:
            print(f"  ✓ Found existing workspace: {workspace.id}")
        print()

        # Step 3: Create a new run
        print("Step 3: Creating a new run...")
        run = create_run(
            session,
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            kind="workflow_execution",
            label="Phase E8.A Test Run",
            initiator="test_script",
            notes="Testing minimal workflow runner",
        )
        print(f"  ✓ Created run: {run.id}")
        print()

        # Step 4: Create a workflow task
        print("Step 4: Creating a workflow task...")
        task = create_task(
            session,
            run_id=run.id,
            owner="workflow",
            title="Test Workflow Execution",
            payload={"workflow_id": "hello"},
            priority="normal",
            status="pending",
        )
        print(f"  ✓ Created task: {task.id}")
        print(f"     Owner: {task.owner}")
        print(f"     Status: {task.status}")
        print(f"     Payload: {task.payload}")
        print()

        # Step 5: Execute orchestration cycle
        print("Step 5: Executing orchestration cycle...")
        result = orchestrate_single_cycle(session, run_id=run.id)
        print(f"  ✓ Orchestration result:")
        print(f"     Status: {result.get('status')}")
        print(f"     Owner: {result.get('owner')}")
        print(f"     Task ID: {result.get('task_id')}")
        print(f"     Workflow ID: {result.get('workflow_id')}")
        print(f"     Workflow Name: {result.get('workflow_name')}")
        print(f"     Steps Executed: {result.get('steps_executed')}")
        print(f"     Events: {result.get('events')}")
        print()

        # Step 6: Verify task status
        print("Step 6: Verifying task status...")
        session.refresh(task)
        print(f"  ✓ Task status after execution: {task.status}")
        if task.status != "completed":
            print(f"  ✗ ERROR: Expected status 'completed', got '{task.status}'")
            return False
        print()

        # Step 7: Verify events
        print("Step 7: Verifying events...")
        events = (
            session.query(AgentEvent)
            .filter(AgentEvent.run_id == run.id)
            .order_by(AgentEvent.created_at.asc())
            .all()
        )
        print(f"  ✓ Found {len(events)} events:")
        for i, event in enumerate(events, 1):
            print(f"     {i}. {event.event_type}: {event.summary}")
            if event.details:
                print(f"        Details: {event.details}")
        print()

        # Step 8: Verify expected events
        print("Step 8: Verifying expected event types...")
        event_types = [e.event_type for e in events]
        expected_events = [
            "task_dispatched",
            "workflow_started",
            "workflow_step_noop",
            "workflow_completed",
        ]

        missing_events = [e for e in expected_events if e not in event_types]
        if missing_events:
            print(f"  ✗ ERROR: Missing expected events: {missing_events}")
            print(f"     Found events: {event_types}")
            return False

        print(f"  ✓ All expected events found:")
        for event_type in expected_events:
            print(f"     - {event_type}")
        print()

        # Step 9: Verify orchestration summary
        print("Step 9: Verifying orchestration summary...")
        checks = [
            ("status", "dispatched", result.get("status")),
            ("owner", "workflow", result.get("owner")),
            ("steps_executed", 1, result.get("steps_executed")),
        ]

        all_passed = True
        for check_name, expected, actual in checks:
            if actual == expected:
                print(f"  ✓ {check_name}: {actual} (expected {expected})")
            else:
                print(f"  ✗ {check_name}: {actual} (expected {expected})")
                all_passed = False

        if not all_passed:
            return False
        print()

        print("=" * 80)
        print("✓ Phase E8.A test PASSED!")
        print("=" * 80)
        return True

    except Exception as e:
        print()
        print("=" * 80)
        print(f"✗ Phase E8.A test FAILED with error:")
        print(f"  {type(e).__name__}: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return False

    finally:
        session.close()


if __name__ == "__main__":
    success = test_workflow_execution()
    sys.exit(0 if success else 1)
