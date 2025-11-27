from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter(
    tags=["ui-orchestrator"],
)


def _tpl_root() -> str:
    """
    Resolve templates directory in a way that matches main.py behavior.

    We check:
      - /app/app/templates
      - /app/templates
      - <this_file>/../templates
    and return the first that exists.
    """
    candidates = [
        Path("/app/app/templates"),
        Path("/app/templates"),
        Path(__file__).resolve().parent.parent / "templates",
    ]
    for cand in candidates:
        if cand.exists():
            return str(cand)
    return str(candidates[0])


templates = Jinja2Templates(directory=_tpl_root())


@router.get("/ui/orchestrator", response_class=HTMLResponse)
async def ui_orchestrator(request: Request) -> Any:
    """
    Minimal operator-facing Orchestrator UI.

    This page itself does not hit the DB; instead, it uses frontend JS to talk
    to the existing JSON endpoints:

      - POST /internal/core/orchestrator/run
      - POST /internal/core/orchestrator/task/update
      - GET  /internal/core/orchestrator/run/{run_id}/debug
      - GET  /internal/core/runs/debug

    All the logic for creating runs and inspecting state stays in those internal
    endpoints. This route only serves HTML + JS.
    """
    return templates.TemplateResponse(
        "orchestrator.html",
        {
            "request": request,
            "app_version": os.getenv("APP_VERSION", "dev"),
        },
    )
