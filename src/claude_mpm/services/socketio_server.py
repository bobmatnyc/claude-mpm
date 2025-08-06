"""Socket.IO server for real-time monitoring of Claude MPM sessions.

WHY: This provides a Socket.IO-based alternative to the WebSocket server,
offering improved connection reliability and automatic reconnection.
Socket.IO handles connection drops gracefully and provides better
cross-platform compatibility.
"""

import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Set, Dict, Any, Optional, List
from collections import deque

try:
    import socketio
    import aiohttp
    from aiohttp import web
    SOCKETIO_AVAILABLE = True
    # Don't print at module level - this causes output during imports
    # Version will be logged when server is actually started
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None
    aiohttp = None
    web = None
    # Don't print warnings at module level

from ..core.logger import get_logger
from ..deployment_paths import get_project_root, get_scripts_dir


class SocketIOClientProxy:
    """Proxy that connects to an existing Socket.IO server as a client.
    
    WHY: In exec mode, a persistent Socket.IO server runs in a separate process.
    The hook handler in the Claude process needs a Socket.IO-like interface
    but shouldn't start another server. This proxy provides that interface
    while the actual events are handled by the persistent server.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.logger = get_logger("socketio_client_proxy")
        self.running = True  # Always "running" for compatibility
        self._sio_client = None
        self._client_thread = None
        self._client_loop = None
        
    def start(self):
        """Start the Socket.IO client connection to the persistent server."""
        self.logger.debug(f"SocketIOClientProxy: Connecting to server on {self.host}:{self.port}")
        if SOCKETIO_AVAILABLE:
            self._start_client()
        
    def stop(self):
        """Stop the Socket.IO client connection."""
        self.logger.debug(f"SocketIOClientProxy: Disconnecting from server")
        if self._sio_client:
            self._sio_client.disconnect()
        
    def _start_client(self):
        """Start Socket.IO client in a background thread."""
        def run_client():
            self._client_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._client_loop)
            try:
                self._client_loop.run_until_complete(self._connect_and_run())
            except Exception as e:
                self.logger.error(f"SocketIOClientProxy client thread error: {e}")
            finally:
                self._client_loop.close()
            
        self._client_thread = threading.Thread(target=run_client, daemon=True)
        self._client_thread.start()
        # Give it a moment to connect
        time.sleep(0.2)
        
    async def _connect_and_run(self):
        """Connect to the persistent Socket.IO server and keep connection alive."""
        try:
            self._sio_client = socketio.AsyncClient()
            
            @self._sio_client.event
            async def connect():
                self.logger.info(f"SocketIOClientProxy: Connected to server at http://{self.host}:{self.port}")
                
            @self._sio_client.event
            async def disconnect():
                self.logger.info(f"SocketIOClientProxy: Disconnected from server")
                
            # Connect to the server
            await self._sio_client.connect(f'http://127.0.0.1:{self.port}')
            
            # Keep the connection alive until stopped
            while self.running:
                await asyncio.sleep(1)
                    
        except Exception as e:
            self.logger.error(f"SocketIOClientProxy: Connection error: {e}")
            self._sio_client = None
        
    def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """Send event to the persistent Socket.IO server."""
        if not SOCKETIO_AVAILABLE:
            return
            
        # Ensure client is started
        if not self._client_thread or not self._client_thread.is_alive():
            self.logger.debug(f"SocketIOClientProxy: Starting client for {event_type}")
            self._start_client()
            
        if self._sio_client and self._sio_client.connected:
            try:
                event = {
                    "type": event_type,
                    "timestamp": datetime.now().isoformat(),
                    "data": data
                }
                
                # Send event safely using run_coroutine_threadsafe
                if hasattr(self, '_client_loop') and self._client_loop and not self._client_loop.is_closed():
                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            self._sio_client.emit('claude_event', event),
                            self._client_loop
                        )
                        # Don't wait for the result to avoid blocking
                        self.logger.debug(f"SocketIOClientProxy: Scheduled emit for {event_type}")
                    except Exception as e:
                        self.logger.error(f"SocketIOClientProxy: Failed to schedule emit for {event_type}: {e}")
                else:
                    self.logger.warning(f"SocketIOClientProxy: Client event loop not available for {event_type}")
                
                self.logger.debug(f"SocketIOClientProxy: Sent event {event_type}")
            except Exception as e:
                self.logger.error(f"SocketIOClientProxy: Failed to send event {event_type}: {e}")
        else:
            self.logger.warning(f"SocketIOClientProxy: Client not ready for {event_type}")
    
    # Compatibility methods for WebSocketServer interface
    def session_started(self, session_id: str, launch_method: str, working_dir: str):
        self.logger.debug(f"SocketIOClientProxy: Session started {session_id}")
        
    def session_ended(self):
        self.logger.debug(f"SocketIOClientProxy: Session ended")
        
    def claude_status_changed(self, status: str, pid: Optional[int] = None, message: str = ""):
        self.logger.debug(f"SocketIOClientProxy: Claude status {status}")
        
    def agent_delegated(self, agent: str, task: str, status: str = "started"):
        self.logger.debug(f"SocketIOClientProxy: Agent {agent} delegated")
        
    def todo_updated(self, todos: List[Dict[str, Any]]):
        self.logger.debug(f"SocketIOClientProxy: Todo updated ({len(todos)} todos)")


class SocketIOServer:
    """Socket.IO server for broadcasting Claude MPM events.
    
    WHY: Socket.IO provides better connection reliability than raw WebSockets,
    with automatic reconnection, fallback transports, and better error handling.
    It maintains the same event interface as WebSocketServer for compatibility.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.logger = get_logger("socketio_server")
        self.clients: Set[str] = set()  # Store session IDs instead of connection objects
        self.event_history: deque = deque(maxlen=1000)  # Keep last 1000 events
        self.sio = None
        self.app = None
        self.runner = None
        self.site = None
        self.loop = None
        self.thread = None
        self.running = False
        
        # Session state
        self.session_id = None
        self.session_start = None
        self.claude_status = "stopped"
        self.claude_pid = None
        
        if not SOCKETIO_AVAILABLE:
            self.logger.warning("Socket.IO support not available. Install 'python-socketio' and 'aiohttp' packages to enable.")
        else:
            # Log version info when server is actually created
            try:
                version = getattr(socketio, '__version__', 'unknown')
                self.logger.info(f"Socket.IO server using python-socketio v{version}")
            except:
                self.logger.info("Socket.IO server using python-socketio (version unavailable)")
        
    def start(self):
        """Start the Socket.IO server in a background thread."""
        if not SOCKETIO_AVAILABLE:
            self.logger.debug("Socket.IO server skipped - required packages not installed")
            return
            
        if self.running:
            self.logger.debug(f"Socket.IO server already running on port {self.port}")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        self.logger.info(f"🚀 Socket.IO server STARTING on http://{self.host}:{self.port}")
        self.logger.info(f"🔧 Thread created: {self.thread.name} (daemon={self.thread.daemon})")
        
        # Give server a moment to start
        time.sleep(0.1)
        
        if self.thread.is_alive():
            self.logger.info(f"✅ Socket.IO server thread is alive and running")
        else:
            self.logger.error(f"❌ Socket.IO server thread failed to start!")
        
    def stop(self):
        """Stop the Socket.IO server."""
        self.running = False
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._shutdown(), self.loop)
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("Socket.IO server stopped")
        
    def _run_server(self):
        """Run the server event loop."""
        self.logger.info(f"🔄 _run_server starting on thread: {threading.current_thread().name}")
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.logger.info(f"📡 Event loop created and set for Socket.IO server")
        
        try:
            self.logger.info(f"🎯 About to start _serve() coroutine")
            self.loop.run_until_complete(self._serve())
        except Exception as e:
            self.logger.error(f"❌ Socket.IO server error in _run_server: {e}")
            import traceback
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
        finally:
            self.logger.info(f"🔚 Socket.IO server _run_server shutting down")
            self.loop.close()
            
    async def _serve(self):
        """Start the Socket.IO server."""
        try:
            self.logger.info(f"🔌 _serve() starting - attempting to bind to {self.host}:{self.port}")
            
            # Create Socket.IO server with improved configuration
            self.sio = socketio.AsyncServer(
                cors_allowed_origins="*",
                ping_timeout=120,
                ping_interval=30,
                max_http_buffer_size=1000000,
                allow_upgrades=True,
                transports=['websocket', 'polling'],
                logger=False,  # Reduce noise in logs
                engineio_logger=False
            )
            
            # Create aiohttp web application
            self.app = web.Application()
            self.sio.attach(self.app)
            
            # Add CORS middleware
            import aiohttp_cors
            cors = aiohttp_cors.setup(self.app, defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*"
                )
            })
            
            # Add HTTP routes
            self.app.router.add_get('/health', self._handle_health)
            self.app.router.add_get('/status', self._handle_health)
            self.app.router.add_get('/api/git-diff', self._handle_git_diff)
            self.app.router.add_options('/api/git-diff', self._handle_cors_preflight)
            self.app.router.add_get('/api/file-content', self._handle_file_content)
            self.app.router.add_options('/api/file-content', self._handle_cors_preflight)
            
            # Add dashboard routes
            self.app.router.add_get('/', self._handle_dashboard)
            self.app.router.add_get('/dashboard', self._handle_dashboard)
            
            # Add static file serving for web assets
            static_path = get_project_root() / 'src' / 'claude_mpm' / 'dashboard' / 'static'
            if static_path.exists():
                self.app.router.add_static('/static/', path=str(static_path), name='static')
            
            # Register event handlers
            self._register_events()
            
            # Start the server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
            
            self.logger.info(f"🎉 Socket.IO server SUCCESSFULLY listening on http://{self.host}:{self.port}")
            
            # Keep server running
            loop_count = 0
            while self.running:
                await asyncio.sleep(0.1)
                loop_count += 1
                if loop_count % 100 == 0:  # Log every 10 seconds
                    self.logger.debug(f"🔄 Socket.IO server heartbeat - {len(self.clients)} clients connected")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to start Socket.IO server: {e}")
            import traceback
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            raise
                
    async def _shutdown(self):
        """Shutdown the server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
            
    async def _handle_health(self, request):
        """Handle health check requests."""
        return web.json_response({
            "status": "healthy",
            "server": "claude-mpm-python-socketio",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "port": self.port,
            "host": self.host,
            "clients_connected": len(self.clients)
        }, headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Accept'
        })

    async def _handle_dashboard(self, request):
        """Serve the dashboard HTML file."""
        dashboard_path = get_project_root() / 'src' / 'claude_mpm' / 'dashboard' / 'templates' / 'index.html'
        self.logger.info(f"Dashboard requested, looking for: {dashboard_path}")
        self.logger.info(f"Path exists: {dashboard_path.exists()}")
        if dashboard_path.exists():
            return web.FileResponse(str(dashboard_path))
        else:
            return web.Response(text=f"Dashboard not found at: {dashboard_path}", status=404)
    
    async def _handle_cors_preflight(self, request):
        """Handle CORS preflight requests."""
        return web.Response(
            status=200,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Accept, Authorization',
                'Access-Control-Max-Age': '86400'
            }
        )
        
    async def _handle_git_diff(self, request):
        """Handle git diff requests for file operations.
        
        Expected query parameters:
        - file: The file path to generate diff for
        - timestamp: ISO timestamp of the operation (optional)
        - working_dir: Working directory for git operations (optional)
        """
        try:
            # Extract query parameters
            file_path = request.query.get('file')
            timestamp = request.query.get('timestamp')
            working_dir = request.query.get('working_dir', os.getcwd())
            
            self.logger.info(f"Git diff API request: file={file_path}, timestamp={timestamp}, working_dir={working_dir}")
            self.logger.info(f"Git diff request details: query_params={dict(request.query)}, file_exists={os.path.exists(file_path) if file_path else False}")
            
            if not file_path:
                self.logger.warning("Git diff request missing file parameter")
                return web.json_response({
                    "success": False,
                    "error": "Missing required parameter: file"
                }, status=400, headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Accept'
                })
            
            self.logger.debug(f"Git diff requested for file: {file_path}, timestamp: {timestamp}")
            
            # Generate git diff using the _generate_git_diff helper
            diff_result = await self._generate_git_diff(file_path, timestamp, working_dir)
            
            self.logger.info(f"Git diff result: success={diff_result.get('success', False)}, method={diff_result.get('method', 'unknown')}")
            
            return web.json_response(diff_result, headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Accept'
            })
            
        except Exception as e:
            self.logger.error(f"Error generating git diff: {e}")
            import traceback
            self.logger.error(f"Git diff error traceback: {traceback.format_exc()}")
            return web.json_response({
                "success": False,
                "error": f"Failed to generate git diff: {str(e)}"
            }, status=500, headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Accept'
            })
    
    async def _handle_file_content(self, request):
        """Handle file content requests via HTTP API.
        
        Expected query parameters:
        - file_path: The file path to read
        - working_dir: Working directory for file operations (optional)
        - max_size: Maximum file size in bytes (optional, default 1MB)
        """
        try:
            # Extract query parameters
            file_path = request.query.get('file_path')
            working_dir = request.query.get('working_dir', os.getcwd())
            max_size = int(request.query.get('max_size', 1024 * 1024))  # 1MB default
            
            self.logger.info(f"File content API request: file_path={file_path}, working_dir={working_dir}")
            
            if not file_path:
                self.logger.warning("File content request missing file_path parameter")
                return web.json_response({
                    "success": False,
                    "error": "Missing required parameter: file_path"
                }, status=400, headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Accept'
                })
            
            # Use the same file reading logic as the Socket.IO handler
            result = await self._read_file_safely(file_path, working_dir, max_size)
            
            status_code = 200 if result.get('success') else 400
            return web.json_response(result, status=status_code, headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',  
                'Access-Control-Allow-Headers': 'Content-Type, Accept'
            })
            
        except Exception as e:
            self.logger.error(f"Error reading file content: {e}")
            import traceback
            self.logger.error(f"File content error traceback: {traceback.format_exc()}")
            return web.json_response({
                "success": False,
                "error": f"Failed to read file: {str(e)}"
            }, status=500, headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Accept'
            })
    
    async def _read_file_safely(self, file_path: str, working_dir: str = None, max_size: int = 1024 * 1024):
        """Safely read file content with security checks.
        
        This method contains the core file reading logic that can be used by both
        HTTP API endpoints and Socket.IO event handlers.
        
        Args:
            file_path: Path to the file to read
            working_dir: Working directory (defaults to current directory)
            max_size: Maximum file size in bytes
            
        Returns:
            dict: Response with success status, content, and metadata
        """
        try:
            if working_dir is None:
                working_dir = os.getcwd()
                
            # Resolve absolute path based on working directory
            if not os.path.isabs(file_path):
                full_path = os.path.join(working_dir, file_path)
            else:
                full_path = file_path
            
            # Security check: ensure file is within working directory or project
            try:
                real_path = os.path.realpath(full_path)
                real_working_dir = os.path.realpath(working_dir)
                
                # Allow access to files within working directory or the project root
                project_root = os.path.realpath(get_project_root())
                allowed_paths = [real_working_dir, project_root]
                
                is_allowed = any(real_path.startswith(allowed_path) for allowed_path in allowed_paths)
                
                if not is_allowed:
                    return {
                        'success': False,
                        'error': 'Access denied: file is outside allowed directories',
                        'file_path': file_path
                    }
                    
            except Exception as path_error:
                self.logger.error(f"Path validation error: {path_error}")
                return {
                    'success': False,
                    'error': 'Invalid file path',
                    'file_path': file_path
                }
            
            # Check if file exists
            if not os.path.exists(real_path):
                return {
                    'success': False,
                    'error': 'File does not exist',
                    'file_path': file_path
                }
            
            # Check if it's a file (not directory)
            if not os.path.isfile(real_path):
                return {
                    'success': False,
                    'error': 'Path is not a file',
                    'file_path': file_path
                }
            
            # Check file size
            file_size = os.path.getsize(real_path)
            if file_size > max_size:
                return {
                    'success': False,
                    'error': f'File too large ({file_size} bytes). Maximum allowed: {max_size} bytes',
                    'file_path': file_path,
                    'file_size': file_size
                }
            
            # Read file content
            try:
                with open(real_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Get file extension for syntax highlighting hint
                _, ext = os.path.splitext(real_path)
                
                return {
                    'success': True,
                    'file_path': file_path,
                    'content': content,
                    'file_size': file_size,
                    'extension': ext.lower(),
                    'encoding': 'utf-8'
                }
                
            except UnicodeDecodeError:
                # Try reading as binary if UTF-8 fails
                try:
                    with open(real_path, 'rb') as f:
                        binary_content = f.read()
                    
                    # Check if it's a text file by looking for common text patterns
                    try:
                        text_content = binary_content.decode('latin-1')
                        if '\x00' in text_content:
                            # Binary file
                            return {
                                'success': False,
                                'error': 'File appears to be binary and cannot be displayed as text',
                                'file_path': file_path,
                                'file_size': file_size
                            }
                        else:
                            # Text file with different encoding
                            _, ext = os.path.splitext(real_path)
                            return {
                                'success': True,
                                'file_path': file_path,
                                'content': text_content,
                                'file_size': file_size,
                                'extension': ext.lower(),
                                'encoding': 'latin-1'
                            }
                    except Exception:
                        return {
                            'success': False,
                            'error': 'File encoding not supported',
                            'file_path': file_path
                        }
                except Exception as read_error:
                    return {
                        'success': False,
                        'error': f'Failed to read file: {str(read_error)}',
                        'file_path': file_path
                    }
                    
        except Exception as e:
            self.logger.error(f"Error in _read_file_safely: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path
            }
    
    async def _generate_git_diff(self, file_path: str, timestamp: Optional[str] = None, working_dir: str = None):
        """Generate git diff for a specific file operation.
        
        WHY: This method generates a git diff showing the changes made to a file
        during a specific write operation. It uses git log and show commands to
        find the most relevant commit around the specified timestamp.
        
        Args:
            file_path: Path to the file relative to the git repository
            timestamp: ISO timestamp of the file operation (optional)
            working_dir: Working directory containing the git repository
            
        Returns:
            dict: Contains diff content, metadata, and status information
        """
        try:
            # If file_path is absolute, determine its git repository
            if os.path.isabs(file_path):
                # Find the directory containing the file
                file_dir = os.path.dirname(file_path)
                if os.path.exists(file_dir):
                    # Try to find the git root from the file's directory
                    current_dir = file_dir
                    while current_dir != "/" and current_dir:
                        if os.path.exists(os.path.join(current_dir, ".git")):
                            working_dir = current_dir
                            self.logger.info(f"Found git repository at: {working_dir}")
                            break
                        current_dir = os.path.dirname(current_dir)
                    else:
                        # If no git repo found, use the file's directory
                        working_dir = file_dir
                        self.logger.info(f"No git repo found, using file's directory: {working_dir}")
            
            # Handle case where working_dir is None, empty string, or 'Unknown'
            original_working_dir = working_dir
            if not working_dir or working_dir == 'Unknown' or working_dir.strip() == '':
                working_dir = os.getcwd()
                self.logger.info(f"[GIT-DIFF-DEBUG] working_dir was invalid ({repr(original_working_dir)}), using cwd: {working_dir}")
            else:
                self.logger.info(f"[GIT-DIFF-DEBUG] Using provided working_dir: {working_dir}")
                
            # For read-only git operations, we can work from any directory
            # by passing the -C flag to git commands instead of changing directories
            original_cwd = os.getcwd()
            try:
                # We'll use git -C <working_dir> for all commands instead of chdir
                
                # Check if this is a git repository
                git_check = await asyncio.create_subprocess_exec(
                    'git', '-C', working_dir, 'rev-parse', '--git-dir',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await git_check.communicate()
                
                if git_check.returncode != 0:
                    return {
                        "success": False,
                        "error": "Not a git repository",
                        "file_path": file_path,
                        "working_dir": working_dir
                    }
                
                # Get the absolute path of the file relative to git root
                git_root_proc = await asyncio.create_subprocess_exec(
                    'git', '-C', working_dir, 'rev-parse', '--show-toplevel',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                git_root_output, _ = await git_root_proc.communicate()
                
                if git_root_proc.returncode != 0:
                    return {"success": False, "error": "Failed to determine git root directory"}
                
                git_root = git_root_output.decode().strip()
                
                # Make file_path relative to git root if it's absolute
                if os.path.isabs(file_path):
                    try:
                        file_path = os.path.relpath(file_path, git_root)
                    except ValueError:
                        # File is not under git root
                        pass
                
                # If timestamp is provided, try to find commits around that time
                if timestamp:
                    # Convert timestamp to git format
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        git_since = dt.strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Find commits that modified this file around the timestamp
                        log_proc = await asyncio.create_subprocess_exec(
                            'git', '-C', working_dir, 'log', '--oneline', '--since', git_since, 
                            '--until', f'{git_since} +1 hour', '--', file_path,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        log_output, _ = await log_proc.communicate()
                        
                        if log_proc.returncode == 0 and log_output:
                            # Get the most recent commit hash
                            commits = log_output.decode().strip().split('\n')
                            if commits and commits[0]:
                                commit_hash = commits[0].split()[0]
                                
                                # Get the diff for this specific commit
                                diff_proc = await asyncio.create_subprocess_exec(
                                    'git', '-C', working_dir, 'show', '--format=fuller', commit_hash, '--', file_path,
                                    stdout=asyncio.subprocess.PIPE,
                                    stderr=asyncio.subprocess.PIPE
                                )
                                diff_output, diff_error = await diff_proc.communicate()
                                
                                if diff_proc.returncode == 0:
                                    return {
                                        "success": True,
                                        "diff": diff_output.decode(),
                                        "commit_hash": commit_hash,
                                        "file_path": file_path,
                                        "method": "timestamp_based",
                                        "timestamp": timestamp
                                    }
                    except Exception as e:
                        self.logger.warning(f"Failed to parse timestamp or find commits: {e}")
                
                # Fallback: Get the most recent change to the file
                log_proc = await asyncio.create_subprocess_exec(
                    'git', '-C', working_dir, 'log', '-1', '--oneline', '--', file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                log_output, _ = await log_proc.communicate()
                
                if log_proc.returncode == 0 and log_output:
                    commit_hash = log_output.decode().strip().split()[0]
                    
                    # Get the diff for the most recent commit
                    diff_proc = await asyncio.create_subprocess_exec(
                        'git', '-C', working_dir, 'show', '--format=fuller', commit_hash, '--', file_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    diff_output, diff_error = await diff_proc.communicate()
                    
                    if diff_proc.returncode == 0:
                        return {
                            "success": True,
                            "diff": diff_output.decode(),
                            "commit_hash": commit_hash,
                            "file_path": file_path,
                            "method": "latest_commit",
                            "timestamp": timestamp
                        }
                
                # Try to show unstaged changes first
                diff_proc = await asyncio.create_subprocess_exec(
                    'git', '-C', working_dir, 'diff', '--', file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                diff_output, _ = await diff_proc.communicate()
                
                if diff_proc.returncode == 0 and diff_output.decode().strip():
                    return {
                        "success": True,
                        "diff": diff_output.decode(),
                        "commit_hash": "unstaged_changes",
                        "file_path": file_path,
                        "method": "unstaged_changes",
                        "timestamp": timestamp
                    }
                
                # Then try staged changes
                diff_proc = await asyncio.create_subprocess_exec(
                    'git', '-C', working_dir, 'diff', '--cached', '--', file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                diff_output, _ = await diff_proc.communicate()
                
                if diff_proc.returncode == 0 and diff_output.decode().strip():
                    return {
                        "success": True,
                        "diff": diff_output.decode(),
                        "commit_hash": "staged_changes",
                        "file_path": file_path,
                        "method": "staged_changes",
                        "timestamp": timestamp
                    }
                
                # Final fallback: Show changes against HEAD
                diff_proc = await asyncio.create_subprocess_exec(
                    'git', '-C', working_dir, 'diff', 'HEAD', '--', file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                diff_output, _ = await diff_proc.communicate()
                
                if diff_proc.returncode == 0:
                    working_diff = diff_output.decode()
                    if working_diff.strip():
                        return {
                            "success": True,
                            "diff": working_diff,
                            "commit_hash": "working_directory",
                            "file_path": file_path,
                            "method": "working_directory",
                            "timestamp": timestamp
                        }
                
                # Check if file is tracked by git
                status_proc = await asyncio.create_subprocess_exec(
                    'git', '-C', working_dir, 'ls-files', '--', file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                status_output, _ = await status_proc.communicate()
                
                is_tracked = status_proc.returncode == 0 and status_output.decode().strip()
                
                if not is_tracked:
                    # File is not tracked by git
                    return {
                        "success": False,
                        "error": "This file is not tracked by git",
                        "file_path": file_path,
                        "working_dir": working_dir,
                        "suggestions": [
                            "This file has not been added to git yet",
                            "Use 'git add' to track this file before viewing its diff",
                            "Git diff can only show changes for files that are tracked by git"
                        ]
                    }
                
                # File is tracked but has no changes to show
                suggestions = [
                    "The file may not have any committed changes yet",
                    "The file may have been added but not committed",
                    "The timestamp may be outside the git history range"
                ]
                
                if os.path.isabs(file_path) and not file_path.startswith(os.getcwd()):
                    current_repo = os.path.basename(os.getcwd())
                    file_repo = "unknown"
                    # Try to extract repository name from path
                    path_parts = file_path.split("/")
                    if "Projects" in path_parts:
                        idx = path_parts.index("Projects")
                        if idx + 1 < len(path_parts):
                            file_repo = path_parts[idx + 1]
                    
                    suggestions.clear()
                    suggestions.append(f"This file is from the '{file_repo}' repository")
                    suggestions.append(f"The git diff viewer is running from the '{current_repo}' repository")
                    suggestions.append("Git diff can only show changes for files in the current repository")
                    suggestions.append("To view changes for this file, run the monitoring dashboard from its repository")
                
                return {
                    "success": False,
                    "error": "No git history found for this file",
                    "file_path": file_path,
                    "suggestions": suggestions
                }
                
            finally:
                os.chdir(original_cwd)
                
        except Exception as e:
            self.logger.error(f"Error in _generate_git_diff: {e}")
            return {
                "success": False,
                "error": f"Git diff generation failed: {str(e)}",
                "file_path": file_path
            }
        
            
    def _register_events(self):
        """Register Socket.IO event handlers."""
        
        @self.sio.event
        async def connect(sid, environ, *args):
            """Handle client connection."""
            self.clients.add(sid)
            client_addr = environ.get('REMOTE_ADDR', 'unknown') 
            user_agent = environ.get('HTTP_USER_AGENT', 'unknown')
            self.logger.info(f"🔗 NEW CLIENT CONNECTED: {sid} from {client_addr}")
            self.logger.info(f"📱 User Agent: {user_agent[:100]}...")
            self.logger.info(f"📈 Total clients now: {len(self.clients)}")
            
            # Send initial status immediately with enhanced data
            status_data = {
                "server": "claude-mpm-python-socketio",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "clients_connected": len(self.clients),
                "session_id": self.session_id,
                "claude_status": self.claude_status,
                "claude_pid": self.claude_pid,
                "server_version": "2.0.0",
                "client_id": sid
            }
            
            try:
                await self.sio.emit('status', status_data, room=sid)
                await self.sio.emit('welcome', {
                    "message": "Connected to Claude MPM Socket.IO server",
                    "client_id": sid,
                    "server_time": datetime.utcnow().isoformat() + "Z"
                }, room=sid)
                
                # Automatically send the last 50 events to new clients
                await self._send_event_history(sid, limit=50)
                
                self.logger.debug(f"✅ Sent welcome messages and event history to client {sid}")
            except Exception as e:
                self.logger.error(f"❌ Failed to send welcome to client {sid}: {e}")
                import traceback
                self.logger.error(f"Full traceback: {traceback.format_exc()}")
            
        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection."""
            if sid in self.clients:
                self.clients.remove(sid)
                self.logger.info(f"🔌 CLIENT DISCONNECTED: {sid}")
                self.logger.info(f"📉 Total clients now: {len(self.clients)}")
            else:
                self.logger.warning(f"⚠️  Attempted to disconnect unknown client: {sid}")
            
        @self.sio.event
        async def get_status(sid):
            """Handle status request."""
            # Send compatible status event (not claude_event)
            status_data = {
                "server": "claude-mpm-python-socketio",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "clients_connected": len(self.clients),
                "session_id": self.session_id,
                "claude_status": self.claude_status,
                "claude_pid": self.claude_pid
            }
            await self.sio.emit('status', status_data, room=sid)
            self.logger.debug(f"Sent status response to client {sid}")
            
        @self.sio.event
        async def get_history(sid, data=None):
            """Handle history request."""
            params = data or {}
            event_types = params.get("event_types", [])
            limit = min(params.get("limit", 100), len(self.event_history))
            
            await self._send_event_history(sid, event_types=event_types, limit=limit)
            
        @self.sio.event
        async def request_history(sid, data=None):
            """Handle legacy history request (for client compatibility)."""
            # This handles the 'request.history' event that the client currently emits
            params = data or {}
            event_types = params.get("event_types", [])
            limit = min(params.get("limit", 50), len(self.event_history))
            
            await self._send_event_history(sid, event_types=event_types, limit=limit)
            
        @self.sio.event
        async def subscribe(sid, data=None):
            """Handle subscription request."""
            channels = data.get("channels", ["*"]) if data else ["*"]
            await self.sio.emit('subscribed', {
                "channels": channels
            }, room=sid)
            
        @self.sio.event
        async def claude_event(sid, data):
            """Handle events from client proxies."""
            # Store in history
            self.event_history.append(data)
            self.logger.debug(f"📚 Event from client stored in history (total: {len(self.event_history)})")
            
            # Re-broadcast to all other clients
            await self.sio.emit('claude_event', data, skip_sid=sid)
        
        @self.sio.event
        async def get_git_branch(sid, working_dir=None):
            """Get the current git branch for a directory"""
            import subprocess
            try:
                self.logger.info(f"[GIT-BRANCH-DEBUG] get_git_branch called with working_dir: {repr(working_dir)} (type: {type(working_dir)})")
                
                # Handle case where working_dir is None, empty string, or common invalid states
                original_working_dir = working_dir
                invalid_states = [
                    None, '', 'Unknown', 'Loading...', 'Loading', 'undefined', 'null', 
                    'Not Connected', 'Invalid Directory', 'No Directory'
                ]
                
                if working_dir in invalid_states or (isinstance(working_dir, str) and working_dir.strip() == ''):
                    working_dir = os.getcwd()
                    self.logger.info(f"[GIT-BRANCH-DEBUG] working_dir was invalid ({repr(original_working_dir)}), using cwd: {working_dir}")
                else:
                    self.logger.info(f"[GIT-BRANCH-DEBUG] Using provided working_dir: {working_dir}")
                    
                # Additional validation for obviously invalid paths
                if isinstance(working_dir, str):
                    working_dir = working_dir.strip()
                    # Check for null bytes or other invalid characters
                    if '\x00' in working_dir:
                        self.logger.warning(f"[GIT-BRANCH-DEBUG] working_dir contains null bytes, using cwd instead")
                        working_dir = os.getcwd()
                
                # Validate that the directory exists and is a valid path
                if not os.path.exists(working_dir):
                    self.logger.info(f"[GIT-BRANCH-DEBUG] Directory does not exist: {working_dir} - responding gracefully")
                    await self.sio.emit('git_branch_response', {
                        'success': False,
                        'error': f'Directory not found',
                        'working_dir': working_dir,
                        'original_working_dir': original_working_dir,
                        'detail': f'Path does not exist: {working_dir}'
                    }, room=sid)
                    return
                    
                if not os.path.isdir(working_dir):
                    self.logger.info(f"[GIT-BRANCH-DEBUG] Path is not a directory: {working_dir} - responding gracefully")
                    await self.sio.emit('git_branch_response', {
                        'success': False,
                        'error': f'Not a directory',
                        'working_dir': working_dir,
                        'original_working_dir': original_working_dir,
                        'detail': f'Path is not a directory: {working_dir}'
                    }, room=sid)
                    return
                
                self.logger.info(f"[GIT-BRANCH-DEBUG] Running git command in directory: {working_dir}")
                
                # Run git command to get current branch
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=working_dir,
                    capture_output=True,
                    text=True
                )
                
                self.logger.info(f"[GIT-BRANCH-DEBUG] Git command result: returncode={result.returncode}, stdout={repr(result.stdout)}, stderr={repr(result.stderr)}")
                
                if result.returncode == 0:
                    branch = result.stdout.strip()
                    self.logger.info(f"[GIT-BRANCH-DEBUG] Successfully got git branch: {branch}")
                    await self.sio.emit('git_branch_response', {
                        'success': True,
                        'branch': branch,
                        'working_dir': working_dir,
                        'original_working_dir': original_working_dir
                    }, room=sid)
                else:
                    self.logger.warning(f"[GIT-BRANCH-DEBUG] Git command failed: {result.stderr}")
                    await self.sio.emit('git_branch_response', {
                        'success': False,
                        'error': 'Not a git repository',
                        'working_dir': working_dir,
                        'original_working_dir': original_working_dir,
                        'git_error': result.stderr
                    }, room=sid)
                    
            except Exception as e:
                self.logger.error(f"[GIT-BRANCH-DEBUG] Exception in get_git_branch: {e}")
                import traceback
                self.logger.error(f"[GIT-BRANCH-DEBUG] Stack trace: {traceback.format_exc()}")
                await self.sio.emit('git_branch_response', {
                    'success': False,
                    'error': str(e),
                    'working_dir': working_dir,
                    'original_working_dir': original_working_dir
                }, room=sid)
        
        @self.sio.event
        async def check_file_tracked(sid, data):
            """Check if a file is tracked by git"""
            import subprocess
            try:
                file_path = data.get('file_path')
                working_dir = data.get('working_dir', os.getcwd())
                
                if not file_path:
                    await self.sio.emit('file_tracked_response', {
                        'success': False,
                        'error': 'file_path is required',
                        'file_path': file_path
                    }, room=sid)
                    return
                
                # Use git ls-files to check if file is tracked
                result = subprocess.run(
                    ["git", "-C", working_dir, "ls-files", "--", file_path],
                    capture_output=True,
                    text=True
                )
                
                is_tracked = result.returncode == 0 and result.stdout.strip()
                
                await self.sio.emit('file_tracked_response', {
                    'success': True,
                    'file_path': file_path,
                    'working_dir': working_dir,
                    'is_tracked': bool(is_tracked)
                }, room=sid)
                    
            except Exception as e:
                self.logger.error(f"Error checking file tracked status: {e}")
                await self.sio.emit('file_tracked_response', {
                    'success': False,
                    'error': str(e),
                    'file_path': data.get('file_path', 'unknown')
                }, room=sid)
        
        @self.sio.event
        async def read_file(sid, data):
            """Read file contents safely"""
            try:
                file_path = data.get('file_path')
                working_dir = data.get('working_dir', os.getcwd())
                max_size = data.get('max_size', 1024 * 1024)  # 1MB default limit
                
                if not file_path:
                    await self.sio.emit('file_content_response', {
                        'success': False,
                        'error': 'file_path is required',
                        'file_path': file_path
                    }, room=sid)
                    return
                
                # Use the shared file reading logic
                result = await self._read_file_safely(file_path, working_dir, max_size)
                
                # Send the result back to the client
                await self.sio.emit('file_content_response', result, room=sid)
                        
            except Exception as e:
                self.logger.error(f"Error reading file: {e}")
                await self.sio.emit('file_content_response', {
                    'success': False,
                    'error': str(e),
                    'file_path': data.get('file_path', 'unknown')
                }, room=sid)
        
        @self.sio.event
        async def check_git_status(sid, data):
            """Check git status for a file to determine if git diff icons should be shown"""
            import subprocess
            try:
                file_path = data.get('file_path')
                working_dir = data.get('working_dir', os.getcwd())
                
                self.logger.info(f"[GIT-STATUS-DEBUG] check_git_status called with file_path: {repr(file_path)}, working_dir: {repr(working_dir)}")
                
                if not file_path:
                    await self.sio.emit('git_status_response', {
                        'success': False,
                        'error': 'file_path is required',
                        'file_path': file_path
                    }, room=sid)
                    return
                
                # Validate and sanitize working_dir
                original_working_dir = working_dir
                if not working_dir or working_dir == 'Unknown' or working_dir.strip() == '' or working_dir == '.':
                    working_dir = os.getcwd()
                    self.logger.info(f"[GIT-STATUS-DEBUG] working_dir was invalid ({repr(original_working_dir)}), using cwd: {working_dir}")
                else:
                    self.logger.info(f"[GIT-STATUS-DEBUG] Using provided working_dir: {working_dir}")
                
                # Check if the working directory exists and is a directory
                if not os.path.exists(working_dir):
                    self.logger.warning(f"[GIT-STATUS-DEBUG] Directory does not exist: {working_dir}")
                    await self.sio.emit('git_status_response', {
                        'success': False,
                        'error': f'Directory does not exist: {working_dir}',
                        'file_path': file_path,
                        'working_dir': working_dir,
                        'original_working_dir': original_working_dir
                    }, room=sid)
                    return
                    
                if not os.path.isdir(working_dir):
                    self.logger.warning(f"[GIT-STATUS-DEBUG] Path is not a directory: {working_dir}")
                    await self.sio.emit('git_status_response', {
                        'success': False,
                        'error': f'Path is not a directory: {working_dir}',
                        'file_path': file_path,
                        'working_dir': working_dir,
                        'original_working_dir': original_working_dir
                    }, room=sid)
                    return
                
                # Check if this is a git repository
                self.logger.info(f"[GIT-STATUS-DEBUG] Checking if {working_dir} is a git repository")
                git_check = subprocess.run(
                    ["git", "-C", working_dir, "rev-parse", "--git-dir"],
                    capture_output=True,
                    text=True
                )
                
                if git_check.returncode != 0:
                    self.logger.info(f"[GIT-STATUS-DEBUG] Not a git repository: {working_dir}")
                    await self.sio.emit('git_status_response', {
                        'success': False,
                        'error': 'Not a git repository',
                        'file_path': file_path,
                        'working_dir': working_dir,
                        'original_working_dir': original_working_dir
                    }, room=sid)
                    return
                
                # Determine if the file path should be made relative to git root
                file_path_for_git = file_path
                if os.path.isabs(file_path):
                    # Get git root to make path relative if needed
                    git_root_result = subprocess.run(
                        ["git", "-C", working_dir, "rev-parse", "--show-toplevel"],
                        capture_output=True,
                        text=True
                    )
                    
                    if git_root_result.returncode == 0:
                        git_root = git_root_result.stdout.strip()
                        try:
                            file_path_for_git = os.path.relpath(file_path, git_root)
                            self.logger.info(f"[GIT-STATUS-DEBUG] Made file path relative to git root: {file_path_for_git}")
                        except ValueError:
                            # File is not under git root - keep original path
                            self.logger.info(f"[GIT-STATUS-DEBUG] File not under git root, keeping original path: {file_path}")
                            pass
                
                # Check if the file exists
                full_path = file_path if os.path.isabs(file_path) else os.path.join(working_dir, file_path)
                if not os.path.exists(full_path):
                    self.logger.warning(f"[GIT-STATUS-DEBUG] File does not exist: {full_path}")
                    await self.sio.emit('git_status_response', {
                        'success': False,
                        'error': f'File does not exist: {file_path}',
                        'file_path': file_path,
                        'working_dir': working_dir,
                        'original_working_dir': original_working_dir
                    }, room=sid)
                    return
                
                # Check git status for the file - this succeeds if git knows about the file
                # (either tracked, modified, staged, etc.)
                self.logger.info(f"[GIT-STATUS-DEBUG] Checking git status for file: {file_path_for_git}")
                git_status_result = subprocess.run(
                    ["git", "-C", working_dir, "status", "--porcelain", file_path_for_git],
                    capture_output=True,
                    text=True
                )
                
                self.logger.info(f"[GIT-STATUS-DEBUG] Git status result: returncode={git_status_result.returncode}, stdout={repr(git_status_result.stdout)}, stderr={repr(git_status_result.stderr)}")
                
                # Also check if file is tracked by git (alternative approach)
                ls_files_result = subprocess.run(
                    ["git", "-C", working_dir, "ls-files", file_path_for_git],
                    capture_output=True,
                    text=True
                )
                
                is_tracked = ls_files_result.returncode == 0 and ls_files_result.stdout.strip()
                has_status = git_status_result.returncode == 0
                
                self.logger.info(f"[GIT-STATUS-DEBUG] File tracking status: is_tracked={is_tracked}, has_status={has_status}")
                
                # Success if git knows about the file (either tracked or has status changes)
                if is_tracked or has_status:
                    self.logger.info(f"[GIT-STATUS-DEBUG] Git status check successful for {file_path}")
                    await self.sio.emit('git_status_response', {
                        'success': True,
                        'file_path': file_path,
                        'working_dir': working_dir,
                        'original_working_dir': original_working_dir,
                        'is_tracked': is_tracked,
                        'has_changes': bool(git_status_result.stdout.strip()) if has_status else False
                    }, room=sid)
                else:
                    self.logger.info(f"[GIT-STATUS-DEBUG] File {file_path} is not tracked by git")
                    await self.sio.emit('git_status_response', {
                        'success': False,
                        'error': 'File is not tracked by git',
                        'file_path': file_path,
                        'working_dir': working_dir,
                        'original_working_dir': original_working_dir,
                        'is_tracked': False
                    }, room=sid)
                    
            except Exception as e:
                self.logger.error(f"[GIT-STATUS-DEBUG] Exception in check_git_status: {e}")
                import traceback
                self.logger.error(f"[GIT-STATUS-DEBUG] Stack trace: {traceback.format_exc()}")
                await self.sio.emit('git_status_response', {
                    'success': False,
                    'error': str(e),
                    'file_path': data.get('file_path', 'unknown'),
                    'working_dir': data.get('working_dir', 'unknown')
                }, room=sid)

        @self.sio.event
        async def git_add_file(sid, data):
            """Add file to git tracking"""
            import subprocess
            try:
                file_path = data.get('file_path')
                working_dir = data.get('working_dir', os.getcwd())
                
                self.logger.info(f"[GIT-ADD-DEBUG] git_add_file called with file_path: {repr(file_path)}, working_dir: {repr(working_dir)} (type: {type(working_dir)})")
                
                if not file_path:
                    await self.sio.emit('git_add_response', {
                        'success': False,
                        'error': 'file_path is required',
                        'file_path': file_path
                    }, room=sid)
                    return
                
                # Validate and sanitize working_dir
                original_working_dir = working_dir
                if not working_dir or working_dir == 'Unknown' or working_dir.strip() == '' or working_dir == '.':
                    working_dir = os.getcwd()
                    self.logger.info(f"[GIT-ADD-DEBUG] working_dir was invalid ({repr(original_working_dir)}), using cwd: {working_dir}")
                else:
                    self.logger.info(f"[GIT-ADD-DEBUG] Using provided working_dir: {working_dir}")
                
                # Validate that the directory exists and is a valid path
                if not os.path.exists(working_dir):
                    self.logger.warning(f"[GIT-ADD-DEBUG] Directory does not exist: {working_dir}")
                    await self.sio.emit('git_add_response', {
                        'success': False,
                        'error': f'Directory does not exist: {working_dir}',
                        'file_path': file_path,
                        'working_dir': working_dir,
                        'original_working_dir': original_working_dir
                    }, room=sid)
                    return
                    
                if not os.path.isdir(working_dir):
                    self.logger.warning(f"[GIT-ADD-DEBUG] Path is not a directory: {working_dir}")
                    await self.sio.emit('git_add_response', {
                        'success': False,
                        'error': f'Path is not a directory: {working_dir}',
                        'file_path': file_path,
                        'working_dir': working_dir,
                        'original_working_dir': original_working_dir
                    }, room=sid)
                    return
                
                self.logger.info(f"[GIT-ADD-DEBUG] Running git add command in directory: {working_dir}")
                
                # Use git add to track the file
                result = subprocess.run(
                    ["git", "-C", working_dir, "add", file_path],
                    capture_output=True,
                    text=True
                )
                
                self.logger.info(f"[GIT-ADD-DEBUG] Git add result: returncode={result.returncode}, stdout={repr(result.stdout)}, stderr={repr(result.stderr)}")
                
                if result.returncode == 0:
                    self.logger.info(f"[GIT-ADD-DEBUG] Successfully added {file_path} to git in {working_dir}")
                    await self.sio.emit('git_add_response', {
                        'success': True,
                        'file_path': file_path,
                        'working_dir': working_dir,
                        'original_working_dir': original_working_dir,
                        'message': 'File successfully added to git tracking'
                    }, room=sid)
                else:
                    error_message = result.stderr.strip() or 'Unknown git error'
                    self.logger.warning(f"[GIT-ADD-DEBUG] Git add failed: {error_message}")
                    await self.sio.emit('git_add_response', {
                        'success': False,
                        'error': f'Git add failed: {error_message}',
                        'file_path': file_path,
                        'working_dir': working_dir,
                        'original_working_dir': original_working_dir
                    }, room=sid)
                    
            except Exception as e:
                self.logger.error(f"[GIT-ADD-DEBUG] Exception in git_add_file: {e}")
                import traceback
                self.logger.error(f"[GIT-ADD-DEBUG] Stack trace: {traceback.format_exc()}")
                await self.sio.emit('git_add_response', {
                    'success': False,
                    'error': str(e),
                    'file_path': data.get('file_path', 'unknown'),
                    'working_dir': data.get('working_dir', 'unknown')
                }, room=sid)
            
    async def _send_current_status(self, sid: str):
        """Send current system status to a client."""
        try:
            status = {
                "type": "system.status",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": {
                    "session_id": self.session_id,
                    "session_start": self.session_start,
                    "claude_status": self.claude_status,
                    "claude_pid": self.claude_pid,
                    "connected_clients": len(self.clients),
                    "websocket_port": self.port,
                    "instance_info": {
                        "port": self.port,
                        "host": self.host,
                        "working_dir": os.getcwd() if self.session_id else None
                    }
                }
            }
            await self.sio.emit('claude_event', status, room=sid)
            self.logger.debug("Sent status to client")
        except Exception as e:
            self.logger.error(f"Failed to send status to client: {e}")
            raise
            
    async def _send_event_history(self, sid: str, event_types: list = None, limit: int = 50):
        """Send event history to a specific client.
        
        WHY: When clients connect to the dashboard, they need context from recent events
        to understand what's been happening. This sends the most recent events in
        chronological order (oldest first) so the dashboard displays them properly.
        
        Args:
            sid: Socket.IO session ID of the client
            event_types: Optional list of event types to filter by
            limit: Maximum number of events to send (default: 50)
        """
        try:
            if not self.event_history:
                self.logger.debug(f"No event history to send to client {sid}")
                return
                
            # Limit to reasonable number to avoid overwhelming client
            limit = min(limit, 100)
            
            # Get the most recent events, filtered by type if specified
            history = []
            for event in reversed(self.event_history):
                if not event_types or event.get("type") in event_types:
                    history.append(event)
                    if len(history) >= limit:
                        break
            
            # Reverse to get chronological order (oldest first)
            history = list(reversed(history))
            
            if history:
                # Send as 'history' event that the client expects
                await self.sio.emit('history', {
                    "events": history,
                    "count": len(history),
                    "total_available": len(self.event_history)
                }, room=sid)
                
                self.logger.info(f"📚 Sent {len(history)} historical events to client {sid}")
            else:
                self.logger.debug(f"No matching events found for client {sid} with filters: {event_types}")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to send event history to client {sid}: {e}")
            import traceback
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            
    def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """Broadcast an event to all connected clients."""
        if not SOCKETIO_AVAILABLE:
            self.logger.debug(f"⚠️  Socket.IO broadcast skipped - packages not available")
            return
            
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": data
        }
        
        self.logger.info(f"📤 BROADCASTING EVENT: {event_type}")
        self.logger.debug(f"📄 Event data: {json.dumps(data, indent=2)[:200]}...")
        
        # Store in history
        self.event_history.append(event)
        self.logger.debug(f"📚 Event stored in history (total: {len(self.event_history)})")
        
        # Check if we have clients and event loop
        if not self.clients:
            self.logger.warning(f"⚠️  No Socket.IO clients connected - event will not be delivered")
            return
            
        if not self.loop or not self.sio:
            self.logger.error(f"❌ No event loop or Socket.IO instance available - cannot broadcast event")
            return
            
        self.logger.info(f"🎯 Broadcasting to {len(self.clients)} clients via event loop")
        
        # Broadcast to clients with timeout and error handling
        try:
            # Check if the event loop is still running and not closed
            if self.loop and not self.loop.is_closed() and self.loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self.sio.emit('claude_event', event),
                    self.loop
                )
                # Wait for completion with timeout to detect issues
                try:
                    future.result(timeout=2.0)  # 2 second timeout
                    self.logger.debug(f"📨 Successfully broadcasted {event_type} to {len(self.clients)} clients")
                except asyncio.TimeoutError:
                    self.logger.warning(f"⏰ Broadcast timeout for event {event_type} - continuing anyway")
                except Exception as emit_error:
                    self.logger.error(f"❌ Broadcast emit error for {event_type}: {emit_error}")
            else:
                self.logger.warning(f"⚠️ Event loop not available for broadcast of {event_type} - event loop closed or not running")
        except Exception as e:
            self.logger.error(f"❌ Failed to submit broadcast to event loop: {e}")
            import traceback
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            
    # Convenience methods for common events (same interface as WebSocketServer)
    
    def session_started(self, session_id: str, launch_method: str, working_dir: str):
        """Notify that a session has started."""
        self.session_id = session_id
        self.session_start = datetime.utcnow().isoformat() + "Z"
        self.broadcast_event("session.start", {
            "session_id": session_id,
            "start_time": self.session_start,
            "launch_method": launch_method,
            "working_directory": working_dir,
            "websocket_port": self.port,
            "instance_info": {
                "port": self.port,
                "host": self.host,
                "working_dir": working_dir
            }
        })
        
    def session_ended(self):
        """Notify that a session has ended."""
        if self.session_id:
            duration = None
            if self.session_start:
                start = datetime.fromisoformat(self.session_start.replace("Z", "+00:00"))
                duration = (datetime.utcnow() - start.replace(tzinfo=None)).total_seconds()
                
            self.broadcast_event("session.end", {
                "session_id": self.session_id,
                "end_time": datetime.utcnow().isoformat() + "Z",
                "duration_seconds": duration
            })
            
        self.session_id = None
        self.session_start = None
        
    def claude_status_changed(self, status: str, pid: Optional[int] = None, message: str = ""):
        """Notify Claude status change."""
        self.claude_status = status
        self.claude_pid = pid
        self.broadcast_event("claude.status", {
            "status": status,
            "pid": pid,
            "message": message
        })
        
    def claude_output(self, content: str, stream: str = "stdout"):
        """Broadcast Claude output."""
        self.broadcast_event("claude.output", {
            "content": content,
            "stream": stream
        })
        
    def agent_delegated(self, agent: str, task: str, status: str = "started"):
        """Notify agent delegation."""
        self.broadcast_event("agent.delegation", {
            "agent": agent,
            "task": task,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    def todo_updated(self, todos: List[Dict[str, Any]]):
        """Notify todo list update."""
        stats = {
            "total": len(todos),
            "completed": sum(1 for t in todos if t.get("status") == "completed"),
            "in_progress": sum(1 for t in todos if t.get("status") == "in_progress"),
            "pending": sum(1 for t in todos if t.get("status") == "pending")
        }
        
        self.broadcast_event("todo.update", {
            "todos": todos,
            "stats": stats
        })
        
    def ticket_created(self, ticket_id: str, title: str, priority: str = "medium"):
        """Notify ticket creation."""
        self.broadcast_event("ticket.created", {
            "id": ticket_id,
            "title": title,
            "priority": priority,
            "created_at": datetime.utcnow().isoformat() + "Z"
        })
        
    def memory_loaded(self, agent_id: str, memory_size: int, sections_count: int):
        """Notify when agent memory is loaded from file."""
        self.broadcast_event("memory:loaded", {
            "agent_id": agent_id,
            "memory_size": memory_size,
            "sections_count": sections_count,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    def memory_created(self, agent_id: str, template_type: str):
        """Notify when new agent memory is created from template."""
        self.broadcast_event("memory:created", {
            "agent_id": agent_id,
            "template_type": template_type,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    def memory_updated(self, agent_id: str, learning_type: str, content: str, section: str):
        """Notify when learning is added to agent memory."""
        self.broadcast_event("memory:updated", {
            "agent_id": agent_id,
            "learning_type": learning_type,
            "content": content,
            "section": section,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    def memory_injected(self, agent_id: str, context_size: int):
        """Notify when agent memory is injected into context."""
        self.broadcast_event("memory:injected", {
            "agent_id": agent_id,
            "context_size": context_size,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })


# Global instance for easy access
_socketio_server: Optional[SocketIOServer] = None


def get_socketio_server() -> SocketIOServer:
    """Get or create the global Socket.IO server instance.
    
    WHY: In exec mode, a persistent Socket.IO server may already be running
    in a separate process. We need to detect this and create a client proxy
    instead of trying to start another server.
    """
    global _socketio_server
    if _socketio_server is None:
        # Check if a Socket.IO server is already running on the default port
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                result = s.connect_ex(('127.0.0.1', 8765))
                if result == 0:
                    # Server is already running - create a client proxy
                    _socketio_server = SocketIOClientProxy(port=8765)
                else:
                    # No server running - create a real server
                    _socketio_server = SocketIOServer()
        except Exception:
            # On any error, create a real server
            _socketio_server = SocketIOServer()
        
    return _socketio_server


def start_socketio_server():
    """Start the global Socket.IO server."""
    server = get_socketio_server()
    server.start()
    return server


def stop_socketio_server():
    """Stop the global Socket.IO server."""
    global _socketio_server
    if _socketio_server:
        _socketio_server.stop()
        _socketio_server = None
