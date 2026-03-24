"""FastAPI application factory for the UI Service.

Creates the FastAPI app, registers all routers, configures CORS and
WebSocket endpoints, and manages the ProcessManager lifecycle via the
lifespan context manager.
"""

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from claude_mpm.services.ui_service.config import UIServiceConfig
from claude_mpm.services.ui_service.process_manager import ProcessManager
from claude_mpm.services.ui_service.routers import (
    auth,
    commands,
    config,
    diagnostics,
    hooks,
    mcp,
    memory,
    messages,
    models,
    permissions,
    sessions,
    tools,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage ProcessManager lifecycle for the FastAPI app.

    Starts the ProcessManager on startup and gracefully stops it
    (terminating all subprocesses) on shutdown.
    """
    pm: ProcessManager = app.state.process_manager
    await pm.start()
    logger.info("UI Service started on port %s", app.state.config.port)
    try:
        yield
    finally:
        await pm.stop()
        logger.info("UI Service stopped")


def create_app(service_config: UIServiceConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        service_config: Optional pre-built config; if None, loads from env.

    Returns:
        Fully configured FastAPI application instance.
    """
    cfg = service_config or UIServiceConfig.from_env()

    app = FastAPI(
        title="claude-mpm UI Service",
        description=(
            "REST + SSE + WebSocket API exposing Claude Code REPL features "
            "for web UI consumption."
        ),
        version="1.0.0",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    # Store shared state
    app.state.config = cfg
    app.state.process_manager = ProcessManager(
        max_sessions=cfg.max_sessions,
        session_timeout_minutes=cfg.session_timeout_minutes,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register all routers under /api/v1
    api_prefix = "/api/v1"
    app.include_router(sessions.router, prefix=api_prefix)
    app.include_router(messages.router, prefix=api_prefix)
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(models.router, prefix=api_prefix)
    app.include_router(config.router, prefix=api_prefix)
    app.include_router(permissions.router, prefix=api_prefix)
    app.include_router(hooks.router, prefix=api_prefix)
    app.include_router(mcp.router, prefix=api_prefix)
    app.include_router(commands.router, prefix=api_prefix)
    app.include_router(memory.router, prefix=api_prefix)
    app.include_router(tools.router, prefix=api_prefix)
    app.include_router(diagnostics.router, prefix=api_prefix)

    # WebSocket endpoint
    @app.websocket("/api/v1/ws/sessions/{session_id}")
    async def websocket_session(websocket: WebSocket, session_id: str):
        """Bidirectional WebSocket for a session.

        Client sends JSON objects:
        - ``{"type": "message", "content": "..."}``
        - ``{"type": "interrupt"}``
        - ``{"type": "command", "name": "/compact"}``

        Server sends StreamEvent objects serialised as JSON.
        """
        pm: ProcessManager = websocket.app.state.process_manager

        try:
            pm.get_session(session_id)
        except KeyError:
            await websocket.close(code=4004, reason=f"Session {session_id} not found")
            return

        await websocket.accept()
        logger.debug("WebSocket connected for session %s", session_id)

        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_text(
                        json.dumps({"type": "error", "message": "Invalid JSON"})
                    )
                    continue

                msg_type = msg.get("type")

                if msg_type == "message":
                    content = msg.get("content", "")
                    async for event in pm.send_message(session_id, content):
                        await websocket.send_text(event.model_dump_json())
                    await websocket.send_text('{"type": "message_stop"}')

                elif msg_type == "interrupt":
                    await pm.interrupt(session_id)
                    await websocket.send_text('{"type": "interrupt_ack"}')

                elif msg_type == "command":
                    cmd_name = msg.get("name", "")
                    if cmd_name:
                        await pm.send_command(session_id, cmd_name)
                        await websocket.send_text(
                            json.dumps({"type": "command_sent", "command": cmd_name})
                        )

                else:
                    await websocket.send_text(
                        json.dumps(
                            {"type": "error", "message": f"Unknown type: {msg_type}"}
                        )
                    )

        except WebSocketDisconnect:
            logger.debug("WebSocket disconnected for session %s", session_id)

    # Health / info root endpoint
    @app.get("/api/v1/health", tags=["Health"])
    async def health():
        """Return service health status."""
        pm: ProcessManager = app.state.process_manager
        return {
            "status": "healthy",
            "active_sessions": len(pm.list_sessions()),
        }

    return app
