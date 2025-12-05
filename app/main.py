# =============================================================================
# Early initialization (before other imports)
# =============================================================================
from dotenv import load_dotenv

# --- safe optional import to avoid NameError in /ui/admin/links ---
try:
    from app.ui_admin_links_fix import get_admin_links_page
except Exception:
    get_admin_links_page = None

load_dotenv(dotenv_path="/app/.env", override=True)
from app import _path_bootstrap as _bp
from pathlib import Path

def _choose_templates_dir():
    # Support both layouts: /app/templates AND /app/app/templates
    candidates = [
        Path(__file__).resolve().parent / "templates",
        Path("/app/templates"),
        Path("/app/app/templates"),
    ]
    for d in candidates:
        if d.exists():
            return d
    return candidates[0]

TEMPLATES_DIR = _choose_templates_dir()

def _resolve_tpl(name: str) -> Path:
    return (TEMPLATES_DIR / name)

FALLBACK_ADMIN_LINKS_HTML = """<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Operator Links</title><style>
body{font:14px/1.45 -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:24px}
nav a{margin-right:10px}.muted{color:#666}.panel{max-width:840px;margin:0 auto}
</style></head><body><div class="panel"><header><nav>
<a class="tab" href="/ui">Home</a>
<a class="tab" href="/ui/admin/links">Admin Links</a>
<a class="tab" href="/ui/logs">Raw Logs</a>
<a class="tab" href="/auth/logout">Logout</a>
</nav></header><main class="panel"><h1>Operator Links</h1><div id="links"></div></main></div>
<script>
(async () => {
  try {
    const r = await fetch('/ops/links',{credentials:'include'});
    const data = await r.json(); const items = (data.links||data);
    document.getElementById('links').innerHTML =
      '<ul>' + items.map(x => `<li><a href="${x.url}" target="_blank" rel="noopener">${x.name}</a>${x.section? ' — <span class="muted">'+x.section+'</span>':''}</li>`).join('') + '</ul>';
  } catch(e) { document.getElementById('links').textContent = 'Failed to load /ops/links'; }
})();
</script></body></html>"""

APP_DIR = Path(__file__).resolve().parent  # e.g. /app/app

# =============================================================================
# Standard library imports
# =============================================================================
import os
import time
import json
import asyncio
from collections import deque
from datetime import datetime
from typing import Optional, Dict

# =============================================================================
# Third-party imports
# =============================================================================
from fastapi import FastAPI, Request, Depends, HTTPException, Header, Form
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette import status
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel

# =============================================================================
# Environment variables
# =============================================================================
APP_VERSION = os.getenv("APP_VERSION") or "dev"
AGENT_TOKEN    = os.getenv("AGENT_TOKEN", "jensen4254")
ADMIN_USER     = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS     = os.getenv("ADMIN_PASS", "ChangeMeNow!")
SECRET_KEY     = os.getenv("SECRET_KEY", "change-this-please")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LINKS_PATH = os.getenv("OPERATOR_LINKS_PATH") or str(Path(os.getenv("DATA_DIR", "/app/data")) / "operator_links.json")

# =============================================================================
# App creation + process metrics
# =============================================================================
# Process start timestamp for uptime
START_TS = globals().get("START_TS", time.time())

def _rss_bytes():
    # Prefer /proc/self/statm for portable RSS on Linux
    try:
        with open("/proc/self/statm","r") as f:
            parts = f.read().split()
        rss_pages = int(parts[1])
        page_size = os.sysconf("SC_PAGE_SIZE")
        return rss_pages * page_size
    except Exception:
        try:
            import resource
            v = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # On Linux ru_maxrss is KB; on others it may be bytes
            return int(v*1024) if v < 10**9 else int(v)
        except Exception:
            return 0

app = FastAPI()

# =============================================================================
# Router includes (consolidated - one per router)
# =============================================================================
# Diagnostics
from app.routers import diag_env as _diag_env
app.include_router(_diag_env.router)

from app import diag_ro as _diag
app.include_router(_diag.router)

from app import diagnostics as _diagnostics
app.include_router(_diagnostics.router)

# Integrations
try:
    from app.routers import integrations_pg as _integrations_pg
    app.include_router(_integrations_pg.router)
except Exception:
    pass

try:
    from app.routers import integrations_ro as _integrations_ro
    app.include_router(_integrations_ro.router)
except Exception:
    pass

# Export & Archives
try:
    from app.routers import export_ro as _export_ro
    app.include_router(_export_ro.router)
except Exception:
    pass

try:
    from app.routers import exporter_ro as _exporter_ro
    app.include_router(_exporter_ro.router)
except Exception:
    pass

try:
    from app.routers import archives_ro as _archives_ro
    app.include_router(_archives_ro.router)
except Exception:
    pass

# Metrics, Audit, Actions, Jobs
try:
    from app.routers import metrics_ro as _metrics_ro
    app.include_router(_metrics_ro.router)
except Exception:
    pass

try:
    from app.routers import audit_ro as _audit_ro
    app.include_router(_audit_ro.router)
except Exception:
    pass

try:
    from app.routers import actions_rw as _actions_rw
    app.include_router(_actions_rw.router)
except Exception:
    pass

try:
    from app.routers import jobs_rw as _jobs_rw
    app.include_router(_jobs_rw.router)
except Exception:
    pass

# Chat & LLM
try:
    from app.routers import chat_model as _chat_model
    app.include_router(_chat_model.router)
except Exception:
    pass

# Audio & LLM routers
try:
    from .audio_router import router as audio_router
    app.include_router(audio_router)
except Exception:
    pass

try:
    from .llm_router import router as llm_router
    app.include_router(llm_router)
except Exception:
    pass

# Core orchestrator
try:
    from app.routers import core_runs_debug as _core_runs_debug
    app.include_router(_core_runs_debug.router)
except Exception:
    pass

try:
    from app.routers import core_orchestrator_v1 as _core_orchestrator_v1
    app.include_router(_core_orchestrator_v1.router)
except Exception:
    pass

try:
    from app.routers import orchestrator_ui as _orchestrator_ui
    app.include_router(_orchestrator_ui.router)
except Exception:
    pass

# Phase G: Template Catalog
try:
    from app.routers import template_catalog_v1 as _template_catalog_v1
    app.include_router(_template_catalog_v1.router)
except Exception:
    pass

# =============================================================================
# Middleware & state setup
# =============================================================================
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, https_only=False, same_site="lax")

# In-memory recent access log
app.state.logs = deque(maxlen=200)

# Static files
try:
    STATIC_ROOT = Path("/app/app/static")
    if STATIC_ROOT.exists():
        app.mount("/static", StaticFiles(directory=str(_bp.STATIC_DIR)), name="static")
except Exception:
    pass

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# =============================================================================
# Helper functions
# =============================================================================
def log_line(req: Request, msg: str):
    t = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    host = getattr(req.client, "host", "-")
    app.state.logs.append(f"[{t}] {host} {req.method} {req.url.path} :: {msg}")

def require_login(request: Request):
    if not request.session.get("user"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return request.session["user"]

def _ctx(request: Request, user: str, **extra):
    base = {
        "request": request,
        "user": user,
        "token": AGENT_TOKEN,
        "version": APP_VERSION,
        "key_status": ("present (hidden)" if OPENAI_API_KEY else "not set"),
    }
    base.update(extra)
    return base

# =============================================================================
# Models
# =============================================================================
class ChatIn(BaseModel):
    message: str

class LoginIn(BaseModel):
    username: str
    password: str

class SaveKeyIn(BaseModel):
    openai_api_key: str

class ChatRequest(BaseModel):
    message: str
    system: Optional[str] = None
    provider: Optional[str] = None  # "openai", "anthropic", etc.
    model: Optional[str] = None     # optional explicit model name

# =============================================================================
# Health + version
# =============================================================================
@app.get("/health")
def health():
    return {"ok": True}

@app.head("/health")
def _health_head():
    return Response(status_code=200)

@app.get("/version")
def version():
    return {"version": APP_VERSION}

@app.head("/version")
def _version_head():
    return Response(status_code=200)

# =============================================================================
# Auth
# =============================================================================
@app.post("/auth/login")
def do_login(data: LoginIn, request: Request):
    if data.username == ADMIN_USER and data.password == ADMIN_PASS:
        request.session["user"] = ADMIN_USER
        log_line(request, "login ok")
        return {"detail": "ok"}
    log_line(request, "login failed")
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/auth/logout")
def do_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/static/login.html", status_code=status.HTTP_302_FOUND)

@app.get("/auth/logout")
def do_logout_get(request: Request):
    request.session.clear()
    return RedirectResponse(url="/static/login.html", status_code=status.HTTP_302_FOUND)

@app.head("/auth/logout")
def logout_head(request: Request):
    return Response(status_code=200)

# =============================================================================
# UI (protected)
# =============================================================================
@app.get("/ui/", response_class=HTMLResponse)
def ui_index(request: Request, user: str = Depends(require_login)):
    return templates.TemplateResponse("index.html", _ctx(request, user, title="Jensen Agent — Dashboard"))

@app.get("/ui/chat", response_class=HTMLResponse)
def ui_chat(request: Request, user: str = Depends(require_login)):
    return templates.TemplateResponse("chat.html", _ctx(request, user, title="Jensen Agent — Chat"))

@app.get("/ui/admin", response_class=HTMLResponse)
def ui_admin(request: Request, user: str = Depends(require_login)):
    return templates.TemplateResponse("admin.html", _ctx(request, user, title="Admin"))

@app.get("/ui/logs", response_class=HTMLResponse)
def ui_logs(request: Request, user: str = Depends(require_login)):
    text = "\n".join(list(app.state.logs))
    return templates.TemplateResponse("logs.html", _ctx(request, user, title="Raw Logs", logs=text))

@app.post("/ui/logs/reload", response_class=HTMLResponse)
def ui_logs_reload(request: Request, user: str = Depends(require_login)):
    return ui_logs(request, user)

@app.get("/ui/admin/links", response_class=HTMLResponse)
async def ui_admin_links(request: Request, user: str = Depends(require_login)):
    if get_admin_links_page:
        try:
            return get_admin_links_page()
        except Exception:
            pass
    # Robust fallback to template
    return templates.TemplateResponse("admin_links.html", _ctx(request, user, title="Links & Integrations"))

@app.head("/ui/admin/links")
def _admin_links_head():
    return Response(status_code=200)

# =============================================================================
# Admin APIs (protected)
# =============================================================================
@app.post("/admin/config")
def admin_save_config(data: SaveKeyIn, request: Request, user: str = Depends(require_login)):
    # Write (or replace) OPENAI_API_KEY in /app/.env
    env_path = "/app/.env"
    try:
        lines = []
        found = False
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f.readlines():
                    if line.startswith("OPENAI_API_KEY="):
                        lines.append(f"OPENAI_API_KEY={data.openai_api_key}\n")
                        found = True
                    else:
                        lines.append(line)
        if not found:
            lines.append(f"OPENAI_API_KEY={data.openai_api_key}\n")
        with open(env_path, "w") as f:
            f.writelines(lines)
        log_line(request, "saved OPENAI_API_KEY (masked)")
        return {"detail": "Key saved. Restart container to apply."}
    except Exception as e:
        log_line(request, f"save key error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save key")

@app.get("/admin/logs")
def admin_logs(request: Request, user: str = Depends(require_login)):
    return {"logs": list(app.state.logs)}

@app.post("/admin/key")
def _admin_key_alias():
    # unify on the authenticated JSON endpoint
    return RedirectResponse(url="/admin/config", status_code=307)

# =============================================================================
# Chat endpoints
# =============================================================================
@app.post("/chat_v15")
def chat(data: ChatIn, request: Request):
    token = request.headers.get("X-Agent-Token", "")
    if token != AGENT_TOKEN:
        log_line(request, "chat 401 (bad token)")
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Demo responses until model calls are enabled
    if not OPENAI_API_KEY:
        log_line(request, "chat (demo reply, no key)")
        return {"reply": "Hello! How can I assist you today?",
                "route": "general",
                "summary": f"User asked: {data.message}"}

    log_line(request, "chat (demo reply, key present)")
    return {"reply": "Thanks! Your OpenAI key is set. (Model call can be enabled next.)",
            "route": "general",
            "summary": f"User asked: {data.message}"}

# Back-compat shim: /chat forwards to /chat_v15
try:
    import httpx as _httpx
    _HAS_HTTPX = True
except Exception:
    _HAS_HTTPX = False

@app.post("/chat")
async def chat_alias(request: Request, x_agent_token: str = Header(default=None)):
    # If httpx isn't installed, fall back to a 307 redirect that preserves POST.
    if not _HAS_HTTPX:
        return RedirectResponse(url="/chat_v15", status_code=307)

    body = await request.json()
    headers = {"Content-Type": "application/json"}
    if x_agent_token:
        headers["X-Agent-Token"] = x_agent_token

    async with _httpx.AsyncClient() as client:
        r = await client.post(
            "http://127.0.0.1:8000/chat_v15",
            headers=headers,
            json=body,
            timeout=30
        )
    # Pass-through status + JSON so clients see the same shape as /chat_v15
    return JSONResponse(status_code=r.status_code, content=r.json())

# Real model-backed chat endpoints
def _require_token(x_agent_token: Optional[str]):
    expected = os.getenv("AGENT_TOKEN", "jensen4254")
    if not x_agent_token or x_agent_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

def _do_llm_chat(body: ChatRequest) -> dict:
    """
    Helper that calls the shared LLM gateway and returns a standard payload.
    """
    from app.services.llm_gateway import ChatMessage, call_chat_llm

    sys_msg = body.system or "You are Jensen Agent. Answer briefly and helpfully."

    messages = [
        ChatMessage(role="system", content=sys_msg),
        ChatMessage(role="user", content=body.message),
    ]

    result = call_chat_llm(
        messages=messages,
        provider=(body.provider or None),
        model=(body.model or None),
        temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
        max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "256")),
    )

    text = result.reply or "(no content)"
    return {
        "reply": text,
        "route": "live",
        "summary": f"User asked: {body.message[:90]}",
        "provider": result.provider,
        "model": result.model,
    }

@app.post("/chat_live")
async def chat_live(
    body: ChatRequest,
    x_agent_token: Optional[str] = Header(None, alias="X-Agent-Token"),
):
    """
    Real model-backed chat using the LLM Gateway.

    - Uses X-Agent-Token for auth.
    - Uses env defaults when provider/model are not supplied.
    """
    _require_token(x_agent_token)
    try:
        return _do_llm_chat(body)
    except Exception as e:
        return {
            "reply": f"LLM error: {type(e).__name__}: {e}",
            "route": "error",
        }

@app.post("/chat_live2")
async def chat_live2(
    body: ChatRequest,
    request: Request,
):
    """
    Same as /chat_live but fetches X-Agent-Token directly from headers.
    """
    token = request.headers.get("x-agent-token") or request.headers.get("X-Agent-Token")
    _require_token(token)
    try:
        payload = _do_llm_chat(body)
        payload["route"] = "live2"
        return payload
    except Exception as e:
        return {
            "reply": f"LLM error: {type(e).__name__}: {e}",
            "route": "error",
        }

# =============================================================================
# Operator links
# =============================================================================
@app.get("/ops/links")
def ops_links():
    try:
        p = Path(LINKS_PATH)
        if not p.exists():
            return {"links": []}
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        # Never take the service down for ops links
        return {"links": []}

# =============================================================================
# Short links + HEAD helpers
# =============================================================================
@app.get("/admin")
def admin_short(request: Request, user: str = Depends(require_login)):
    return RedirectResponse(url="/ui/admin", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

@app.get("/logs")
def logs_short(request: Request, user: str = Depends(require_login)):
    return RedirectResponse(url="/ui/logs", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

@app.head("/admin")
def admin_head_open():
    return Response(status_code=200)

@app.head("/logs")
def logs_head_open():
    return Response(status_code=200)

# =============================================================================
# Root behavior
# =============================================================================
@app.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse(url="/static/login.html", status_code=status.HTTP_302_FOUND)

@app.head("/", include_in_schema=False)
def root_head():
    return Response(status_code=200)

# =============================================================================
# Diagnostics
# =============================================================================
@app.get("/__routes")
def __routes():
    out = []
    for r in app.router.routes:
        try:
            out.append({"path": getattr(r, "path", str(r)), "methods": sorted(list(getattr(r, "methods", []) or []))})
        except Exception:
            pass
    return {"routes": out}

@app.get("/diag/routes")
def __diag_routes():
    paths = []
    try:
        for r in app.router.routes:
            try:
                methods = sorted(list(getattr(r, "methods", [])))
            except Exception:
                methods = []
            paths.append({"path": getattr(r, "path", None), "methods": methods})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    return {"routes": paths}

# =============================================================================
# Quiet common icon probes (avoid 404 noise)
# =============================================================================
@app.get("/favicon.ico", include_in_schema=False)
def _fav():
    return Response(status_code=204)

@app.get("/apple-touch-icon.png", include_in_schema=False)
def _ati():
    return Response(status_code=204)

@app.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
def _atip():
    return Response(status_code=204)

# =============================================================================
# Middleware
# =============================================================================
@app.middleware("http")
async def access_log_mw(request: Request, call_next):
    try:
        response = await call_next(request)
        log_line(request, f"{response.status_code}")
        return response
    except Exception as e:
        log_line(request, f"500 {e}")
        raise

# =============================================================================
# Global exception handler
# =============================================================================
@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    try:
        t = type(exc).__name__
        app.state.logs.append(f"[exc] {t}: {exc}")
    except Exception:
        pass
    return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)

# =============================================================================
# Background workers & services startup
# =============================================================================
# Audit watcher
try:
    from app.services import audit_watcher as _audit_watcher
    _audit_watcher.start()
except Exception:
    pass

# Job runner
try:
    from app.services.job_runner import runner as _jobrunner
    @app.on_event("startup")
    async def _start_job_runner():
        await _jobrunner.start()
except Exception:
    pass

# Integration worker
if os.getenv('INTEGRATIONS_ENABLED','false').lower()=='true':
    try:
        from app.worker_pg import worker_loop
        @app.on_event('startup')
        async def _start_worker_pg():
            asyncio.create_task(worker_loop())
    except Exception:
        pass

# =============================================================================
# Prometheus metrics (standard ASGI mount + counters)
# =============================================================================
try:
    from prometheus_client import make_asgi_app, Counter

    # Mount Prometheus metrics endpoint
    app.mount("/metrics", make_asgi_app())

    # Define counters
    REQUESTS_OK = Counter("jensen_requests_ok_total", "Successful agent requests")
    REQUESTS_ERR = Counter("jensen_requests_error_total", "Errored agent requests")

    @app.middleware("http")
    async def _count_requests_mw(request, call_next):
        try:
            response = await call_next(request)
            # treat <400 as OK, >=400 as error
            if getattr(response, "status_code", 500) < 400:
                REQUESTS_OK.inc()
            else:
                REQUESTS_ERR.inc()
            return response
        except Exception:
            REQUESTS_ERR.inc()
            raise
except Exception:
    # If prometheus_client isn't available, skip silently
    pass
