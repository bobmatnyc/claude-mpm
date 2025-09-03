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

import glob
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

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

    def setup(self) -> bool:
        """Set up the server components."""
        if not DEPENDENCIES_AVAILABLE:
            print(
                "❌ Error: Missing dependencies. Install with: pip install aiohttp python-socketio"
            )
            return False

        # Find dashboard files
        self.dashboard_path = find_dashboard_files()
        if not self.dashboard_path:
            print("❌ Error: Could not find dashboard files")
            print("Please ensure Claude MPM is properly installed")
            return False

        print(f"📁 Using dashboard files from: {self.dashboard_path}")

        # Create SocketIO server with improved timeout settings
        self.sio = socketio.AsyncServer(
            cors_allowed_origins="*",
            logger=True,
            engineio_logger=True,
            ping_interval=30,  # Match client's 30 second ping interval
            ping_timeout=60,  # Match client's 60 second timeout
            max_http_buffer_size=1e8,  # Allow larger messages
        )
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
        self.app.router.add_get("/", self._serve_dashboard)
        self.app.router.add_get("/static/{path:.*}", self._serve_static)
        self.app.router.add_get("/api/directory/list", self._list_directory)
        self.app.router.add_get("/api/file/read", self._read_file)
        self.app.router.add_get("/version.json", self._serve_version)

    def _setup_socketio_events(self):
        """Set up SocketIO event handlers."""

        @self.sio.event
        async def connect(sid, environ):
            print(f"✅ SocketIO client connected: {sid}")
            print(f"   Client info: {environ.get('HTTP_USER_AGENT', 'Unknown')}")
            # Send a test message to confirm connection
            await self.sio.emit(
                "connection_test", {"status": "connected", "server": "stable"}, room=sid
            )

        @self.sio.event
        async def disconnect(sid):
            print(f"❌ SocketIO client disconnected: {sid}")

        @self.sio.event
        async def code_analyze_file(sid, data):
            print(
                f"📡 Received file analysis request from {sid}: {data.get('path', 'unknown')}"
            )

            file_path = data.get("path", "")
            file_name = file_path.split("/")[-1] if file_path else "unknown"

            # Create mock response
            response = create_mock_ast_data(file_path, file_name)

            print(f"📤 Sending analysis response: {len(response['elements'])} elements")
            await self.sio.emit("code:file:analyzed", response, room=sid)

        # CRITICAL: Handle the actual event name with colons that the client sends
        @self.sio.on("code:analyze:file")
        async def handle_code_analyze_file(sid, data):
            print(
                f"📡 Received code:analyze:file from {sid}: {data.get('path', 'unknown')}"
            )

            file_path = data.get("path", "")
            file_name = file_path.split("/")[-1] if file_path else "unknown"

            # Create mock response
            response = create_mock_ast_data(file_path, file_name)

            print(f"📤 Sending analysis response: {len(response['elements'])} elements")
            await self.sio.emit("code:file:analyzed", response, room=sid)

        # Handle other events the dashboard sends
        @self.sio.event
        async def get_git_branch(sid, data):
            print(f"📡 Received git branch request from {sid}: {data}")
            await self.sio.emit(
                "git_branch_response", {"branch": "main", "path": data}, room=sid
            )

        @self.sio.event
        async def request_status(sid, data):
            print(f"📡 Received status request from {sid}")
            await self.sio.emit(
                "status_response", {"status": "running", "server": "stable"}, room=sid
            )

        # Handle the event with dots (SocketIO converts colons to dots sometimes)
        @self.sio.event
        async def request_dot_status(sid, data):
            print(f"📡 Received request.status from {sid}")
            await self.sio.emit(
                "status_response", {"status": "running", "server": "stable"}, room=sid
            )

        @self.sio.event
        async def code_discover_top_level(sid, data):
            print(f"📡 Received top-level discovery request from {sid}")
            await self.sio.emit("code:top_level:discovered", {"status": "ok"}, room=sid)

    async def _serve_dashboard(self, request):
        """Serve the main dashboard HTML."""
        dashboard_file = self.dashboard_path / "templates" / "index.html"
        if dashboard_file.exists():
            with open(dashboard_file) as f:
                content = f.read()
            return web.Response(text=content, content_type="text/html")
        return web.Response(text="Dashboard not found", status=404)

    async def _serve_static(self, request):
        """Serve static files."""
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
            return web.Response(text=content, content_type=content_type)
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

            return web.json_response(
                {
                    "path": abs_path,
                    "name": os.path.basename(abs_path),
                    "content": content,
                    "lines": len(content.splitlines()),
                    "size": os.path.getsize(abs_path),
                }
            )

        except PermissionError:
            return web.json_response({"error": "Permission denied"}, status=403)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def _serve_version(self, request):
        """Serve version information."""
        version_info = {
            "version": "4.2.2",
            "server": "stable",
            "features": ["http", "socketio", "mock_ast"],
            "status": "running",
        }
        return web.json_response(version_info)

    def run(self):
        """Run the server with automatic port conflict resolution."""
        print("🔧 Setting up server...")
        if not self.setup():
            print("❌ Server setup failed")
            return False

        print(f"🚀 Starting stable dashboard server at http://{self.host}:{self.port}")
        print("✅ Server ready: HTTP + SocketIO on same port")
        print("📡 SocketIO events registered:")
        print("   - connect/disconnect")
        print("   - code_analyze_file (from 'code:analyze:file')")
        print("🌐 HTTP endpoints available:")
        print("   - GET / (dashboard)")
        print("   - GET /static/* (static files)")
        print("   - GET /api/directory/list (directory API)")
        print(f"🔗 Open in browser: http://{self.host}:{self.port}")

        # Try to start server with port conflict handling
        max_port_attempts = 10
        original_port = self.port

        for attempt in range(max_port_attempts):
            try:
                web.run_app(self.app, host=self.host, port=self.port, access_log=None)
                break  # Server started successfully
            except KeyboardInterrupt:
                print("\n🛑 Server stopped by user")
                break
            except OSError as e:
                if "[Errno 48]" in str(e) or "Address already in use" in str(e):
                    # Port is already in use, try next port
                    if attempt < max_port_attempts - 1:
                        self.port += 1
                        print(
                            f"⚠️ Port {self.port - 1} in use, trying port {self.port}..."
                        )
                        # Recreate the app with new port
                        self.setup()
                    else:
                        print(
                            f"❌ Could not find available port after {max_port_attempts} attempts"
                        )
                        print(f"   Ports {original_port} to {self.port} are all in use")
                        return False
                else:
                    # Other OS error
                    print(f"❌ Server error: {e}")
                    if self.debug:
                        import traceback

                        traceback.print_exc()
                    return False
            except Exception as e:
                print(f"❌ Server error: {e}")
                if self.debug:
                    import traceback

                    traceback.print_exc()
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
