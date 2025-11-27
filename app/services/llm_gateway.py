from __future__ import annotations

import os
from typing import List, Optional, Dict, Any

from openai import OpenAI
from anthropic import Anthropic
from pydantic import BaseModel


# ---------- OpenAI client helpers ----------


def get_openai_client() -> OpenAI:
    """
    Return an OpenAI client using the OPENAI_API_KEY environment variable.

    Raises:
        RuntimeError: if OPENAI_API_KEY is not set or empty.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set; cannot create OpenAI client")

    return OpenAI(api_key=api_key)


# ---------- Anthropic (Claude) client helpers ----------


def get_anthropic_client() -> Anthropic:
    """
    Return an Anthropic client using the ANTHROPIC_API_KEY environment variable.

    Raises:
        RuntimeError: if ANTHROPIC_API_KEY is not set or empty.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set; cannot create Anthropic client")

    return Anthropic(api_key=api_key)


# ---------- Shared data models ----------


class ChatMessage(BaseModel):
    """
    Single chat message for the LLM Gateway.

    role:
        "system", "user", or "assistant".
    content:
        Plain text content for the message.
    """
    role: str
    content: str


class ChatResult(BaseModel):
    """
    Result of a chat completion.

    provider:
        Name of the provider ("openai" or "anthropic").
    model:
        Name of the model that actually ran.
    reply:
        The main reply text from the assistant.
    usage:
        Optional raw usage information from the underlying client.
    """
    provider: str
    model: str
    reply: str
    usage: Optional[Dict[str, Any]] = None


# ---------- Provider-specific call helpers ----------


def _call_openai_chat(
    messages: List[ChatMessage],
    *,
    model: Optional[str],
    temperature: float,
    max_tokens: int,
) -> ChatResult:
    """
    Call OpenAI chat.completions API and return a ChatResult.
    """
    resolved_model = model or os.getenv("OPENAI_MODEL", "gpt-5.1")

    client = get_openai_client()
    payload_messages = [m.model_dump() for m in messages]

    resp = client.chat.completions.create(
        model=resolved_model,
        messages=payload_messages,
        temperature=temperature,
        # New OpenAI client uses max_completion_tokens for output limit
        max_completion_tokens=max_tokens,
    )

    # Extract reply text from the first choice
    reply_text = ""
    choices = getattr(resp, "choices", None)
    if choices:
        first = choices[0]
        message_obj = getattr(first, "message", None)
        if message_obj is not None and getattr(message_obj, "content", None) is not None:
            reply_text = message_obj.content
        elif getattr(first, "content", None) is not None:
            # Fallback if the structure differs
            reply_text = first.content  # type: ignore[assignment]

    # Extract model name: prefer resp.model, fall back to resolved_model
    used_model = getattr(resp, "model", None) or resolved_model

    # Extract usage as a plain dict if available
    usage_dict: Optional[Dict[str, Any]] = None
    usage_obj = getattr(resp, "usage", None)
    if usage_obj is not None:
        try:
            if hasattr(usage_obj, "model_dump"):
                usage_dict = usage_obj.model_dump()  # type: ignore[assignment]
            else:
                usage_dict = dict(vars(usage_obj))
        except Exception:
            usage_dict = None

    return ChatResult(
        provider="openai",
        model=used_model,
        reply=reply_text,
        usage=usage_dict,
    )


def _call_anthropic_chat(
    messages: List[ChatMessage],
    *,
    model: Optional[str],
    temperature: float,
    max_tokens: int,
) -> ChatResult:
    """
    Call Anthropic Claude messages API and return a ChatResult.

    Notes:
    - Uses ANTHROPIC_MODEL env var if model is not provided.
    - Maps the ChatMessage list into Anthropic's 'system' + 'messages' format.
    """
    resolved_model = model or os.getenv("ANTHROPIC_MODEL", "").strip()
    if not resolved_model:
        raise RuntimeError("ANTHROPIC_MODEL is not set; cannot call Anthropic")

    client = get_anthropic_client()

    # Separate out the first system message (if any)
    system_prompt: Optional[str] = None
    chat_messages: List[Dict[str, Any]] = []

    for m in messages:
        if m.role == "system" and system_prompt is None:
            system_prompt = m.content
        else:
            # Map roles directly; Claude expects "user" and "assistant"
            role = m.role
            if role not in ("user", "assistant"):
                # Non-user/non-assistant roles default to 'user'
                role = "user"

            chat_messages.append(
                {
                    "role": role,
                    "content": [
                        {
                            "type": "text",
                            "text": m.content,
                        }
                    ],
                }
            )

    # Build request payload
    create_kwargs: Dict[str, Any] = {
        "model": resolved_model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": chat_messages,
    }
    if system_prompt:
        create_kwargs["system"] = system_prompt

    resp = client.messages.create(**create_kwargs)

    reply_text = ""
    # Anthropic responses typically have content as a list of blocks
    content = getattr(resp, "content", None)
    if content:
        # Find first text block
        for block in content:
            if getattr(block, "type", None) == "text":
                reply_text = getattr(block, "text", "") or ""
                if reply_text:
                    break

    used_model = getattr(resp, "model", None) or resolved_model

    usage_dict: Optional[Dict[str, Any]] = None
    usage_obj = getattr(resp, "usage", None)
    if usage_obj is not None:
        try:
            if hasattr(usage_obj, "model_dump"):
                usage_dict = usage_obj.model_dump()  # type: ignore[assignment]
            else:
                usage_dict = dict(vars(usage_obj))
        except Exception:
            usage_dict = None

    return ChatResult(
        provider="anthropic",
        model=used_model,
        reply=reply_text,
        usage=usage_dict,
    )


# ---------- Public gateway function ----------


def call_chat_llm(
    messages: List[ChatMessage],
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 512,
) -> ChatResult:
    """
    Unified LLM Gateway v2 for chat completions.

    - Supports multiple providers under one API:
        - "openai" (default)
        - "anthropic" (Claude)
    - Provider selection:
        - If `provider` argument is provided, use it.
        - Otherwise, read from the LLM_PROVIDER env var (default "openai").
    - Model selection is provider-specific:
        - OpenAI: model arg -> OPENAI_MODEL -> "gpt-5.1"
        - Anthropic: model arg -> ANTHROPIC_MODEL (must be set)
    """
    # Resolve provider from argument -> env -> default
    resolved_provider = (provider or os.getenv("LLM_PROVIDER", "openai")).strip().lower()

    if resolved_provider == "openai":
        return _call_openai_chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    elif resolved_provider == "anthropic":
        return _call_anthropic_chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    else:
        raise RuntimeError(f"Unsupported provider: {resolved_provider!r}")
