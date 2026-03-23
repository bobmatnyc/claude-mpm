"""Local HTTP endpoint for injecting messages into PM agent sessions.

Allows external systems (webhooks, CI, scripts, cURL) to send prompts
to the running PM agent via the SDK runtime.

Usage:
    # Start the endpoint:
    python -m claude_mpm.services.agents.message_endpoint

    # Or from another process:
    curl -X POST http://localhost:7856/inject \\
        -H "Content-Type: application/json" \\
        -d '{"prompt": "Check the status of PR #123"}'

    # With session resume:
    curl -X POST http://localhost:7856/inject \\
        -H "Content-Type: application/json" \\
        -d '{"prompt": "Continue with the fix", "session_id": "abc123"}'
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Default port - configurable via CLAUDE_MPM_INJECT_PORT
DEFAULT_PORT = 7856


# ---------------------------------------------------------------------------
# Pydantic request / response models  (module-level so FastAPI can resolve
# them even when ``from __future__ import annotations`` is active)
# ---------------------------------------------------------------------------


class InjectRequest(BaseModel):
    """JSON body accepted by ``POST /inject``."""

    prompt: str
    system_prompt: str | None = None
    model: str | None = None
    session_id: str | None = None
    allowed_tools: list[str] | None = None
    cwd: str | None = None
    max_turns: int | None = None


class InjectResponse(BaseModel):
    """JSON body returned by ``POST /inject``."""

    text: str
    session_id: str | None = None
    cost_usd: float | None = None
    num_turns: int | None = None
    duration_ms: int | None = None
    is_error: bool = False
    runtime: str = "unknown"


# ---------------------------------------------------------------------------
# Plain dataclasses (convenience wrappers, not used by FastAPI directly)
# ---------------------------------------------------------------------------


@dataclass
class InjectedMessage:
    """A message injected via the HTTP endpoint."""

    prompt: str
    system_prompt: str | None = None
    model: str | None = None
    session_id: str | None = None
    allowed_tools: list[str] | None = None
    cwd: str | None = None
    mcp_servers: dict[str, Any] | None = None
    max_turns: int | None = None


@dataclass
class InjectionResult:
    """Result from processing an injected message."""

    text: str
    session_id: str | None = None
    cost_usd: float | None = None
    num_turns: int | None = None
    duration_ms: int | None = None
    is_error: bool = False
    runtime: str = "unknown"


# ---------------------------------------------------------------------------
# Endpoint server
# ---------------------------------------------------------------------------


class MessageEndpoint:
    """HTTP server for accepting injected messages.

    Runs a lightweight FastAPI server on a local port.
    Accepts POST /inject with JSON body.
    Also provides GET /status for health checks.
    """

    def __init__(self, port: int | None = None) -> None:
        self.port = port or int(
            os.environ.get("CLAUDE_MPM_INJECT_PORT", str(DEFAULT_PORT))
        )
        self._app: Any | None = None
        self._history: list[dict[str, Any]] = []

    def create_app(self) -> Any:
        """Create the FastAPI app with routes."""
        try:
            from fastapi import FastAPI
            from fastapi.responses import JSONResponse
        except ImportError as exc:
            raise RuntimeError(
                "FastAPI is required. Install with: pip install fastapi uvicorn"
            ) from exc

        app = FastAPI(
            title="Claude MPM Message Injection",
            description="Inject prompts into the PM agent session",
            version="0.1.0",
        )

        @app.get("/status")
        async def status() -> dict[str, Any]:
            from claude_mpm.services.agents.runtime_config import get_runtime_type

            try:
                runtime_type = get_runtime_type()
            except Exception:
                runtime_type = "unknown"
            return {
                "status": "running",
                "runtime": runtime_type,
                "port": self.port,
                "history_count": len(self._history),
            }

        @app.post("/inject", response_model=InjectResponse)
        async def inject(body: InjectRequest) -> Any:
            from claude_mpm.services.agents.runtime_bridge import execute_agent_prompt

            logger.info("Received inject request: %s", body.prompt[:100])

            try:
                result = await execute_agent_prompt(
                    prompt=body.prompt,
                    system_prompt=body.system_prompt,
                    model=body.model,
                    session_id=body.session_id,
                    allowed_tools=body.allowed_tools,
                    cwd=body.cwd,
                )

                self._history.append(
                    {
                        "prompt": body.prompt[:200],
                        "result_preview": result.get("text", "")[:200],
                        "is_error": result.get("is_error", False),
                        "runtime": result.get("runtime", "unknown"),
                    }
                )

                return InjectResponse(
                    text=result.get("text", ""),
                    session_id=result.get("session_id"),
                    cost_usd=result.get("cost_usd"),
                    num_turns=result.get("num_turns"),
                    duration_ms=result.get("duration_ms"),
                    is_error=result.get("is_error", False),
                    runtime=result.get("runtime", "unknown"),
                )
            except Exception as e:
                logger.exception("Injection failed")
                return JSONResponse(
                    status_code=500,
                    content={"error": str(e), "is_error": True},
                )

        @app.get("/session")
        async def session() -> dict[str, Any]:
            from claude_mpm.services.agents.session_state_tracker import (
                get_global_tracker,
            )

            tracker = get_global_tracker()
            if tracker is None:
                return {"error": "No active SDK session", "state": "unavailable"}
            return tracker.get_session_state()

        @app.get("/activity")
        async def activity(limit: int = 50) -> dict[str, Any]:
            from claude_mpm.services.agents.session_state_tracker import (
                get_global_tracker,
            )

            tracker = get_global_tracker()
            if tracker is None:
                return {"events": [], "error": "No active SDK session"}
            return {"events": tracker.get_activity(limit=limit)}

        @app.get("/history")
        async def history() -> dict[str, Any]:
            return {"history": self._history[-50:]}  # Last 50

        self._app = app
        return app

    def run(self) -> None:
        """Start the server with clean shutdown support."""
        import uvicorn

        app = self.create_app()
        logger.info("Starting message injection endpoint on port %d", self.port)

        config = uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="info")
        self._server = uvicorn.Server(config)

        self._server.run()

    def shutdown(self) -> None:
        """Signal the server to shut down gracefully."""
        if hasattr(self, "_server") and self._server:
            self._server.should_exit = True


if __name__ == "__main__":
    import sys

    port = DEFAULT_PORT
    for arg in sys.argv[1:]:
        if arg.startswith("--port="):
            port = int(arg.split("=")[1])

    endpoint = MessageEndpoint(port=port)
    print(f"Starting message injection endpoint on http://127.0.0.1:{port}")
    print("  POST /inject  - Send a prompt")
    print("  GET  /status  - Health check")
    print("  GET  /history - View recent injections")
    endpoint.run()
