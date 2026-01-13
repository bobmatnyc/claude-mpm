"""FastAPI application for MPM Commander REST API.

This module defines the main FastAPI application instance with CORS,
lifecycle management, and route registration.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..registry import ProjectRegistry
from ..tmux_orchestrator import TmuxOrchestrator
from .routes import messages, projects, sessions

# Global instances (injected at startup via lifespan)
registry: Optional[ProjectRegistry] = None
tmux: Optional[TmuxOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle.

    Initializes shared resources on startup and cleans up on shutdown.

    Args:
        app: FastAPI application instance

    Yields:
        None during application runtime
    """
    # Startup
    global registry, tmux
    registry = ProjectRegistry()
    tmux = TmuxOrchestrator()

    yield

    # Shutdown
    # No cleanup needed for Phase 1


app = FastAPI(
    title="MPM Commander API",
    description="REST API for MPM Commander - Autonomous AI Orchestration",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(messages.router, prefix="/api", tags=["messages"])

# Mount static files
static_path = Path(__file__).parent.parent / "web" / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Status and version information
    """
    return {"status": "ok", "version": "1.0.0"}


@app.get("/")
async def root() -> FileResponse:
    """Serve the web UI index page.

    Returns:
        HTML page for the web UI
    """
    return FileResponse(static_path / "index.html")
