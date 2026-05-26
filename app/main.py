from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
import os
import traceback

logger = logging.getLogger("screensaver")
logger.setLevel(logging.INFO)


from app.services.tunnel import tunnel_service
from app.api import auth, capture, sessions, questions, tunnel as tunnel_router, system


@asynccontextmanager
async def lifespan(app: FastAPI):
    tunnel_service.start_manager()
    yield
    tunnel_service.stop_manager()


app = FastAPI(
    title="Screensaver",
    description="Private DSA screen-capture and solver service",
    version="3.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

# API Routers
app.include_router(auth.router)
app.include_router(capture.router)
app.include_router(sessions.router)
app.include_router(questions.router)
app.include_router(tunnel_router.router)
app.include_router(system.router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = f"Unhandled exception on {request.method} {request.url.path}: {exc}"
    logger.error(error_msg)
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error: " + str(exc)}
    )

# Static files
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "frontend", "static")
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))
