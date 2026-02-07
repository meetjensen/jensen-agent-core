# CLAUDE.md — Jensen Agent Core

## Project Overview

Jensen Agent Core is a self-contained FastAPI microservice that orchestrates AI workflows with multi-provider LLM support (OpenAI, Anthropic). It runs in Docker on a Synology NAS and is exposed via reverse proxy. The project follows a phased development approach building toward a full AI agent orchestration platform.

Current phase: **E8.A** — minimal full workflow runner with sequential noop step execution.

## Tech Stack

- **Language**: Python 3.11
- **Framework**: FastAPI + Uvicorn ASGI
- **Database**: PostgreSQL via SQLAlchemy 2.0 ORM + psycopg2
- **LLM Providers**: OpenAI (`openai` SDK), Anthropic (`anthropic` SDK)
- **Templates**: Jinja2
- **Deployment**: Docker Compose on Synology NAS

## Repository Structure

```
jensen-agent-core/
├── app/                          # Main application package
│   ├── main.py                   # FastAPI app entry point, routes, middleware
│   ├── _db.py                    # Database engine, table definitions (actions/jobs/audits)
│   ├── _path_bootstrap.py        # Path initialization
│   ├── orchestrator.py           # Task dispatch logic (Phase E8.A)
│   ├── models/
│   │   └── core_entities.py      # SQLAlchemy ORM: Tenant, Workspace, Run, Task, AgentEvent
│   ├── services/
│   │   ├── core_runs.py          # CRUD helpers for Runs, Tasks, AgentEvents
│   │   ├── llm_gateway.py        # Multi-provider LLM abstraction
│   │   ├── job_runner.py         # Background job execution
│   │   ├── audit_watcher.py      # Audit trail tracking
│   │   └── registry.py           # Service registry
│   ├── engines/
│   │   ├── platform_engine.py    # Abstract PlatformEngine + DbPlatformEngine
│   │   └── workflow_engine.py    # DbWorkflowEngine (plan + run workflows)
│   ├── workflows/
│   │   ├── schemas.py            # Pydantic: WorkflowDefinition, WorkflowStep
│   │   ├── loader.py             # Load workflows from YAML/JSON files
│   │   ├── runner.py             # WorkflowRunner (sequential step execution)
│   │   └── examples/             # Example workflow definitions
│   ├── routers/                  # FastAPI routers (18+ modules)
│   │   ├── core_orchestrator_v1.py  # /internal/core/orchestrator/* endpoints
│   │   ├── core_runs_debug.py       # Run debug endpoints
│   │   ├── chat_model.py            # Chat API
│   │   └── ...                      # metrics, audit, actions, jobs, export, etc.
│   ├── integrations/
│   │   └── exporter.py           # Export to HTTP/S3
│   ├── static/                   # CSS, images, login page
│   └── templates/                # Jinja2 HTML templates
├── scripts/                      # Operational/deployment scripts
├── templates/                    # Additional templates
├── Dockerfile                    # Python 3.11-slim, ffmpeg, uvicorn
├── docker-compose.yml            # Single service on jensen-net
├── Makefile                      # dev, logs, down, restart, smoke, backup
├── requirements.txt              # Python dependencies (no versions pinned for most)
├── deploy.sh                     # Deployment with health checks
└── start.sh                      # Container startup
```

## Key Architecture

### Entity Hierarchy (multi-tenant)

```
Tenant → Workspace → Run → Task → AgentEvent
```

All entities use UUID primary keys with PostgreSQL `uuid_generate_v4()`.

### Orchestration Flow

1. **API request** hits `/internal/core/orchestrator/run`
2. **Orchestrator** creates Tenant, Workspace, Run, Task, and initial AgentEvent
3. **`orchestrate_single_cycle()`** finds pending tasks and dispatches by `task.owner`:
   - `owner='workflow'` → `DbWorkflowEngine.run_workflow()`
   - `owner='platform'` → `DbPlatformEngine.process_next_task()`
4. **WorkflowRunner** executes steps sequentially (only `noop` type in Phase E8.A)
5. Events are logged at every step for full audit trail

### LLM Gateway

`app/services/llm_gateway.py` provides `call_chat_llm()` — a unified function supporting:
- **OpenAI**: env `OPENAI_API_KEY`, model defaults to `gpt-5.1`
- **Anthropic**: env `ANTHROPIC_API_KEY` + `ANTHROPIC_MODEL`
- Provider selection: `provider` arg → `LLM_PROVIDER` env → `"openai"` default

### Router Pattern

Routers in `app/routers/` are included in `main.py` with try/except wrappers, allowing graceful degradation if a module's dependencies are unavailable. Each router defines its own `APIRouter` with a prefix and tags.

## Development Commands

```bash
# Build and run (Docker Compose)
make dev

# View logs
make logs

# Stop
make down

# Restart
make restart

# Smoke test (health, version, chat)
make smoke

# Backup
make backup
```

The app runs on port 8000. Entry point: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

## Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | For orchestrator | — | PostgreSQL connection string |
| `OPENAI_API_KEY` | For OpenAI LLM | — | OpenAI authentication |
| `ANTHROPIC_API_KEY` | For Anthropic LLM | — | Anthropic authentication |
| `ANTHROPIC_MODEL` | For Anthropic LLM | — | Claude model name |
| `LLM_PROVIDER` | No | `"openai"` | Default LLM provider |
| `AGENT_TOKEN` | No | `"jensen4254"` | API auth token (X-Agent-Token header) |
| `ADMIN_USER` / `ADMIN_PASS` | No | `"admin"` / `"ChangeMeNow!"` | Web UI login |
| `SECRET_KEY` | No | `"change-this-please"` | Session middleware secret |
| `APP_VERSION` | No | `"dev"` | Reported by /version |
| `INTEGRATIONS_ENABLED` | No | `"false"` | Enable DB integrations worker |
| `DATA_DIR` | No | `"/app/data"` | Data directory path |

## Testing

There is no formal test framework (pytest) configured. Tests exist as standalone scripts:
- `test_phase_e8a.py` — integration test for workflow execution
- `app/scripts/test_core_run.py` — core run testing
- `scripts/test_core_run.py` — additional test utilities

Tests require a running PostgreSQL database with the correct schema.

## Code Conventions

### Style

- No linter or formatter is configured (no black, ruff, flake8, pylint)
- Imports are organized: `__future__` → stdlib → third-party → local
- Type hints are used throughout (`from __future__ import annotations` at top of modules)
- Docstrings follow NumPy/Google hybrid style with `Parameters`, `Returns`, `Raises` sections

### Patterns

- **Service layer**: Business logic lives in `app/services/`, not in routers
- **Session injection**: SQLAlchemy sessions are passed via FastAPI `Depends(get_session)`
- **Try/except imports**: Optional features wrapped in try/except to avoid startup failures
- **Pydantic models**: Used for API request/response schemas and workflow definitions
- **`from __future__ import annotations`**: Present in all core modules for forward references
- **Keyword-only arguments**: Service functions use `*` to enforce keyword arguments

### Naming

- Router files: `<feature>_ro.py` (read-only) or `<feature>_rw.py` (read-write)
- Internal APIs prefixed with `/internal/`
- Event types use snake_case: `task_created`, `workflow_started`, `platform_stub_handled`
- Task owners: `"orchestrator"`, `"platform"`, `"workflow"`
- Task statuses: `"pending"`, `"handled"`, `"completed"`

### Phased Development

The project follows numbered phases (E1, E2, ... E8.A). Each phase builds on the previous:
- E1–E2: Engine skeleton (abstract PlatformEngine, WorkflowEngine)
- E3–E4: Workflow schemas and loader
- E5: PlatformEngine task consumer
- E6: WorkflowEngine stub
- E7: Orchestrator dispatcher
- E8.A: Full workflow runner (current)

Commit messages reference the phase: `"Phase E8.A: Add minimal full workflow runner"`.

## Versioning

Semantic versioning (`MAJOR.MINOR.PATCH`). When bumping versions, update:
- `app/main.py` — `APP_VERSION` constant
- `README.md` and `API.md` headers
- `CHANGELOG.md`

## API Authentication

- **Token auth**: Most API endpoints require `X-Agent-Token` header matching `AGENT_TOKEN` env var
- **Session auth**: Web UI uses session cookies via `SessionMiddleware` (login at `/auth/login`)
- **Health/version**: `/health` and `/version` are unauthenticated

## Key Endpoints

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/health` | GET | None | Liveness check |
| `/version` | GET | None | App version |
| `/chat_live` | POST | Token | LLM-backed chat |
| `/internal/core/orchestrator/run` | POST | None | Create orchestrated run |
| `/internal/core/orchestrator/task/update` | POST | None | Update task status |
| `/internal/core/orchestrator/run/{id}/debug` | GET | None | Debug view of run |
| `/ui/*` | GET | Session | Protected web UI pages |
| `/metrics` | GET | None | Prometheus metrics |
