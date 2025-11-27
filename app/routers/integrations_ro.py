from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.services.registry import load_actions

router = APIRouter()

@router.get("/integrations/actions")
def list_actions():
    return JSONResponse(content=load_actions())
