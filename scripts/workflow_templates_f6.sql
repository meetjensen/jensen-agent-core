-- workflow_templates_f6.sql
-- Phase F6: Workflow Template Catalog with Compatibility Metadata

-- ============================
-- 1) WORKFLOW_TEMPLATES
-- ============================
CREATE TABLE workflow_templates (
    id           uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    key          text NOT NULL UNIQUE,           -- e.g., 'approval.basic'
    name         text NOT NULL,
    description  text,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_workflow_templates_key ON workflow_templates (key);


-- ============================
-- 2) WORKFLOW_TEMPLATE_VERSIONS
-- ============================
CREATE TABLE workflow_template_versions (
    id                   uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id          uuid NOT NULL REFERENCES workflow_templates (id) ON DELETE CASCADE,
    version              text NOT NULL,                         -- e.g., '1.0.0'
    definition           jsonb NOT NULL,                        -- The workflow definition
    status               text NOT NULL DEFAULT 'draft',         -- 'draft', 'published', 'deprecated'

    -- F6 Compatibility Metadata Fields
    compatibility_level  text NOT NULL DEFAULT 'unknown',       -- 'breaking', 'additive', 'internal', 'unknown'
    change_summary       text,                                  -- Human-readable explanation
    structural_hash      text,                                  -- SHA-256 of normalized definition

    published_at         timestamptz,
    created_at           timestamptz NOT NULL DEFAULT now()
);

-- Ensure a template cannot have duplicate versions
CREATE UNIQUE INDEX uq_template_versions ON workflow_template_versions (template_id, version);

-- Indexes for common queries
CREATE INDEX idx_template_versions_template_id ON workflow_template_versions (template_id);
CREATE INDEX idx_template_versions_status ON workflow_template_versions (status);
CREATE INDEX idx_template_versions_compatibility ON workflow_template_versions (compatibility_level);
CREATE INDEX idx_template_versions_hash ON workflow_template_versions (structural_hash);


-- ============================
-- 3) TRIGGER FOR UPDATED_AT
-- ============================
CREATE OR REPLACE FUNCTION set_workflow_templates_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_workflow_templates_set_updated_at
BEFORE UPDATE ON workflow_templates
FOR EACH ROW
EXECUTE FUNCTION set_workflow_templates_updated_at();
