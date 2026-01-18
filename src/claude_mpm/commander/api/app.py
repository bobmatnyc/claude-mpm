"""FastAPI application for MPM Commander REST API.

This module defines the main FastAPI application instance with CORS,
lifecycle management, and route registration.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

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
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Lifespan starting. Initializing app.state resources...")

    # Initialize app.state resources (daemon will inject its instances later)
    if not hasattr(app.state, "registry"):
        app.state.registry = ProjectRegistry()
    if not hasattr(app.state, "tmux"):
        app.state.tmux = TmuxOrchestrator()
    if not hasattr(app.state, "event_manager"):
        app.state.event_manager = EventManager()
    if not hasattr(app.state, "inbox"):
        app.state.inbox = Inbox(app.state.event_manager, app.state.registry)
    if not hasattr(app.state, "session_manager"):
        app.state.session_manager = {}
    if not hasattr(app.state, "work_queues"):
        logger.info("work_queues not set, creating new dict")
        app.state.work_queues = {}
    else:
        logger.info(
            f"work_queues already set, preserving id: {id(app.state.work_queues)}"
        )
    if not hasattr(app.state, "daemon_instance"):
        app.state.daemon_instance = None
    if not hasattr(app.state, "event_handler"):
        app.state.event_handler = EventHandler(
            app.state.inbox, app.state.session_manager
        )

    logger.info(f"Lifespan complete. work_queues id: {id(app.state.work_queues)}")

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
