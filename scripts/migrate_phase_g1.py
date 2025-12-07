#!/usr/bin/env python3
"""
Phase G.1 Migration - Core Entities Schema

Creates Phase G.1 core orchestration tables:
- tenants
- workspaces
- runs
- tasks
- agent_events

EXECUTION ORDER: Run SECOND (after migrate_phase_g.py, though no strict dependency)
IDEMPOTENT: Safe to run multiple times (uses CREATE IF NOT EXISTS)

Usage:
    python scripts/migrate_phase_g1.py

Or in Docker container:
    docker exec jensen-agent python scripts/migrate_phase_g1.py

Dependencies:
    - PostgreSQL database with DATABASE_URL configured
    - uuid-ossp extension (auto-enabled by this script)
    - No dependency on Phase G tables (workflow_templates/workflow_template_versions)

Created tables:
    1. tenants - Multi-tenancy support
    2. workspaces - Tenant-scoped workspace configuration
    3. runs - Workflow execution runs
    4. tasks - Individual tasks within runs
    5. agent_events - Audit trail for agent actions

Related migrations:
    - migrate_phase_g.py - Creates template catalog schema (independent)

Run this script to apply the migration to your database.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine
except ImportError:
    print("Error: sqlalchemy not installed. Run: pip install sqlalchemy psycopg2-binary")
    sys.exit(1)


def get_database_url() -> str:
    """Get database URL from environment or use default."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        # Construct from individual components
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "jensen")
        db_user = os.getenv("DB_USER", "jensen")
        db_pass = os.getenv("DB_PASSWORD", "")

        if db_pass:
            db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        else:
            db_url = f"postgresql://{db_user}@{db_host}:{db_port}/{db_name}"

    return db_url


def create_migration_engine() -> Engine:
    """Create SQLAlchemy engine for migration."""
    db_url = get_database_url()
    print(f"Connecting to database...")
    return create_engine(db_url, echo=True)


def run_migration(engine: Engine) -> None:
    """Execute the Phase G.1 migration."""

    migration_sql = """
    -- Phase G.1 Migration: Core Entities Schema
    -- Generated: 2025-12-06

    -- Enable UUID extension (if not already enabled)
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    -- ============================
    -- 1) TENANTS
    -- ============================
    CREATE TABLE IF NOT EXISTS tenants (
        id          uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        name        text NOT NULL UNIQUE,
        type        text NOT NULL DEFAULT 'internal',  -- e.g., 'internal', 'client'
        status      text NOT NULL DEFAULT 'active',    -- e.g., 'active', 'inactive'
        created_at  timestamptz NOT NULL DEFAULT now()
    );

    CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants (status);


    -- ============================
    -- 2) WORKSPACES
    -- ============================
    CREATE TABLE IF NOT EXISTS workspaces (
        id           uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        tenant_id    uuid NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
        name         text NOT NULL,
        category     text NOT NULL,                    -- e.g., 'email', 'marketing', 'voice'
        config_ref   jsonb,                            -- inline config or pointer
        created_at   timestamptz NOT NULL DEFAULT now()
    );

    -- A tenant cannot have two workspaces with the same name.
    CREATE UNIQUE INDEX IF NOT EXISTS uq_workspaces_tenant_name ON workspaces (tenant_id, name);
    CREATE INDEX IF NOT EXISTS idx_workspaces_tenant_category ON workspaces (tenant_id, category);


    -- ============================
    -- 3) RUNS
    -- ============================
    CREATE TABLE IF NOT EXISTS runs (
        id            uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        tenant_id     uuid NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
        workspace_id  uuid REFERENCES workspaces (id) ON DELETE SET NULL,
        kind          text NOT NULL,                  -- e.g., 'workflow_execution', 'infra_change', 'config_change'
        label         text NOT NULL,                  -- human-readable label
        status        text NOT NULL DEFAULT 'pending',-- 'pending', 'in_progress', 'completed', 'failed', 'cancelled'
        initiator     text NOT NULL,                  -- e.g., 'operator:jensen', 'schedule:08:00-daily'
        notes         text,                           -- optional free-form notes
        created_at    timestamptz NOT NULL DEFAULT now(),
        started_at    timestamptz,
        finished_at   timestamptz
    );

    CREATE INDEX IF NOT EXISTS idx_runs_tenant_workspace_kind ON runs (tenant_id, workspace_id, kind);
    CREATE INDEX IF NOT EXISTS idx_runs_status_created_at ON runs (status, created_at DESC);


    -- ============================
    -- 4) TASKS
    -- ============================
    CREATE TABLE IF NOT EXISTS tasks (
        id           uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        run_id       uuid NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
        owner        text NOT NULL,                     -- 'platform' or 'workflow'
        title        text NOT NULL,
        status       text NOT NULL DEFAULT 'pending',   -- 'pending', 'in_progress', 'completed', 'blocked', 'cancelled'
        priority     text NOT NULL DEFAULT 'normal',    -- 'low', 'normal', 'high'
        payload      jsonb NOT NULL,                    -- Task brief (GOAL, CONTEXT, REQUIREMENTS, etc.)
        result_ref   text,                              -- pointer to artifact (path, document ID, etc.)
        created_at   timestamptz NOT NULL DEFAULT now(),
        updated_at   timestamptz NOT NULL DEFAULT now()
    );

    CREATE INDEX IF NOT EXISTS idx_tasks_run ON tasks (run_id);
    CREATE INDEX IF NOT EXISTS idx_tasks_owner_status ON tasks (owner, status);
    CREATE INDEX IF NOT EXISTS idx_tasks_status_priority ON tasks (status, priority);


    -- ============================
    -- 5) AGENT_EVENTS
    -- ============================
    CREATE TABLE IF NOT EXISTS agent_events (
        id             uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
        run_id         uuid NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
        task_id        uuid REFERENCES tasks (id) ON DELETE SET NULL,
        actor          text NOT NULL,                     -- 'orchestrator', 'platform', 'workflow', 'operator:<id>', etc.
        step           integer,                           -- optional sequence number within the run/task
        event_type     text NOT NULL,                     -- 'task_created', 'task_routed', 'task_started', 'task_completed', ...
        summary        text NOT NULL,                     -- short human-readable summary
        details        jsonb,                             -- structured details payload
        created_at     timestamptz NOT NULL DEFAULT now()
    );

    CREATE INDEX IF NOT EXISTS idx_agent_events_run_created_at ON agent_events (run_id, created_at);
    CREATE INDEX IF NOT EXISTS idx_agent_events_task ON agent_events (task_id);
    CREATE INDEX IF NOT EXISTS idx_agent_events_actor_type ON agent_events (actor, event_type);


    -- ============================
    -- 6) TRIGGER FOR TASKS.UPDATED_AT
    -- ============================

    -- Create trigger function if it doesn't exist
    CREATE OR REPLACE FUNCTION set_tasks_updated_at()
    RETURNS trigger AS $$
    BEGIN
        NEW.updated_at = now();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    -- Drop trigger if exists (to avoid errors on re-run)
    DROP TRIGGER IF EXISTS tr_tasks_set_updated_at ON tasks;

    -- Create trigger
    CREATE TRIGGER tr_tasks_set_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION set_tasks_updated_at();
    """

    print("\n" + "="*70)
    print("Starting Phase G.1 Migration")
    print("="*70 + "\n")

    with engine.begin() as conn:
        # Execute migration
        conn.execute(text(migration_sql))
        print("\n✓ Migration completed successfully!")

    print("\n" + "="*70)
    print("Phase G.1 Migration Summary")
    print("="*70)
    print("\nCreated tables:")
    print("  • tenants")
    print("  • workspaces")
    print("  • runs")
    print("  • tasks")
    print("  • agent_events")
    print("\nCreated indexes:")
    print("  • idx_tenants_status")
    print("  • uq_workspaces_tenant_name (unique)")
    print("  • idx_workspaces_tenant_category")
    print("  • idx_runs_tenant_workspace_kind")
    print("  • idx_runs_status_created_at")
    print("  • idx_tasks_run")
    print("  • idx_tasks_owner_status")
    print("  • idx_tasks_status_priority")
    print("  • idx_agent_events_run_created_at")
    print("  • idx_agent_events_task")
    print("  • idx_agent_events_actor_type")
    print("\nCreated triggers:")
    print("  • tr_tasks_set_updated_at (auto-updates tasks.updated_at)")
    print("\n" + "="*70 + "\n")


def verify_migration(engine: Engine) -> None:
    """Verify that all tables were created successfully."""

    print("Verifying migration...")

    verification_sql = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('tenants', 'workspaces', 'runs', 'tasks', 'agent_events')
    ORDER BY table_name;
    """

    with engine.begin() as conn:
        result = conn.execute(text(verification_sql))
        tables = [row[0] for row in result]

    expected_tables = ['agent_events', 'runs', 'tasks', 'tenants', 'workspaces']

    if set(tables) == set(expected_tables):
        print(f"✓ All {len(expected_tables)} tables verified successfully!")
        for table in sorted(tables):
            print(f"  • {table}")
    else:
        missing = set(expected_tables) - set(tables)
        if missing:
            print(f"✗ Missing tables: {', '.join(missing)}")
            sys.exit(1)


def main():
    """Main migration execution."""

    print("Phase G.1 Migration Script")
    print("-" * 70)

    try:
        # Create engine
        engine = create_migration_engine()

        # Run migration
        run_migration(engine)

        # Verify migration
        verify_migration(engine)

        print("\n✓ Phase G.1 migration completed successfully!\n")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
