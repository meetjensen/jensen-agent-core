# Phase G: Template Catalog & Version Resolution

## Overview

**Phase G** is the JENSEN Core AI OS's workflow template versioning and resolution system. It enables safe evolution of workflow definitions through semantic versioning with automatic compatibility analysis.

### What is Phase G?

Phase G provides:

1. **Template Catalog** - Central repository for versioned workflow definitions
2. **Compatibility Framework** - Automatic classification of changes (breaking/additive/internal)
3. **Version Resolution Engine** - Intelligent selection of the best version based on constraints
4. **Safe Evolution** - Workflows can evolve without breaking existing runs

### When to Use Phase G

Use Phase G when you need to:

- **Version workflow definitions** - Maintain multiple versions of the same workflow
- **Safely evolve workflows** - Make changes without breaking existing integrations
- **A/B test workflows** - Deploy multiple versions simultaneously
- **Gradual rollouts** - Control which version gets used by different consumers
- **Track workflow history** - Audit trail of all changes with compatibility classification

---

## Core Concepts

### Templates

A **template** is a named container for versioned workflow definitions.

**Properties:**
- `template_key` - Unique identifier (e.g., `"email-drip-campaign"`)
- `name` - Human-readable name
- `description` - Documentation
- `owner` - Team/person responsible
- `created_at`, `updated_at` - Timestamps

**Example:**
```json
{
  "template_key": "welcome-email-sequence",
  "name": "Welcome Email Sequence",
  "description": "Onboarding email drip campaign for new users",
  "owner": "marketing-team"
}
```

### Versions

Each template can have multiple **versions**, identified by `major.minor` version numbers.

**Properties:**
- `version_major`, `version_minor` - Semantic version (e.g., 1.2)
- `definition` - Complete workflow definition (JSONB)
- `status` - Lifecycle state: `active`, `deprecated`, `draft`
- `compatibility_level` - Change classification: `breaking`, `additive`, `internal`, `unknown`
- `structural_hash` - SHA256 hash of workflow structure (first 16 chars)
- `created_at`, `updated_at` - Timestamps

**Example:**
```json
{
  "template_key": "welcome-email-sequence",
  "version_major": 1,
  "version_minor": 2,
  "definition": {
    "steps": [
      {"id": "send_welcome", "type": "email", "inputs": {...}, "outputs": {...}},
      {"id": "send_tutorial", "type": "email", "inputs": {...}, "outputs": {...}}
    ]
  },
  "status": "active",
  "compatibility_level": "additive"
}
```

---

## Compatibility Levels

Phase G automatically classifies changes between versions into four compatibility levels:

### 1. BREAKING (Major Version Bump Recommended)

Changes that **break backward compatibility** and require consumers to update.

**Examples:**
- Removing a step
- Changing a step type
- Removing an output field
- Renaming step IDs

**Version Strategy:** Increment major version (1.x → 2.0)

**Example:**
```python
# Version 1.0
{
  "steps": [
    {"id": "step-1", "type": "email", "outputs": {"result": "..."}}
  ]
}

# Version 2.0 (BREAKING - step type changed)
{
  "steps": [
    {"id": "step-1", "type": "sms", "outputs": {"result": "..."}}
  ]
}
```

### 2. ADDITIVE (Minor Version Bump Recommended)

Changes that **add functionality** without breaking existing behavior.

**Examples:**
- Adding a new step
- Adding a new output field to an existing step
- Adding optional input parameters

**Version Strategy:** Increment minor version (1.0 → 1.1)

**Example:**
```python
# Version 1.0
{
  "steps": [
    {"id": "step-1", "type": "email", "outputs": {}}
  ]
}

# Version 1.1 (ADDITIVE - new step added)
{
  "steps": [
    {"id": "step-1", "type": "email", "outputs": {}},
    {"id": "step-2", "type": "email", "outputs": {}}  # NEW
  ]
}
```

### 3. INTERNAL (Patch Version Semantics)

Changes to **internal implementation only** - no structural changes.

**Examples:**
- Updating descriptions
- Changing input/output values (not keys)
- Updating metadata

**Version Strategy:** No version increment needed (or patch: 1.0.0 → 1.0.1)

**Example:**
```python
# Version 1.0
{
  "steps": [
    {"id": "step-1", "type": "email", "inputs": {"subject": "Hello"}}
  ]
}

# Version 1.1 (INTERNAL - only input value changed)
{
  "steps": [
    {"id": "step-1", "type": "email", "inputs": {"subject": "Hello World"}}
  ]
}
```

### 4. UNKNOWN

Compatibility level could not be determined automatically.

**When this occurs:**
- First version of a template (nothing to compare against)
- Unusual changes that don't fit other categories

**Action Required:** Manually set `compatibility_level` when creating the version.

---

## Version Resolution Rules

The **resolution engine** selects the best version based on Phase G default rules and optional constraints.

### Phase G Default Rules

When resolving a version **without constraints**:

1. ✅ Select **latest ACTIVE** version
2. ❌ Exclude **BREAKING** compatibility level
3. ✅ Allow: `additive` + `internal` + `unknown`
4. ❌ Exclude: `deprecated` and `draft` status

**Example:**

Given these versions:
- v1.0 (active, internal)
- v1.1 (active, additive)
- v1.2 (active, additive)
- v2.0 (active, breaking)

**Default resolution** → Returns **v1.2** (latest active, non-breaking)

### Resolution Constraints

Override default behavior with optional constraints:

| Constraint | Type | Default | Description |
|-----------|------|---------|-------------|
| `version_major` | int | None | Constrain to specific major version |
| `version_minor` | int | None | Exact version (requires version_major) |
| `allow_breaking` | bool | False | Include breaking changes |
| `allow_deprecated` | bool | False | Include deprecated versions |
| `allow_draft` | bool | False | Include draft versions |

### Resolution Examples

#### Example 1: Default Resolution
```bash
GET /internal/templates/welcome-email-sequence/resolve
```
Returns: Latest active, non-breaking version

#### Example 2: Allow Breaking Changes
```bash
GET /internal/templates/welcome-email-sequence/resolve?allow_breaking=true
```
Returns: Latest active version (including breaking)

#### Example 3: Major Version Constraint
```bash
GET /internal/templates/welcome-email-sequence/resolve?version_major=1
```
Returns: Latest active, non-breaking version within v1.x

#### Example 4: Exact Version
```bash
GET /internal/templates/welcome-email-sequence/resolve?version_major=1&version_minor=2
```
Returns: Exactly v1.2 (if it exists)

#### Example 5: Include Deprecated
```bash
GET /internal/templates/welcome-email-sequence/resolve?allow_deprecated=true
```
Returns: Latest non-breaking version (including deprecated)

---

## API Usage

### Creating a Template

```bash
POST /internal/templates/
Content-Type: application/json

{
  "template_key": "email-welcome-sequence",
  "name": "Welcome Email Sequence",
  "description": "Onboarding email drip campaign",
  "owner": "marketing-team"
}
```

**Response: 201 Created**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "template_key": "email-welcome-sequence",
  "name": "Welcome Email Sequence",
  "description": "Onboarding email drip campaign",
  "owner": "marketing-team",
  "created_at": "2025-12-07T10:00:00Z",
  "updated_at": "2025-12-07T10:00:00Z"
}
```

### Creating a Version

```bash
POST /internal/templates/versions
Content-Type: application/json

{
  "template_key": "email-welcome-sequence",
  "version_major": 1,
  "version_minor": 0,
  "definition": {
    "steps": [
      {
        "id": "send_welcome",
        "type": "email",
        "inputs": {"subject": "Welcome!", "body": "..."},
        "outputs": {}
      }
    ]
  },
  "status": "active"
}
```

**Response: 201 Created**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "template_id": "550e8400-e29b-41d4-a716-446655440000",
  "version_major": 1,
  "version_minor": 0,
  "status": "active",
  "compatibility_level": "additive",
  "structural_hash": "a1b2c3d4e5f67890",
  "definition": {...},
  "created_at": "2025-12-07T10:05:00Z",
  "updated_at": "2025-12-07T10:05:00Z"
}
```

**Note:** `compatibility_level` is auto-determined by comparing with the previous version.

### Resolving a Version

```bash
GET /internal/templates/email-welcome-sequence/resolve
```

**Response: 200 OK**
```json
{
  "template_key": "email-welcome-sequence",
  "version_major": 1,
  "version_minor": 2,
  "version_id": "660e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "compatibility_level": "additive",
  "definition": {...},
  "resolution_reason": "Latest version 1.2, status=active, compatibility=additive"
}
```

### Listing Versions

```bash
GET /internal/templates/email-welcome-sequence/versions
```

**Response: 200 OK**
```json
{
  "template_key": "email-welcome-sequence",
  "versions": [
    {"version_major": 2, "version_minor": 0, "status": "active", ...},
    {"version_major": 1, "version_minor": 2, "status": "active", ...},
    {"version_major": 1, "version_minor": 1, "status": "deprecated", ...},
    {"version_major": 1, "version_minor": 0, "status": "deprecated", ...}
  ],
  "total": 4
}
```

---

## Orchestrator Integration

### Using template_key in Workflow Execution

The orchestrator's `DbWorkflowEngine` supports executing workflows by `template_key` instead of providing a full definition.

**Example:**
```python
from app.engines.workflow_engine import DbWorkflowEngine

engine = DbWorkflowEngine(session)

# Execute using template_key (Phase G resolves the version)
result = engine.run_workflow(
    template_key="email-welcome-sequence",
    workspace_config={...},
)
```

**How it works:**
1. Engine calls `template_service.resolve_version(template_key)`
2. Phase G applies default rules (latest active, non-breaking)
3. Returns resolved version's `definition`
4. Engine executes the workflow

**Override resolution:**
```python
# Use specific major version
result = engine.run_workflow(
    template_key="email-welcome-sequence",
    version_major=1,  # Constrain to v1.x
    workspace_config={...},
)

# Allow breaking changes
result = engine.run_workflow(
    template_key="email-welcome-sequence",
    allow_breaking=True,  # Include v2.0 breaking changes
    workspace_config={...},
)
```

---

## Troubleshooting

### Error: "Template 'X' not found"

**Cause:** The template_key does not exist in the catalog.

**Solution:**
1. Verify template_key spelling
2. List all templates: `GET /internal/templates/`
3. Create template if needed: `POST /internal/templates/`

### Error: "Version X.Y not found for template 'Z'"

**Cause:** Requested exact version doesn't exist.

**Solution:**
1. List available versions: `GET /internal/templates/Z/versions`
2. Check version numbers
3. Create missing version or request a different version

### Error: "No suitable version found for template 'X'"

**Cause:** No versions match the resolution constraints.

**Common scenarios:**

#### Scenario 1: Only breaking versions available
```
Template has: v2.0 (breaking)
Default request: excludes breaking
```
**Solution:** Set `allow_breaking=true`

#### Scenario 2: Only deprecated versions available
```
Template has: v1.0 (deprecated)
Default request: excludes deprecated
```
**Solution:** Set `allow_deprecated=true`

#### Scenario 3: Only draft versions available
```
Template has: v1.0 (draft)
Default request: excludes draft
```
**Solution:** Set `allow_draft=true` OR promote version to active status

#### Scenario 4: No versions in requested major version
```
Template has: v2.0, v2.1
Request: version_major=1
```
**Solution:** Remove major version constraint or create v1.x versions

### Resolution Not Returning Expected Version

**Check:**
1. **Status** - Is the version `active`? (Deprecated/draft excluded by default)
2. **Compatibility** - Is it `breaking`? (Excluded by default)
3. **Version ordering** - Latest version is selected; older versions ignored
4. **Constraints** - Are `version_major`/`version_minor` constraining results?

**Debug:**
- List all versions: `GET /internal/templates/{key}/versions`
- Check logs for resolution decisions (structured logging enabled)
- Try with `allow_breaking=true`, `allow_deprecated=true` to see all candidates

### Version Auto-Classification Incorrect

**Cause:** Compatibility auto-determination compares workflow structure, which may not capture semantic meaning.

**Solution:**
Manually override `compatibility_level` when creating version:

```json
{
  "template_key": "my-workflow",
  "version_major": 2,
  "version_minor": 0,
  "definition": {...},
  "compatibility_level": "breaking"  // Manual override
}
```

---

## Best Practices

### Versioning Strategy

1. **First version**: Start at v1.0
2. **Additive changes**: Increment minor (1.0 → 1.1)
3. **Breaking changes**: Increment major (1.x → 2.0)
4. **Internal changes**: Consider keeping version number, just update metadata

### Status Lifecycle

1. **Draft** → Use for testing and development
2. **Active** → Production-ready versions
3. **Deprecated** → Mark old versions for removal (still functional)

**Example workflow:**
```
Create v1.0 as draft
→ Test v1.0
→ Promote to active
→ Create v1.1 as draft
→ Test v1.1
→ Promote v1.1 to active
→ Deprecate v1.0 (but keep for existing consumers)
```

### Template Naming

- Use lowercase with hyphens: `email-welcome-sequence`
- Be descriptive: `customer-onboarding-workflow` not `workflow-1`
- Group by domain: `email-*`, `voice-*`, `analytics-*`

### Documentation

- Always provide `description` for templates
- Document breaking changes in version notes
- Maintain changelog outside Phase G for major changes

---

## Database Schema

### Tables

#### workflow_templates
```sql
CREATE TABLE workflow_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    owner TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### workflow_template_versions
```sql
CREATE TABLE workflow_template_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL REFERENCES workflow_templates(id) ON DELETE CASCADE,
    version_major INTEGER NOT NULL,
    version_minor INTEGER NOT NULL,
    definition JSONB NOT NULL,
    status TEXT NOT NULL,  -- 'active', 'deprecated', 'draft'
    compatibility_level TEXT NOT NULL,  -- 'breaking', 'additive', 'internal', 'unknown'
    structural_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (template_id, version_major, version_minor)
);
```

---

## Monitoring & Observability

### Structured Logging

Phase G logs all resolution decisions with structured data:

**Successful resolution:**
```json
{
  "level": "info",
  "message": "Version resolved successfully",
  "template_key": "email-welcome-sequence",
  "resolved_version": "1.2",
  "version_id": "660e8400-...",
  "status": "active",
  "compatibility_level": "additive",
  "resolution_reason": "Latest version 1.2, status=active, compatibility=additive",
  "constraints": {
    "version_major": null,
    "version_minor": null,
    "allow_breaking": false,
    "allow_deprecated": false,
    "allow_draft": false
  }
}
```

**Failed resolution:**
```json
{
  "level": "warning",
  "message": "Version resolution failed: no matching versions",
  "template_key": "email-welcome-sequence",
  "reason": "no_matching_versions",
  "constraints": {...}
}
```

### Metrics (if Prometheus enabled)

- `phase_g_resolutions_total{template_key, status, compatibility_level}` - Total resolutions
- `phase_g_resolution_failures_total{template_key, reason}` - Failed resolutions
- `phase_g_resolution_duration_seconds` - Resolution latency

---

## Migration

### Running Migrations

```bash
# Phase G migration (template catalog)
docker exec jensen-agent python scripts/migrate_phase_g.py

# Phase G.1 migration (core entities)
docker exec jensen-agent python scripts/migrate_phase_g1.py
```

**Execution Order:** Run `migrate_phase_g.py` first, then `migrate_phase_g1.py` (though no strict dependency)

**Idempotency:** Both migrations are safe to run multiple times

---

## Related Systems

### Phase F5/F6 (Legacy Template System)

Phase G **coexists** with the older Phase F5/F6 template system:

- **Phase F5/F6**: Uses sequential version numbers, different API (`/api/template-publisher`, `/api/templates`)
- **Phase G**: Uses semantic versioning (major.minor), new API (`/internal/templates`)

**Migration Path:** Phase F5/F6 will be deprecated in favor of Phase G, but both systems remain functional for now.

### G-Engine (Future)

Phase G provides the **foundation** for G-Engine, a future meta-governance supervisor that will handle:
- Automated A/B testing
- Gradual rollout strategies
- Performance-based version selection
- Multi-tenant version isolation

G-Engine will consume Phase G's resolution API to intelligently route workflow executions.

---

## Support

For issues or questions:
- Check logs: `docker logs jensen-agent --tail=50`
- Run tests: `pytest test_phase_g.py test_phase_g_e2e.py -v`
- Review this documentation
- Contact the JENSEN Core AI OS team

---

**Last Updated:** 2025-12-07
**Version:** Phase G v1.0
**Status:** Production-Ready
