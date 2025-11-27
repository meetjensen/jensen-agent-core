from fastapi import APIRouter, Request
from pydantic import BaseModel
import os

from app.services.llm_gateway import ChatMessage, call_chat_llm

router = APIRouter()


class ChatIn(BaseModel):
    message: str | None = None
    text: str | None = None
    q: str | None = None


def first(*xs):
    for x in xs:
        if x:
            return x
    return ""


@router.post("/chat")
async def chat_api(body: ChatIn, request: Request):
    # accept several field names so the UI keeps working
    user_msg = first(body.message, body.text, body.q).strip()

    if not user_msg:
        return {
            "reply": "Tell me something to respond to.",
            "route": "general",
            "summary": "Empty message",
        }

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # key not loaded (container not restarted yet)
        return {
            "reply": "OpenAI key not loaded yet—restart the container and try again.",
            "route": "general",
            "summary": f"User asked: {user_msg}",
        }

    # Build messages for the LLM Gateway
    msgs = [
        ChatMessage(
            role="system",
            content="You are Jensen Agent. Be concise and helpful.",
        ),
        ChatMessage(
            role="user",
            content=user_msg,
        ),
    ]

    try:
        # Let the gateway resolve the model (OPENAI_MODEL -> default "gpt-5.1")
        result = call_chat_llm(
            messages=msgs,
            temperature=0.4,
        )
        text = result.reply
        return {
            "reply": text,
            "route": "model",
            "summary": f"User asked: {user_msg}",
        }

    except Exception as e:
        # Preserve a clear error path if the OpenAI call fails
        return {
            "reply": f"OpenAI error: {type(e).__name__}: {e}",
            "route": "error",
            "summary": f"User asked: {user_msg}",
        }
