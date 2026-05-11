from __future__ import annotations
from fastapi import APIRouter, Depends
from app.api.deps import require_auth
from app.services.tunnel import tunnel_service

router = APIRouter(prefix="/api/tunnel", tags=["tunnel"])


@router.get("/status", dependencies=[Depends(require_auth)])
async def tunnel_status():
    return tunnel_service.status()


@router.post("/restart", dependencies=[Depends(require_auth)])
async def tunnel_restart():
    tunnel_service.restart()
    return {"ok": True}


@router.get("/logs", dependencies=[Depends(require_auth)])
async def tunnel_logs():
    return {"logs": tunnel_service.get_logs()}
