from fastapi import APIRouter
from datetime import datetime


router = APIRouter()


@router.get("/healthz")
async def healthz():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"}


@router.get("/discovery/")
async def discovery():
    return {
        "service": {"name": "api-gateway", "version": "0.1.0", "description": "Gateway/BFF"},
        "endpoints": {"health": "/healthz", "docs": "/docs", "openapi": "/openapi.json"},
        "capabilities": {"auth": True, "rate_limit": False, "async": True},
    }
from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def status():
    return {"status": "ok"}
