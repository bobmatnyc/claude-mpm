"""
Stable Dashboard Server for claude-mpm.

WHY: This module provides a simple, stable HTTP + SocketIO server that works
across all installation methods (direct, pip, pipx, homebrew, npm).

DESIGN DECISIONS:
- Uses proven python-socketio + aiohttp combination
- Automatically finds dashboard files across installation methods
- Provides both HTTP endpoints and SocketIO real-time features
- Simple mock AST analysis to avoid complex backend dependencies
- Graceful fallbacks for missing dependencies
"""

import asyncio
import glob
import json
import logging
import os
import sys
import time
import traceback
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Deque, Dict, Optional

try:
    import aiohttp
    import socketio
    from aiohttp import web

    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    socketio = None
    aiohttp = None
    web = None

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def find_dashboard_files() -> Optional[Path]:
    """Find dashboard files across different installation methods."""
    # Try different possible locations
    possible_locations = [
        # Development/direct install
        Path(__file__).parent.parent.parent / "dashboard",
        # Current working directory (for development)
        Path.cwd() / "src" / "claude_mpm" / "dashboard",
        # Pip install in current Python environment
        Path(sys.prefix)
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
        / "claude_mpm"
        / "dashboard",
        # User site-packages
        Path.home()
        / ".local"
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
        / "claude_mpm"
        / "dashboard",
    ]

    # Add glob patterns for different Python versions
    python_patterns = [
        f"/opt/homebrew/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages/claude_mpm/dashboard",
        f"/usr/local/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages/claude_mpm/dashboard",
    ]

    # Check direct paths first
    for location in possible_locations:
        if location.exists() and (location / "templates" / "index.html").exists():
            return location

    # Check pattern-based paths
    for pattern in python_patterns:
        matches = glob.glob(pattern)
        for match in matches:
            path = Path(match)
            if path.exists() and (path / "templates" / "index.html").exists():
                return path

    # Fallback: try to find via module import
    try:
        import claude_mpm.dashboard

        module_path = Path(claude_mpm.dashboard.__file__).parent
        if (module_path / "templates" / "index.html").exists():
            return module_path
    except ImportError:
        pass

    return None


def create_mock_ast_data(file_path: str, file_name: str) -> Dict[str, Any]:
    """Create mock AST analysis data."""
    ext = file_name.split(".")[-1].lower() if "." in file_name else ""

    elements = []
    if ext == "py":
        elements = [
            {
                "name": "MockClass",
                "type": "class",
                "line": 10,
                "complexity": 2,
                "docstring": "Mock class for demonstration",
                "methods": [
                    {"name": "__init__", "type": "method", "line": 11, "complexity": 1},
                    {
                        "name": "mock_method",
                        "type": "method",
                        "line": 15,
                        "complexity": 1,
                    },
                ],
            },
            {
                "name": "mock_function",
                "type": "function",
                "line": 20,
                "complexity": 1,
                "docstring": "Mock function for demonstration",
            },
        ]
    elif ext in ["js", "ts", "jsx", "tsx"]:
        elements = [
            {
                "name": "MockClass",
                "type": "class",
                "line": 5,
                "complexity": 2,
                "methods": [
                    {
                        "name": "constructor",
                        "type": "method",
                        "line": 6,
                        "complexity": 1,
                    },
                    {
                        "name": "mockMethod",
                        "type": "method",
                        "line": 10,
                        "complexity": 1,
                    },
                ],
            },
            {"name": "mockFunction", "type": "function", "line": 15, "complexity": 1},
        ]

    return {
        "path": file_path,
        "elements": elements,
        "complexity": sum(e.get("complexity", 1) for e in elements),
        "lines": 50,
        "stats": {
            "classes": len([e for e in elements if e["type"] == "class"]),
            "functions": len([e for e in elements if e["type"] == "function"]),
            "methods": sum(len(e.get("methods", [])) for e in elements),
            "lines": 50,
        },
    }


class StableDashboardServer:
    """Stable dashboard server that works across all installation methods."""

    def __init__(self, host: str = "localhost", port: int = 8765, debug: bool = False):
        self.host = host
        self.port = port
        self.debug = debug
        self.dashboard_path = None
        self.app = None
        self.sio = None
        self.server_runner = None
        self.server_site = None

        # Event storage with circular buffer (keep last 500 events)
        self.event_history: Deque[Dict[str, Any]] = deque(maxlen=500)
        self.event_count = 0
        self.server_start_time = time.time()
        self.last_event_time = None
        self.connected_clients = set()

        # Resilience features
        self.retry_count = 0
        self.max_retries = 3
        self.health_check_failures = 0
        self.is_healthy = True

        # Persistent event storage (optional)
        self.persist_events = (
            os.environ.get("CLAUDE_MPM_PERSIST_EVENTS", "false").lower() == "true"
        )
        self.event_log_path = Path.home() / ".claude" / "dashboard_events.jsonl"
        if self.persist_events:
            self.event_log_path.parent.mkdir(parents=True, exist_ok=True)

    def setup(self) -> bool:
        """Set up the server components."""
        if not DEPENDENCIES_AVAILABLE:
            print(
                "❌ Error: Missing dependencies. Install with: pip install aiohttp python-socketio"
            )
            return False

        # Find dashboard files only if not already set (for testing)
        if not self.dashboard_path:
            self.dashboard_path = find_dashboard_files()
            if not self.dashboard_path:
                print("❌ Error: Could not find dashboard files")
                print("Please ensure Claude MPM is properly installed")
                return False

        # Validate that the dashboard path has the required files
        template_path = self.dashboard_path / "templates" / "index.html"
        static_path = self.dashboard_path / "static"

        if not template_path.exists():
            print(f"❌ Error: Dashboard template not found at {template_path}")
            print("Please ensure Claude MPM dashboard files are properly installed")
            return False

        if not static_path.exists():
            print(f"❌ Error: Dashboard static files not found at {static_path}")
            print("Please ensure Claude MPM dashboard files are properly installed")
            return False

        if self.debug:
            print(f"🔍 Debug: Dashboard path resolved to: {self.dashboard_path}")
            print("🔍 Debug: Checking for required files...")
            template_exists = (
                self.dashboard_path / "templates" / "index.html"
            ).exists()
            static_exists = (self.dashboard_path / "static").exists()
            print(f"   - templates/index.html: {template_exists}")
            print(f"   - static directory: {static_exists}")

        print(f"📁 Using dashboard files from: {self.dashboard_path}")

        # Create SocketIO server with improved timeout settings
        logger_enabled = self.debug  # Only enable verbose logging in debug mode
        self.sio = socketio.AsyncServer(
            cors_allowed_origins="*",
            logger=logger_enabled,
            engineio_logger=logger_enabled,
            ping_interval=30,  # Match client's 30 second ping interval
            ping_timeout=60,  # Match client's 60 second timeout
            max_http_buffer_size=1e8,  # Allow larger messages
        )
        # Create app WITHOUT any static file handlers to prevent directory listing
        # This is critical - we only want explicit routes we define
        self.app = web.Application()
        self.sio.attach(self.app)
        print("✅ SocketIO server created and attached")

        # Set up routes
        self._setup_routes()
        self._setup_socketio_events()

        print("✅ Server setup complete!")

        return True

    def _setup_routes(self):
        """Set up HTTP routes."""
        # IMPORTANT: Only add explicit routes, never add static file serving for root
        # This prevents aiohttp from serving directory listings
        self.app.router.add_get("/", self._serve_dashboard)
        self.app.router.add_get(
            "/index.html", self._serve_dashboard
        )  # Also handle /index.html
        self.app.router.add_get("/static/{path:.*}", self._serve_static)
        self.app.router.add_get("/api/directory/list", self._list_directory)
        self.app.router.add_get("/api/file/read", self._read_file)
        self.app.router.add_get("/version.json", self._serve_version)

        # New resilience endpoints
        self.app.router.add_get("/health", self._health_check)
        self.app.router.add_get("/api/status", self._serve_status)
        self.app.router.add_get("/api/events/history", self._serve_event_history)

        # CRITICAL: Add the missing /api/events endpoint for receiving events
        self.app.router.add_post("/api/events", self._receive_event)

    def _setup_socketio_events(self):
        """Set up SocketIO event handlers."""

        @self.sio.event
        async def connect(sid, environ):
            self.connected_clients.add(sid)
            if self.debug:
                print(f"✅ SocketIO client connected: {sid}")
                user_agent = environ.get("HTTP_USER_AGENT", "Unknown")
                # Truncate long user agents for readability
                if len(user_agent) > 80:
                    user_agent = user_agent[:77] + "..."
                print(f"   Client info: {user_agent}")

            # Send connection confirmation
            await self.sio.emit(
                "connection_test", {"status": "connected", "server": "stable"}, room=sid
            )

            # Send recent event history to new client
            if self.event_history:
                # Send last 20 events to catch up new client
                recent_events = list(self.event_history)[-20:]
                for event in recent_events:
                    await self.sio.emit("claude_event", event, room=sid)

        @self.sio.event
        async def disconnect(sid):
            self.connected_clients.discard(sid)
            if self.debug:
                print(f"📤 SocketIO client disconnected: {sid}")

        @self.sio.event
        async def code_analyze_file(sid, data):
            if self.debug:
                print(
                    f"📡 Received file analysis request from {sid}: {data.get('path', 'unknown')}"
                )

            file_path = data.get("path", "")
            file_name = file_path.split("/")[-1] if file_path else "unknown"

            # Create mock response
            response = create_mock_ast_data(file_path, file_name)

            if self.debug:
                print(
                    f"📤 Sending analysis response: {len(response['elements'])} elements"
                )
            await self.sio.emit("code:file:analyzed", response, room=sid)

        # CRITICAL: Handle the actual event name with colons that the client sends
        @self.sio.on("code:analyze:file")
        async def handle_code_analyze_file(sid, data):
            if self.debug:
                print(
                    f"📡 Received code:analyze:file from {sid}: {data.get('path', 'unknown')}"
                )

            file_path = data.get("path", "")
            file_name = file_path.split("/")[-1] if file_path else "unknown"

            # Create mock response
            response = create_mock_ast_data(file_path, file_name)

            if self.debug:
                print(
                    f"📤 Sending analysis response: {len(response['elements'])} elements"
                )
            await self.sio.emit("code:file:analyzed", response, room=sid)

        # Handle code analysis cancellation
        @self.sio.on("code:analysis:cancel")
        async def handle_code_analysis_cancel(sid, data=None):
            """Handle request to cancel code analysis."""
            if self.debug:
                print(f"📡 Received code:analysis:cancel from {sid}")
            
            # Send acknowledgment
            await self.sio.emit(
                "code:analysis:cancelled",
                {"status": "cancelled", "timestamp": datetime.now().isoformat()},
                room=sid,
            )
        
        # Handle other events the dashboard sends
        @self.sio.event
        async def get_git_branch(sid, data):
            if self.debug:
                print(f"📡 Received git branch request from {sid}: {data}")
            await self.sio.emit(
                "git_branch_response", {"branch": "main", "path": data}, room=sid
            )

        @self.sio.event
        async def request_status(sid, data):
            if self.debug:
                print(f"📡 Received status request from {sid}")
            await self.sio.emit(
                "status_response", {"status": "running", "server": "stable"}, room=sid
            )

        # Handle the event with dots (SocketIO converts colons to dots sometimes)
        @self.sio.event
        async def request_dot_status(sid, data):
            if self.debug:
                print(f"📡 Received request.status from {sid}")
            await self.sio.emit(
                "status_response", {"status": "running", "server": "stable"}, room=sid
            )

        # Handle directory discovery request with proper event name and response
        @self.sio.on("code:discover:top_level")
        async def handle_code_discover_top_level(sid, data):
            """Handle request to discover top-level directories."""
            if self.debug:
                print(f"📡 Received code:discover:top_level from {sid}: {data}")
            
            # Get the path from the request
            path = data.get("path", os.getcwd())
            request_id = data.get("request_id", "")
            
            # Read directory contents
            abs_path = os.path.abspath(os.path.expanduser(path))
            
            if not os.path.exists(abs_path):
                # Send error response
                await self.sio.emit(
                    "code:directory:discovered",
                    {
                        "error": f"Path does not exist: {abs_path}",
                        "path": abs_path,
                        "request_id": request_id,
                    },
                    room=sid,
                )
                return
            
            if not os.path.isdir(abs_path):
                # Send error response
                await self.sio.emit(
                    "code:directory:discovered",
                    {
                        "error": f"Path is not a directory: {abs_path}",
                        "path": abs_path,
                        "request_id": request_id,
                    },
                    room=sid,
                )
                return
            
            # Build directory contents
            contents = []
            try:
                for item in sorted(os.listdir(abs_path)):
                    # Skip hidden files and common non-code directories
                    if item.startswith(".") or item in ["node_modules", "__pycache__", "venv", ".venv"]:
                        continue
                    
                    item_path = os.path.join(abs_path, item)
                    is_dir = os.path.isdir(item_path)
                    
                    # Determine if it's a code file
                    is_code_file = False
                    if not is_dir:
                        ext = os.path.splitext(item)[1].lower()
                        is_code_file = ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h", ".hpp", ".cs", ".go", ".rs", ".rb", ".php"]
                    
                    contents.append({
                        "name": item,
                        "path": item_path,
                        "type": "directory" if is_dir else "file",
                        "is_directory": is_dir,
                        "is_file": not is_dir,
                        "is_code_file": is_code_file,
                    })
                    
            except PermissionError as e:
                # Send error response
                await self.sio.emit(
                    "code:directory:discovered",
                    {
                        "error": f"Permission denied: {str(e)}",
                        "path": abs_path,
                        "request_id": request_id,
                    },
                    room=sid,
                )
                return
            
            # Send successful response
            response = {
                "path": abs_path,
                "contents": contents,
                "request_id": request_id,
            }
            
            if self.debug:
                print(f"📤 Sending directory discovery response: {len(contents)} items")
            
            await self.sio.emit("code:directory:discovered", response, room=sid)

        # Mock event generator when no real events
        @self.sio.event
        async def request_mock_event(sid, data):
            """Generate a mock event for testing."""
            if self.debug:
                print(f"📡 Mock event requested by {sid}")

            mock_event = self._create_mock_event()
            # Store and broadcast like a real event
            self.event_count += 1
            self.last_event_time = datetime.now()
            self.event_history.append(mock_event)
            await self.sio.emit("claude_event", mock_event)

    def _create_mock_event(self) -> Dict[str, Any]:
        """Create a mock event for testing/demo purposes."""
        import random

        event_types = ["file", "command", "test", "build", "deploy"]
        event_subtypes = ["start", "progress", "complete", "error", "warning"]

        return {
            "type": random.choice(event_types),
            "subtype": random.choice(event_subtypes),
            "timestamp": datetime.now().isoformat(),
            "source": "mock",
            "data": {
                "message": f"Mock {random.choice(['operation', 'task', 'process'])} {random.choice(['started', 'completed', 'in progress'])}",
                "file": f"/path/to/file_{random.randint(1, 100)}.py",
                "line": random.randint(1, 500),
                "progress": random.randint(0, 100),
            },
            "session_id": "mock-session",
            "server_event_id": self.event_count + 1,
        }

    async def _start_mock_event_generator(self):
        """Start generating mock events if no real events for a while."""
        try:
            while True:
                await asyncio.sleep(30)  # Check every 30 seconds

                # If no events in last 60 seconds and clients connected, generate mock
                if self.connected_clients and (
                    not self.last_event_time
                    or (datetime.now() - self.last_event_time).total_seconds() > 60
                ):
                    if self.debug:
                        print("⏰ No recent events, generating mock event")

                    mock_event = self._create_mock_event()
                    self.event_count += 1
                    self.last_event_time = datetime.now()
                    self.event_history.append(mock_event)

                    await self.sio.emit("claude_event", mock_event)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Mock event generator error: {e}")

    async def _serve_dashboard(self, request):
        """Serve the main dashboard HTML with fallback."""
        dashboard_file = (
            self.dashboard_path / "templates" / "index.html"
            if self.dashboard_path
            else None
        )

        # Try to serve actual dashboard
        if dashboard_file and dashboard_file.exists():
            try:
                with open(dashboard_file, encoding="utf-8") as f:
                    content = f.read()
                return web.Response(text=content, content_type="text/html")
            except Exception as e:
                logger.error(f"Error reading dashboard template: {e}")
                # Fall through to fallback HTML

        # Fallback HTML if template missing or error
        fallback_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude MPM Dashboard - Fallback Mode</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 20px; background: #1e1e1e; color: #e0e0e0; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2d2d2d; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .status { background: #2d2d2d; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .status.healthy { border-left: 4px solid #4caf50; }
        .status.degraded { border-left: 4px solid #ff9800; }
        .events { background: #2d2d2d; padding: 20px; border-radius: 8px; }
        .event { background: #1e1e1e; padding: 10px; margin: 10px 0; border-radius: 4px; }
        h1 { color: #fff; margin: 0; }
        .subtitle { color: #999; margin-top: 5px; }
        .metric { display: inline-block; margin-right: 20px; }
        .metric-label { color: #999; font-size: 12px; }
        .metric-value { color: #fff; font-size: 20px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Claude MPM Dashboard</h1>
            <div class="subtitle">Fallback Mode - Template not found</div>
        </div>

        <div id="status" class="status healthy">
            <h3>Server Status</h3>
            <div class="metric">
                <div class="metric-label">Health</div>
                <div class="metric-value" id="health">Loading...</div>
            </div>
            <div class="metric">
                <div class="metric-label">Uptime</div>
                <div class="metric-value" id="uptime">Loading...</div>
            </div>
            <div class="metric">
                <div class="metric-label">Events</div>
                <div class="metric-value" id="events">Loading...</div>
            </div>
        </div>

        <div class="events">
            <h3>Recent Events</h3>
            <div id="event-list">
                <div class="event">Waiting for events...</div>
            </div>
        </div>
    </div>

    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script>
        // Fallback dashboard JavaScript
        const socket = io();

        // Update status periodically
        async function updateStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();

                document.getElementById('health').textContent = data.status;
                document.getElementById('uptime').textContent = data.uptime.human;
                document.getElementById('events').textContent = data.events.total;

                const statusDiv = document.getElementById('status');
                statusDiv.className = data.status === 'running' ? 'status healthy' : 'status degraded';
            } catch (e) {
                console.error('Failed to fetch status:', e);
            }
        }

        // Listen for events
        socket.on('claude_event', (event) => {
            const eventList = document.getElementById('event-list');
            const eventDiv = document.createElement('div');
            eventDiv.className = 'event';
            eventDiv.textContent = JSON.stringify(event, null, 2);
            eventList.insertBefore(eventDiv, eventList.firstChild);

            // Keep only last 10 events
            while (eventList.children.length > 10) {
                eventList.removeChild(eventList.lastChild);
            }
        });

        socket.on('connect', () => {
            console.log('Connected to dashboard server');
        });

        // Initial load and periodic updates
        updateStatus();
        setInterval(updateStatus, 5000);
    </script>
</body>
</html>
        """

        logger.warning("Serving fallback dashboard HTML")
        return web.Response(text=fallback_html, content_type="text/html")

    async def _serve_static(self, request):
        """Serve static files with cache prevention."""
        file_path = request.match_info["path"]
        static_file = self.dashboard_path / "static" / file_path

        if static_file.exists() and static_file.is_file():
            content_type = (
                "text/javascript"
                if file_path.endswith(".js")
                else "text/css" if file_path.endswith(".css") else "text/plain"
            )
            with open(static_file) as f:
                content = f.read()
            
            # Add cache prevention headers to ensure fresh JavaScript
            headers = {
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
            return web.Response(text=content, content_type=content_type, headers=headers)
        return web.Response(text="File not found", status=404)

    async def _list_directory(self, request):
        """List directory contents."""
        path = request.query.get("path", ".")
        abs_path = os.path.abspath(os.path.expanduser(path))

        result = {"path": abs_path, "exists": os.path.exists(abs_path), "contents": []}

        if os.path.exists(abs_path) and os.path.isdir(abs_path):
            try:
                for item in sorted(os.listdir(abs_path)):
                    item_path = os.path.join(abs_path, item)
                    result["contents"].append(
                        {
                            "name": item,
                            "path": item_path,
                            "is_directory": os.path.isdir(item_path),
                            "is_file": os.path.isfile(item_path),
                            "is_code_file": item.endswith(
                                (".py", ".js", ".ts", ".jsx", ".tsx")
                            ),
                        }
                    )
            except PermissionError:
                result["error"] = "Permission denied"

        return web.json_response(result)

    async def _read_file(self, request):
        """Read file content for source viewer."""
        file_path = request.query.get("path", "")

        if not file_path:
            return web.json_response({"error": "No path provided"}, status=400)

        abs_path = os.path.abspath(os.path.expanduser(file_path))

        # Security check - ensure file is within the project
        try:
            # Get the project root (current working directory)
            project_root = os.getcwd()
            # Ensure the path is within the project
            if not abs_path.startswith(project_root):
                return web.json_response({"error": "Access denied"}, status=403)
        except Exception:
            pass  # Allow read if we can't determine project root

        if not os.path.exists(abs_path):
            return web.json_response({"error": "File not found"}, status=404)

        if not os.path.isfile(abs_path):
            return web.json_response({"error": "Not a file"}, status=400)

        try:
            # Determine file type
            file_ext = os.path.splitext(abs_path)[1].lower()
            is_json = file_ext in [".json", ".jsonl", ".geojson"]

            # Read file with appropriate encoding
            encodings = ["utf-8", "latin-1", "cp1252"]
            content = None

            for encoding in encodings:
                try:
                    with open(abs_path, encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                return web.json_response({"error": "Could not decode file"}, status=400)

            # Format JSON files for better readability
            formatted_content = content
            is_valid_json = False
            if is_json:
                try:
                    import json

                    parsed = json.loads(content)
                    formatted_content = json.dumps(parsed, indent=2, sort_keys=False)
                    is_valid_json = True
                except json.JSONDecodeError:
                    # Not valid JSON, return as-is
                    is_valid_json = False

            return web.json_response(
                {
                    "path": abs_path,
                    "name": os.path.basename(abs_path),
                    "content": formatted_content,
                    "lines": len(formatted_content.splitlines()),
                    "size": os.path.getsize(abs_path),
                    "type": "json" if is_json else "text",
                    "is_valid_json": is_valid_json,
                }
            )

        except PermissionError:
            return web.json_response({"error": "Permission denied"}, status=403)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def _health_check(self, request):
        """Health check endpoint for monitoring."""
        uptime = time.time() - self.server_start_time
        status = "healthy" if self.is_healthy else "degraded"

        health_info = {
            "status": status,
            "uptime_seconds": round(uptime, 2),
            "connected_clients": len(self.connected_clients),
            "event_count": self.event_count,
            "last_event": (
                self.last_event_time.isoformat() if self.last_event_time else None
            ),
            "retry_count": self.retry_count,
            "health_check_failures": self.health_check_failures,
            "event_history_size": len(self.event_history),
        }

        status_code = 200 if self.is_healthy else 503
        return web.json_response(health_info, status=status_code)

    async def _serve_status(self, request):
        """Detailed server status endpoint."""
        uptime = time.time() - self.server_start_time

        status_info = {
            "server": "stable",
            "version": "4.2.3",
            "status": "running" if self.is_healthy else "degraded",
            "uptime": {
                "seconds": round(uptime, 2),
                "human": self._format_uptime(uptime),
            },
            "connections": {
                "active": len(self.connected_clients),
                "clients": list(self.connected_clients),
            },
            "events": {
                "total": self.event_count,
                "buffered": len(self.event_history),
                "last_received": (
                    self.last_event_time.isoformat() if self.last_event_time else None
                ),
            },
            "features": [
                "http",
                "socketio",
                "event_bridge",
                "health_monitoring",
                "auto_retry",
                "event_history",
                "graceful_degradation",
            ],
            "resilience": {
                "retry_count": self.retry_count,
                "max_retries": self.max_retries,
                "health_failures": self.health_check_failures,
                "persist_events": self.persist_events,
            },
        }
        return web.json_response(status_info)

    async def _serve_event_history(self, request):
        """Serve recent event history."""
        limit = int(request.query.get("limit", "100"))
        events = list(self.event_history)[-limit:]
        return web.json_response(
            {"events": events, "count": len(events), "total_events": self.event_count}
        )

    async def _receive_event(self, request):
        """Receive events from hook system via HTTP POST."""
        try:
            # Parse event data
            data = await request.json()

            # Add server metadata
            event = {
                **data,
                "received_at": datetime.now().isoformat(),
                "server_event_id": self.event_count + 1,
            }

            # Update tracking
            self.event_count += 1
            self.last_event_time = datetime.now()

            # Store in circular buffer
            self.event_history.append(event)

            # Persist to disk if enabled
            if self.persist_events:
                try:
                    with open(self.event_log_path, "a") as f:
                        f.write(json.dumps(event) + "\n")
                except Exception as e:
                    logger.error(f"Failed to persist event: {e}")

            # Emit to all connected SocketIO clients
            if self.sio and self.connected_clients:
                await self.sio.emit("claude_event", event)
                if self.debug:
                    print(
                        f"📡 Forwarded event to {len(self.connected_clients)} clients"
                    )

            # Return success response
            return web.json_response(
                {
                    "status": "received",
                    "event_id": event["server_event_id"],
                    "clients_notified": len(self.connected_clients),
                }
            )

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in event request: {e}")
            return web.json_response(
                {"error": "Invalid JSON", "details": str(e)}, status=400
            )
        except Exception as e:
            logger.error(f"Error processing event: {e}")
            if self.debug:
                traceback.print_exc()
            return web.json_response(
                {"error": "Failed to process event", "details": str(e)}, status=500
            )

    async def _serve_version(self, request):
        """Serve version information."""
        version_info = {
            "version": "4.2.3",
            "server": "stable",
            "features": ["http", "socketio", "event_bridge", "resilience"],
            "status": "running" if self.is_healthy else "degraded",
        }
        return web.json_response(version_info)

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")

        return " ".join(parts)

    def run(self):
        """Run the server with automatic restart on crash."""
        restart_attempts = 0
        max_restart_attempts = 5

        while restart_attempts < max_restart_attempts:
            try:
                print(
                    f"🔧 Setting up server... (attempt {restart_attempts + 1}/{max_restart_attempts})"
                )

                # Reset health status on restart
                self.is_healthy = True
                self.health_check_failures = 0

                if not self.setup():
                    if not DEPENDENCIES_AVAILABLE:
                        print("❌ Missing required dependencies")
                        return False

                    # Continue with fallback mode even if dashboard files not found
                    print("⚠️  Dashboard files not found - running in fallback mode")
                    print(
                        "   Server will provide basic functionality and receive events"
                    )

                    # Set up minimal server without dashboard files
                    self.sio = socketio.AsyncServer(
                        cors_allowed_origins="*",
                        logger=self.debug,
                        engineio_logger=self.debug,
                        ping_interval=30,
                        ping_timeout=60,
                        max_http_buffer_size=1e8,
                    )
                    self.app = web.Application()
                    self.sio.attach(self.app)
                    self._setup_routes()
                    self._setup_socketio_events()

                return self._run_with_resilience()

            except Exception as e:
                restart_attempts += 1
                logger.error(f"Server crashed: {e}")
                if self.debug:
                    traceback.print_exc()

                if restart_attempts < max_restart_attempts:
                    wait_time = min(
                        2**restart_attempts, 30
                    )  # Exponential backoff, max 30s
                    print(f"🔄 Restarting server in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(
                        f"❌ Server failed after {max_restart_attempts} restart attempts"
                    )
                    return False

        return False

    def _run_with_resilience(self):
        """Run server with port conflict resolution and error handling."""

        print(f"🚀 Starting stable dashboard server at http://{self.host}:{self.port}")
        print("✅ Server ready: HTTP + SocketIO with resilience features")
        print("🛡️  Resilience features enabled:")
        print("   - Automatic restart on crash")
        print("   - Health monitoring endpoint (/health)")
        print("   - Event history buffer (500 events)")
        print("   - Graceful degradation")
        print("   - Connection retry logic")
        print("📡 SocketIO events:")
        print("   - claude_event (real-time events from hooks)")
        print("   - code:analyze:file (code analysis)")
        print("   - connection management")
        print("🌐 HTTP endpoints:")
        print("   - GET /             (dashboard)")
        print("   - GET /health       (health check)")
        print("   - POST /api/events  (receive hook events)")
        print("   - GET /api/status   (detailed status)")
        print("   - GET /api/events/history (event history)")
        print("   - GET /api/directory/list")
        print("   - GET /api/file/read")
        print(f"\n🔗 Open in browser: http://{self.host}:{self.port}")
        print("\n   Press Ctrl+C to stop the server\n")

        # Try to start server with port conflict handling
        max_port_attempts = 10
        original_port = self.port

        for attempt in range(max_port_attempts):
            try:
                # Use the print_func parameter to control access log output
                if self.debug:
                    web.run_app(self.app, host=self.host, port=self.port)
                else:
                    web.run_app(
                        self.app,
                        host=self.host,
                        port=self.port,
                        access_log=None,
                        print=lambda *args: None,  # Suppress startup messages in non-debug mode
                    )
                return True  # Server started successfully
            except KeyboardInterrupt:
                print("\n🛑 Server stopped by user")
                return True
            except OSError as e:
                error_str = str(e)
                if (
                    "[Errno 48]" in error_str
                    or "Address already in use" in error_str
                    or "address already in use" in error_str.lower()
                ):
                    # Port is already in use
                    if attempt < max_port_attempts - 1:
                        self.port += 1
                        print(
                            f"⚠️  Port {self.port - 1} is in use, trying port {self.port}..."
                        )
                        # Recreate the app with new port
                        self.setup()
                    else:
                        print(
                            f"❌ Could not find available port after {max_port_attempts} attempts"
                        )
                        print(f"   Ports {original_port} to {self.port} are all in use")
                        print(
                            "\n💡 Tip: Check if another dashboard instance is running"
                        )
                        print("   You can stop it with: claude-mpm dashboard stop")
                        return False
                else:
                    # Other OS error
                    print(f"❌ Server error: {e}")
                    if self.debug:
                        import traceback

                        traceback.print_exc()
                    return False
            except Exception as e:
                print(f"❌ Unexpected server error: {e}")
                if self.debug:
                    import traceback

                    traceback.print_exc()
                else:
                    print("\n💡 Run with --debug flag for more details")
                return False

        return True


def create_stable_server(
    dashboard_path: Optional[Path] = None, **kwargs
) -> StableDashboardServer:
    """Create a stable dashboard server instance."""
    server = StableDashboardServer(**kwargs)
    if dashboard_path:
        server.dashboard_path = dashboard_path
    return server
