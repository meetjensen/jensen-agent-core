from fastapi import APIRouter
import os, re

router = APIRouter()

def _mask(v: str | None):
    if v is None: return None
    return "***" if len(v) <= 8 else v[:4] + "…" + v[-4:]

@router.get("/diag/env")
def diag_env():
    keys = [
        "OPENAI_API_KEY", "AGENT_TOKEN", "APP_VERSION",
        "AWS_REGION", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
        "S3_EXPORT_ENABLED", "S3_BUCKET_NAME", "S3_REGION",
        "SNS_TOPIC_ARN",
    ]
    out = {}
    for k in keys:
        val = os.getenv(k)
        if re.search(r"(KEY|TOKEN|SECRET|PASSWORD)", k):
            out[k] = _mask(val)
        else:
            out[k] = val
    return {"env": out}
