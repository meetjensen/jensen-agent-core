import os
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import dotenv_values

router = APIRouter(prefix="/router", tags=["router"])

# Config
LLM_ROUTER_ENABLED = os.getenv("LLM_ROUTER_ENABLED", "true").lower() == "true"
LLM_ROUTER_STRATEGY = os.getenv("LLM_ROUTER_STRATEGY", "auto")
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "jensen4254")

DEFAULT_MODEL_GENERAL = "gpt-4o-mini"
DEFAULT_MODEL_SYSTEM = "gpt-4o"
VOICE_MODEL = "gpt-4o-mini"

class RouteIn(BaseModel):
    query: str = Field(..., description="User query or text to process")
    context: Optional[Literal["voice", "system", "general"]] = None

class RouteOut(BaseModel):
    model_used: str
    reply: str

def _get_client() -> OpenAI:
    cfg = dotenv_values('/app/.env')
    key = (cfg.get('OPENAI_API_KEY') or '').strip()
    if not key:
        raise HTTPException(status_code=500, detail="OpenAI key missing")
    return OpenAI(api_key=key)

def choose_model(query: str, context: Optional[str]) -> str:
    if context == "voice":
        return VOICE_MODEL
    if context == "system" or ("system" in query.lower()):
        return DEFAULT_MODEL_SYSTEM
    if len(query.split()) <= 25:
        return DEFAULT_MODEL_GENERAL
    return "gpt-4o"

@router.post("", response_model=RouteOut)
def route_query(data: RouteIn, request: Request):
    # Auth
    token = request.headers.get("X-Agent-Token", "")
    if token != AGENT_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not LLM_ROUTER_ENABLED:
        return RouteOut(model_used=DEFAULT_MODEL_GENERAL, reply="Routing disabled")

    model = choose_model(data.query, data.context)
    try:
        client = _get_client()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are Jensen Agent."},
                {"role": "user", "content": data.query},
            ],
        )
        reply = resp.choices[0].message.content or ""
        return RouteOut(model_used=model, reply=reply)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Router error: {e}")
