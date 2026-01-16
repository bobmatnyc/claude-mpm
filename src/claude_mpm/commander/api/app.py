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

from ..events.manager import EventManager
from ..inbox import Inbox
from ..registry import ProjectRegistry
from ..tmux_orchestrator import TmuxOrchestrator
from ..workflow import EventHandler
from .routes import events, inbox as inbox_routes, messages, projects, sessions, work

# Global instances (injected at startup via lifespan)
registry: Optional[ProjectRegistry] = None
tmux: Optional[TmuxOrchestrator] = None
event_manager: Optional[EventManager] = None
inbox: Optional[Inbox] = None
event_handler: Optional[EventHandler] = None
session_manager: dict = {}  # project_id -> ProjectSession


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
    global registry, tmux, event_manager, inbox, event_handler, session_manager
    registry = ProjectRegistry()
    tmux = TmuxOrchestrator()
    event_manager = EventManager()
    inbox = Inbox(event_manager, registry)
    session_manager = {}  # Populated by daemon when sessions are created
    event_handler = EventHandler(inbox, session_manager)

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
app.include_router(inbox_routes.router, prefix="/api", tags=["inbox"])
app.include_router(events.router, prefix="/api", tags=["events"])
app.include_router(work.router, prefix="/api", tags=["work"])

# Mount static files
static_path = Path(__file__).parent.parent / "web" / "static"
static_v2_path = static_path / "v2"
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


@app.get("/v2")
async def root_v2() -> FileResponse:
    """Serve the new Pro web UI index page.

    Returns:
        HTML page for the Pro web UI
    """
    return FileResponse(static_v2_path / "index.html")


@app.get("/v2/{path:path}")
async def serve_v2_static(path: str) -> FileResponse:
    """Serve static files for v2 UI.

    Args:
        path: Relative path to the static file

    Returns:
        The requested static file
    """
    file_path = static_v2_path / path
    if file_path.exists():
        return FileResponse(file_path)
    return FileResponse(static_v2_path / "index.html")
