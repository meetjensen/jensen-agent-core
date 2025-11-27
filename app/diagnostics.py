from fastapi import APIRouter
import os, re

router = APIRouter()

# Mask secrets but show that they exist
def mask(val: str) -> str:
    if val is None:
        return None
    if len(val) <= 8:
        return "***"
    return val[:4] + "…" + val[-4:]

@router.get("/diag/env")
def diag_env():
    keys = [
        "OPENAI_API_KEY", "AGENT_TOKEN", "APP_VERSION",
        "AWS_REGION", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
        "S3_EXPORT_ENABLED", "S3_BUCKET_NAME", "S3_REGION",
        "SNS_TOPIC_ARN",
    ]
    data = {}
    for k in keys:
        v = os.getenv(k)
        # mask anything that looks sensitive
        if re.search(r"(KEY|TOKEN|SECRET|PASSWORD)", k):
            data[k] = mask(v)
        else:
            data[k] = v
    return {"env": data}
