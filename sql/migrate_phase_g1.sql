-- ============================================================================
-- Phase G.1 Migration: Core Entities Schema
-- ============================================================================
-- Generated: 2025-12-06
--
-- This migration creates the Phase G core entities tables:
--   • tenants       - Multi-tenant isolation
--   • workspaces    - Logical workspaces within tenants
--   • runs          - Execution runs (workflows, operations)
--   • tasks         - Individual tasks within runs
--   • agent_events  - Event log for agent activities
--
-- This migration is idempotent and safe to run multiple times.
-- ============================================================================

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

COMMENT ON TABLE tenants IS 'Multi-tenant isolation - each tenant has its own workspaces and runs';
COMMENT ON COLUMN tenants.type IS 'Tenant type: internal, client, partner, etc.';
COMMENT ON COLUMN tenants.status IS 'Tenant status: active, inactive, suspended, etc.';


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

COMMENT ON TABLE workspaces IS 'Logical workspaces within tenants for organizing work';
COMMENT ON COLUMN workspaces.category IS 'Workspace category: email, marketing, voice, data, etc.';
COMMENT ON COLUMN workspaces.config_ref IS 'Configuration reference (inline JSON or external pointer)';


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

COMMENT ON TABLE runs IS 'Execution runs - workflows, operations, infrastructure changes';
COMMENT ON COLUMN runs.kind IS 'Run type: workflow_execution, infra_change, config_change, etc.';
COMMENT ON COLUMN runs.status IS 'Run status: pending, in_progress, completed, failed, cancelled';
COMMENT ON COLUMN runs.initiator IS 'Who/what initiated the run: operator:name, schedule:cron, webhook:source';


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

COMMENT ON TABLE tasks IS 'Individual tasks within runs - assigned to platform or workflow agents';
COMMENT ON COLUMN tasks.owner IS 'Task owner: platform (system-managed) or workflow (user-defined)';
COMMENT ON COLUMN tasks.status IS 'Task status: pending, in_progress, completed, blocked, cancelled';
COMMENT ON COLUMN tasks.priority IS 'Task priority: low, normal, high, critical';
COMMENT ON COLUMN tasks.payload IS 'Task brief with GOAL, CONTEXT, REQUIREMENTS, etc. (JSONB)';
COMMENT ON COLUMN tasks.result_ref IS 'Reference to task result (file path, document ID, URL, etc.)';


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

COMMENT ON TABLE agent_events IS 'Event log for all agent activities - creates audit trail';
COMMENT ON COLUMN agent_events.actor IS 'Who performed the action: orchestrator, platform, workflow, operator:name';
COMMENT ON COLUMN agent_events.step IS 'Optional step/sequence number for ordering events';
COMMENT ON COLUMN agent_events.event_type IS 'Event type: task_created, task_routed, task_started, task_completed, etc.';
COMMENT ON COLUMN agent_events.summary IS 'Human-readable summary of the event';
COMMENT ON COLUMN agent_events.details IS 'Structured event details (JSONB)';


-- ============================
-- 6) TRIGGER FOR TASKS.UPDATED_AT
-- ============================

-- This trigger keeps tasks.updated_at in sync with changes.
-- If you prefer to handle updated_at in application code, you can drop this trigger.

CREATE OR REPLACE FUNCTION set_tasks_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION set_tasks_updated_at() IS 'Trigger function to automatically update tasks.updated_at on row updates';

-- Drop trigger if exists (to avoid errors on re-run)
DROP TRIGGER IF EXISTS tr_tasks_set_updated_at ON tasks;

-- Create trigger
CREATE TRIGGER tr_tasks_set_updated_at
BEFORE UPDATE ON tasks
FOR EACH ROW
EXECUTE FUNCTION set_tasks_updated_at();


-- ============================================================================
-- Migration Complete
-- ============================================================================
-- The Phase G core entities schema has been created successfully.
-- Tables: tenants, workspaces, runs, tasks, agent_events
-- Indexes: 11 indexes for efficient querying
-- Triggers: 1 trigger for auto-updating tasks.updated_at
-- ============================================================================
