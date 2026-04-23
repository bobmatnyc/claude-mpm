#!/usr/bin/env python3
"""
Emergency fix for dashboard stability issues.
This script implements a simple HTTP-based event relay to fix disconnection issues.
"""

import asyncio
import logging
import sys
from pathlib import Path

import socketio
from aiohttp import web

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StableSocketIOServer:
    """A simplified, stable Socket.IO server without the complexity."""

    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.sio = socketio.AsyncServer(
            cors_allowed_origins="*",
            ping_interval=25,
            ping_timeout=60,
            logger=False,
            engineio_logger=False,
        )
        self.app = web.Application()
        self.sio.attach(self.app)
        self.setup_routes()
        self.setup_handlers()

    def setup_routes(self):
        """Setup HTTP routes for receiving events."""

        async def receive_event(request):
            """HTTP endpoint for hook handlers to send events."""
            try:
                event = await request.json()
                # Broadcast to all connected dashboards
                await self.sio.emit(
                    "claude_event",
                    {
                        "type": event.get("type", "hook"),
                        "subtype": event.get("subtype", "unknown"),
                        "data": event.get("data", {}),
                        "timestamp": event.get("timestamp"),
                    },
                )
                return web.Response(text="OK")
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                return web.Response(text="ERROR", status=500)

        async def health_check(request):
            """Health check endpoint."""
            return web.json_response(
                {"status": "healthy", "server_id": "stable-socketio", "port": self.port}
            )

        # Dashboard HTML
        async def dashboard(request):
            """Serve the dashboard."""
            dashboard_path = (
                Path(__file__).parent.parent
                / "src/claude_mpm/dashboard/templates/index.html"
            )
            if dashboard_path.exists():
                return web.FileResponse(dashboard_path)
            return web.Response(text="Dashboard not found", status=404)

        # Add routes
        self.app.router.add_post("/api/events", receive_event)
        self.app.router.add_get("/health", health_check)
        self.app.router.add_get("/", dashboard)
        self.app.router.add_get("/dashboard", dashboard)

        # Serve static files
        static_path = Path(__file__).parent.parent / "src/claude_mpm/dashboard/static"
        if static_path.exists():
            self.app.router.add_static("/static/", static_path)

    def setup_handlers(self):
        """Setup Socket.IO event handlers."""

        @self.sio.event
        async def connect(sid, environ):
            logger.info(f"Dashboard connected: {sid}")
            # Send connection acknowledgment
            await self.sio.emit(
                "connection_ack", {"status": "connected", "sid": sid}, to=sid
            )

        @self.sio.event
        async def disconnect(sid):
            logger.info(f"Dashboard disconnected: {sid}")

        @self.sio.event
        async def ping(sid):
            await self.sio.emit("pong", to=sid)

    async def start_heartbeat(self):
        """Send periodic heartbeats to keep connections alive."""
        while True:
            await asyncio.sleep(60)
            try:
                await self.sio.emit(
                    "system_event",
                    {
                        "type": "system",
                        "subtype": "heartbeat",
                        "data": {"status": "alive"},
                    },
                )
                logger.info("Heartbeat sent")
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def run(self):
        """Run the server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port, reuse_address=True)
        await site.start()

        logger.info(
            f"Stable Socket.IO server running on http://{self.host}:{self.port}"
        )
        logger.info(f"Dashboard: http://{self.host}:{self.port}/dashboard")
        logger.info(f"Event API: POST http://{self.host}:{self.port}/api/events")

        # Start heartbeat task
        asyncio.create_task(self.start_heartbeat())

        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")


def patch_hook_handler():
    """Create a patched version of hook handler that uses HTTP."""

    hook_patch = '''
# Add this to ConnectionManagerService.emit_event() in connection_manager.py:

def emit_event(self, namespace: str, event: str, data: dict):
    """Emit event via simple HTTP POST."""
    import requests
    try:
        requests.post(
            "http://localhost:8765/api/events",
            json={
                "type": "hook",
                "subtype": event,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            timeout=0.5
        )
        if DEBUG:
            print(f"✅ Emitted via HTTP: {event}", file=sys.stderr)
    except Exception as e:
        if DEBUG:
            print(f"⚠️ Failed to emit via HTTP: {e}", file=sys.stderr)
    '''

    print("\n" + "=" * 60)
    print("PATCH FOR HOOK HANDLER")
    print("=" * 60)
    print(hook_patch)
    print("=" * 60)


async def main():
    """Main entry point."""

    if len(sys.argv) > 1 and sys.argv[1] == "patch":
        patch_hook_handler()
        return

    print("\n" + "=" * 60)
    print("STABLE SOCKET.IO SERVER")
    print("=" * 60)
    print("This is a simplified server without the complexity issues.")
    print("It uses HTTP for receiving events, avoiding process boundary issues.")
    print()

    server = StableSocketIOServer()
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped.")
