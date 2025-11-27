-- core_entities_v1.sql

-- Enable UUID generation (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================
-- 1) TENANTS
-- ============================
CREATE TABLE tenants (
    id          uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        text NOT NULL UNIQUE,
    type        text NOT NULL DEFAULT 'internal',  -- e.g., 'internal', 'client'
    status      text NOT NULL DEFAULT 'active',    -- e.g., 'active', 'inactive'
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_tenants_status ON tenants (status);


-- ============================
-- 2) WORKSPACES
-- ============================
CREATE TABLE workspaces (
    id           uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id    uuid NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    name         text NOT NULL,
    category     text NOT NULL,                    -- e.g., 'email', 'marketing', 'voice'
    config_ref   jsonb,                            -- inline config or pointer
    created_at   timestamptz NOT NULL DEFAULT now()
);

-- A tenant cannot have two workspaces with the same name.
CREATE UNIQUE INDEX uq_workspaces_tenant_name ON workspaces (tenant_id, name);
CREATE INDEX idx_workspaces_tenant_category ON workspaces (tenant_id, category);


-- ============================
-- 3) RUNS
-- ============================
CREATE TABLE runs (
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

CREATE INDEX idx_runs_tenant_workspace_kind ON runs (tenant_id, workspace_id, kind);
CREATE INDEX idx_runs_status_created_at ON runs (status, created_at DESC);


-- ============================
-- 4) TASKS
-- ============================
CREATE TABLE tasks (
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

-- Keep updated_at fresh via trigger if desired (optional, shown later).
CREATE INDEX idx_tasks_run ON tasks (run_id);
CREATE INDEX idx_tasks_owner_status ON tasks (owner, status);
CREATE INDEX idx_tasks_status_priority ON tasks (status, priority);


-- ============================
-- 5) AGENT_EVENTS
-- ============================
CREATE TABLE agent_events (
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

CREATE INDEX idx_agent_events_run_created_at ON agent_events (run_id, created_at);
CREATE INDEX idx_agent_events_task ON agent_events (task_id);
CREATE INDEX idx_agent_events_actor_type ON agent_events (actor, event_type);


-- ============================
-- 6) OPTIONAL TRIGGERS FOR UPDATED_AT
-- ============================

-- This trigger keeps tasks.updated_at in sync with changes.
-- If you prefer to handle updated_at in application code, you can omit this.

CREATE OR REPLACE FUNCTION set_tasks_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_tasks_set_updated_at
BEFORE UPDATE ON tasks
FOR EACH ROW
EXECUTE FUNCTION set_tasks_updated_at();

