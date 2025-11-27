import os
import uuid
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from pydantic import BaseModel
from openai import OpenAI
from dotenv import dotenv_values

router = APIRouter(prefix="/audio", tags=["audio"])

# Config flags (read once)
ENABLE_WHISPER = os.getenv("ENABLE_WHISPER", "true").lower() == "true"
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "jensen4254")
MAX_AUDIO_UPLOAD_MB = int(os.getenv("MAX_AUDIO_UPLOAD_MB", "25"))

ALLOWED_EXTS = {".wav", ".mp3", ".m4a", ".ogg"}

class TranscriptionOut(BaseModel):
    text: str
    duration: Optional[float] = None  # not computed server-side

def _get_client() -> OpenAI:
    """Load key directly from /app/.env to avoid corrupted process env."""
    cfg = dotenv_values('/app/.env')
    key = (cfg.get('OPENAI_API_KEY') or '').strip()
    if not key:
        raise HTTPException(status_code=500, detail="OpenAI key missing")
    return OpenAI(api_key=key)

@router.post("/upload", response_model=TranscriptionOut)
async def upload_audio(request: Request, file: UploadFile = File(...)):
    # Auth
    token = request.headers.get("X-Agent-Token", "")
    if token != AGENT_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not ENABLE_WHISPER:
        raise HTTPException(status_code=400, detail="Whisper disabled by config")

    # Validate extension
    name = (file.filename or "").lower()
    if not any(name.endswith(ext) for ext in ALLOWED_EXTS):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # Read & size check
    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > MAX_AUDIO_UPLOAD_MB:
        raise HTTPException(status_code=413, detail=f"File too large (> {MAX_AUDIO_UPLOAD_MB} MB)")
    await file.seek(0)

    # Temp file
    suffix = os.path.splitext(name)[1] or ".wav"
    tmp = f"/tmp/{uuid.uuid4().hex}{suffix}"
    try:
        with open(tmp, "wb") as f:
            f.write(contents)

        client = _get_client()
        with open(tmp, "rb") as f:
            tr = client.audio.transcriptions.create(model=WHISPER_MODEL, file=f)

        text = getattr(tr, "text", None) or (tr.get("text") if isinstance(tr, dict) else None) or ""
        if not text:
            raise HTTPException(status_code=500, detail="No transcription text returned")
        return TranscriptionOut(text=text, duration=None)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {e}")
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
