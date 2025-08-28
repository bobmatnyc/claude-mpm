"""
Code Analysis Event Handler for Socket.IO
==========================================

WHY: Handles code analysis requests from the dashboard, managing the analysis
runner subprocess and streaming results back to connected clients.

DESIGN DECISIONS:
- Single analysis runner instance per server
- Queue multiple requests for sequential processing
- Support cancellation of running analysis
- Stream events in real-time to all connected clients
"""

import asyncio
import uuid
from pathlib import Path
from typing import Any, Dict

from ....core.logging_config import get_logger
from ....dashboard.analysis_runner import CodeAnalysisRunner
from ....tools.code_tree_analyzer import CodeTreeAnalyzer
from ....tools.code_tree_events import CodeTreeEventEmitter
from .base import BaseEventHandler


class CodeAnalysisEventHandler(BaseEventHandler):
    """Handles code analysis events from dashboard clients.

    WHY: Provides a clean interface between the dashboard UI and the
    code analysis subprocess, managing requests and responses.
    """

    def __init__(self, server):
        """Initialize the code analysis event handler.

        Args:
            server: The SocketIOServer instance
        """
        super().__init__(server)
        self.logger = get_logger(__name__)
        self.analysis_runner = None
        self.code_analyzer = None  # For lazy loading operations

    def initialize(self):
        """Initialize the analysis runner."""
        if not self.analysis_runner:
            self.analysis_runner = CodeAnalysisRunner(self.server)
            self.analysis_runner.start()
            self.logger.info("Code analysis runner initialized")

    def cleanup(self):
        """Cleanup the analysis runner on shutdown."""
        if self.analysis_runner:
            self.analysis_runner.stop()
            self.analysis_runner = None
            self.logger.info("Code analysis runner stopped")

    def get_events(self) -> Dict[str, Any]:
        """Get the events this handler manages.

        Returns:
            Dictionary mapping event names to handler methods
        """
        return {
            # Legacy full analysis
            "code:analyze:request": self.handle_analyze_request,
            "code:analyze:cancel": self.handle_cancel_request,
            "code:analyze:status": self.handle_status_request,
            # Lazy loading operations
            "code:discover:top_level": self.handle_discover_top_level,
            "code:discover:directory": self.handle_discover_directory,
            "code:analyze:file": self.handle_analyze_file,
        }

    def register_events(self) -> None:
        """Register Socket.IO event handlers.

        WHY: Required by BaseEventHandler to register events with the Socket.IO server.
        """
        events = self.get_events()
        for event_name, handler_method in events.items():
            self.server.core.sio.on(event_name, handler_method)
            self.logger.info(f"Registered event handler: {event_name}")

    async def handle_analyze_request(self, sid: str, data: Dict[str, Any]):
        """Handle code analysis request from client.

        Args:
            sid: Socket ID of the requesting client
            data: Request data containing path and options
        """
        self.logger.info(f"Code analysis requested from {sid}: {data}")

        # Initialize runner if needed
        if not self.analysis_runner:
            self.initialize()

        # Validate request
        path = data.get("path")
        if not path:
            await self.server.sio.emit(
                "code:analysis:error",
                {
                    "message": "Path is required for analysis",
                    "request_id": data.get("request_id"),
                },
                room=sid,
            )
            return

        # Generate request ID if not provided
        request_id = data.get("request_id") or str(uuid.uuid4())

        # Extract options
        languages = data.get("languages")
        max_depth = data.get("max_depth")
        ignore_patterns = data.get("ignore_patterns")

        # Queue analysis request
        success = self.analysis_runner.request_analysis(
            request_id=request_id,
            path=path,
            languages=languages,
            max_depth=max_depth,
            ignore_patterns=ignore_patterns,
        )

        if success:
            # Send acknowledgment to requesting client
            await self.server.sio.emit(
                "code:analysis:accepted",
                {
                    "request_id": request_id,
                    "path": path,
                    "message": "Analysis request queued",
                },
                room=sid,
            )
        else:
            # Send error if request failed
            await self.server.sio.emit(
                "code:analysis:error",
                {
                    "request_id": request_id,
                    "message": "Failed to queue analysis request",
                },
                room=sid,
            )

    async def handle_cancel_request(self, sid: str, data: Dict[str, Any]):
        """Handle analysis cancellation request.

        Args:
            sid: Socket ID of the requesting client
            data: Request data (may contain request_id)
        """
        self.logger.info(f"Analysis cancellation requested from {sid}")

        # Cancel current analysis
        self.analysis_runner.cancel_current()

        # Send confirmation
        await self.server.sio.emit(
            "code:analysis:cancelled",
            {"message": "Analysis cancelled", "request_id": data.get("request_id")},
            room=sid,
        )

    async def handle_status_request(self, sid: str, data: Dict[str, Any]):
        """Handle status request from client.

        Args:
            sid: Socket ID of the requesting client
            data: Request data (unused)
        """
        status = self.analysis_runner.get_status()

        # Send status to requesting client
        await self.server.sio.emit("code:analysis:status", status, room=sid)

    async def handle_discover_top_level(self, sid: str, data: Dict[str, Any]):
        """Handle top-level directory discovery request for lazy loading.

        Args:
            sid: Socket ID of the requesting client
            data: Request data containing path and options
        """
        self.logger.info(f"Top-level discovery requested from {sid}: {data}")

        # Get path - this MUST be an absolute path from the frontend
        path = data.get("path")
        if not path:
            await self.server.core.sio.emit(
                "code:analysis:error",
                {
                    "error": "Path is required for top-level discovery",
                    "request_id": data.get("request_id"),
                },
                room=sid,
            )
            return

        # CRITICAL: Never use "." or allow relative paths
        # The frontend must send the absolute working directory
        if path in (".", "..", "/") or not Path(path).is_absolute():
            self.logger.warning(f"Invalid path for discovery: {path}")
            await self.server.core.sio.emit(
                "code:analysis:error",
                {
                    "error": f"Invalid path for discovery: {path}. Must be an absolute path.",
                    "request_id": data.get("request_id"),
                    "path": path,
                },
                room=sid,
            )
            return

        # ADDITIONAL SECURITY: Ensure path is within working directory bounds
        # This prevents access to system directories like /Users, /System, etc.
        working_dir = Path.cwd().absolute()
        try:
            requested_path = Path(path).absolute()
            # This will raise ValueError if path is not within working_dir
            requested_path.relative_to(working_dir)
        except ValueError:
            self.logger.warning(
                f"Access denied - path outside working directory: {path}"
            )
            await self.server.core.sio.emit(
                "code:analysis:error",
                {
                    "error": f"Access denied: Path outside working directory: {path}",
                    "request_id": data.get("request_id"),
                    "path": path,
                },
                room=sid,
            )
            return

        ignore_patterns = data.get("ignore_patterns", [])
        request_id = data.get("request_id")
        show_hidden_files = data.get("show_hidden_files", False)
        
        # Extensive debug logging
        self.logger.info(f"[DEBUG] handle_discover_top_level START")
        self.logger.info(f"[DEBUG] Received show_hidden_files={show_hidden_files} (type: {type(show_hidden_files)})")
        self.logger.info(f"[DEBUG] Current analyzer exists: {self.code_analyzer is not None}")
        if self.code_analyzer:
            current_value = getattr(self.code_analyzer, 'show_hidden_files', 'NOT_FOUND')
            self.logger.info(f"[DEBUG] Current analyzer show_hidden_files={current_value}")
        self.logger.info(f"[DEBUG] Full request data: {data}")

        try:
            # Create analyzer if needed or recreate if show_hidden_files changed
            current_show_hidden = getattr(self.code_analyzer, 'show_hidden_files', None) if self.code_analyzer else None
            need_recreate = (
                not self.code_analyzer or 
                current_show_hidden != show_hidden_files
            )
            
            self.logger.info(f"[DEBUG] Analyzer recreation check:")
            self.logger.info(f"[DEBUG]   - Analyzer exists: {self.code_analyzer is not None}")
            self.logger.info(f"[DEBUG]   - Current show_hidden: {current_show_hidden}")
            self.logger.info(f"[DEBUG]   - Requested show_hidden: {show_hidden_files}")
            self.logger.info(f"[DEBUG]   - Need recreate: {need_recreate}")
            
            if need_recreate:
                # Create a custom emitter that sends to Socket.IO
                emitter = CodeTreeEventEmitter(use_stdout=False)
                # Override emit method to send to Socket.IO
                original_emit = emitter.emit

                def socket_emit(
                    event_type: str, event_data: Dict[str, Any], batch: bool = False
                ):
                    # Keep the original event format with colons - frontend expects this!
                    # The frontend listens for 'code:directory:discovered' not 'code.directory.discovered'
                    
                    # Special handling for 'info' events - they should be passed through directly
                    if event_type == 'info':
                        # INFO events for granular tracking
                        loop = asyncio.get_event_loop()
                        loop.create_task(
                            self.server.core.sio.emit(
                                'info', {"request_id": request_id, **event_data}
                            )
                        )
                    else:
                        # Regular code analysis events
                        loop = asyncio.get_event_loop()
                        loop.create_task(
                            self.server.core.sio.emit(
                                event_type, {"request_id": request_id, **event_data}
                            )
                        )
                    # Call original for stats tracking
                    original_emit(event_type, event_data, batch)

                emitter.emit = socket_emit
                # Initialize CodeTreeAnalyzer with emitter keyword argument and show_hidden_files
                self.logger.info(f"[DEBUG] Creating new CodeTreeAnalyzer with show_hidden_files={show_hidden_files}")
                self.code_analyzer = CodeTreeAnalyzer(emitter=emitter, show_hidden_files=show_hidden_files)
                self.logger.info(f"[DEBUG] CodeTreeAnalyzer created:")
                self.logger.info(f"[DEBUG]   - analyzer.show_hidden_files={self.code_analyzer.show_hidden_files}")
                self.logger.info(f"[DEBUG]   - gitignore_manager.show_hidden_files={self.code_analyzer.gitignore_manager.show_hidden_files}")
            else:
                self.logger.info(f"[DEBUG] Reusing existing analyzer with show_hidden_files={self.code_analyzer.show_hidden_files}")

            # Use the provided path as-is - the frontend sends the absolute path
            # Make sure we're using an absolute path
            directory = Path(path)

            # Validate that the path exists and is a directory
            if not directory.exists():
                await self.server.core.sio.emit(
                    "code:analysis:error",
                    {
                        "request_id": request_id,
                        "path": path,
                        "error": f"Directory does not exist: {path}",
                    },
                    room=sid,
                )
                return

            if not directory.is_dir():
                await self.server.core.sio.emit(
                    "code:analysis:error",
                    {
                        "request_id": request_id,
                        "path": path,
                        "error": f"Path is not a directory: {path}",
                    },
                    room=sid,
                )
                return

            # Log what we're actually discovering
            self.logger.info(
                f"Discovering top-level contents of: {directory.absolute()}"
            )

            # Log before discovery
            self.logger.info(f"[DEBUG] About to discover with analyzer.show_hidden_files={self.code_analyzer.show_hidden_files}")
            
            result = self.code_analyzer.discover_top_level(directory, ignore_patterns)
            
            # Log what we got back
            num_items = len(result.get("children", []))
            dotfiles = [c for c in result.get("children", []) if c.get("name", "").startswith(".")]
            self.logger.info(f"[DEBUG] Discovery result: {num_items} items, {len(dotfiles)} dotfiles")
            if dotfiles:
                self.logger.info(f"[DEBUG] Dotfiles found: {[d.get('name') for d in dotfiles]}")

            # Send result to client with correct event name for top level discovery
            await self.server.core.sio.emit(
                "code:top_level:discovered",
                {
                    "request_id": request_id,
                    "path": str(directory),
                    "items": result.get("children", []),
                    "stats": {
                        "files": len(
                            [
                                c
                                for c in result.get("children", [])
                                if c.get("type") == "file"
                            ]
                        ),
                        "directories": len(
                            [
                                c
                                for c in result.get("children", [])
                                if c.get("type") == "directory"
                            ]
                        ),
                    },
                },
                room=sid,
            )

        except Exception as e:
            self.logger.error(f"Error discovering top level: {e}")
            await self.server.core.sio.emit(
                "code:analysis:error",
                {
                    "request_id": request_id,
                    "path": path,
                    "error": str(e),
                },
                room=sid,
            )

    async def handle_discover_directory(self, sid: str, data: Dict[str, Any]):
        """Handle directory discovery request for lazy loading.

        Args:
            sid: Socket ID of the requesting client
            data: Request data containing directory path
        """
        self.logger.info(f"Directory discovery requested from {sid}: {data}")

        path = data.get("path")
        ignore_patterns = data.get("ignore_patterns", [])
        request_id = data.get("request_id")
        show_hidden_files = data.get("show_hidden_files", False)

        if not path:
            await self.server.core.sio.emit(
                "code:analysis:error",
                {
                    "request_id": request_id,
                    "error": "Path is required",
                },
                room=sid,
            )
            return

        # CRITICAL SECURITY FIX: Add path validation to prevent filesystem traversal
        # The same validation logic as handle_discover_top_level
        if path in (".", "..", "/") or not Path(path).is_absolute():
            self.logger.warning(f"Invalid path for directory discovery: {path}")
            await self.server.core.sio.emit(
                "code:analysis:error",
                {
                    "error": f"Invalid path for discovery: {path}. Must be an absolute path.",
                    "request_id": request_id,
                    "path": path,
                },
                room=sid,
            )
            return

        # ADDITIONAL SECURITY: Ensure path is within working directory bounds
        # This prevents access to system directories like /Users, /System, etc.
        working_dir = Path.cwd().absolute()
        try:
            requested_path = Path(path).absolute()
            # This will raise ValueError if path is not within working_dir
            requested_path.relative_to(working_dir)
        except ValueError:
            self.logger.warning(
                f"Access denied - path outside working directory: {path}"
            )
            await self.server.core.sio.emit(
                "code:analysis:error",
                {
                    "error": f"Access denied: Path outside working directory: {path}",
                    "request_id": request_id,
                    "path": path,
                },
                room=sid,
            )
            return

        try:
            # Ensure analyzer exists or recreate if show_hidden_files changed
            current_show_hidden = getattr(self.code_analyzer, 'show_hidden_files', None) if self.code_analyzer else None
            need_recreate = (
                not self.code_analyzer or 
                current_show_hidden != show_hidden_files
            )
            
            self.logger.info(f"[DEBUG] Analyzer recreation check:")
            self.logger.info(f"[DEBUG]   - Analyzer exists: {self.code_analyzer is not None}")
            self.logger.info(f"[DEBUG]   - Current show_hidden: {current_show_hidden}")
            self.logger.info(f"[DEBUG]   - Requested show_hidden: {show_hidden_files}")
            self.logger.info(f"[DEBUG]   - Need recreate: {need_recreate}")
            
            if need_recreate:
                emitter = CodeTreeEventEmitter(use_stdout=False)
                # Override emit method to send to Socket.IO
                original_emit = emitter.emit

                def socket_emit(
                    event_type: str, event_data: Dict[str, Any], batch: bool = False
                ):
                    # Keep the original event format with colons - frontend expects this!
                    # The frontend listens for 'code:directory:discovered' not 'code.directory.discovered'
                    
                    # Special handling for 'info' events - they should be passed through directly
                    if event_type == 'info':
                        # INFO events for granular tracking
                        loop = asyncio.get_event_loop()
                        loop.create_task(
                            self.server.core.sio.emit(
                                'info', {"request_id": request_id, **event_data}
                            )
                        )
                    else:
                        # Regular code analysis events
                        loop = asyncio.get_event_loop()
                        loop.create_task(
                            self.server.core.sio.emit(
                                event_type, {"request_id": request_id, **event_data}
                            )
                        )
                    original_emit(event_type, event_data, batch)

                emitter.emit = socket_emit
                # Initialize CodeTreeAnalyzer with emitter keyword argument and show_hidden_files
                self.logger.info(f"[DEBUG] Creating new CodeTreeAnalyzer with show_hidden_files={show_hidden_files}")
                self.code_analyzer = CodeTreeAnalyzer(emitter=emitter, show_hidden_files=show_hidden_files)
                self.logger.info(f"[DEBUG] CodeTreeAnalyzer created, analyzer.show_hidden_files={self.code_analyzer.show_hidden_files}")
                self.logger.info(f"[DEBUG] GitignoreManager.show_hidden_files={self.code_analyzer.gitignore_manager.show_hidden_files}")
            else:
                self.logger.info(f"[DEBUG] Reusing analyzer with show_hidden_files={self.code_analyzer.show_hidden_files}")

            # Discover directory
            result = self.code_analyzer.discover_directory(path, ignore_patterns)

            # Send result with correct event name (using colons, not dots!)
            await self.server.core.sio.emit(
                "code:directory:discovered",
                {
                    "request_id": request_id,
                    "path": path,
                    **result,
                },
                room=sid,
            )

        except Exception as e:
            self.logger.error(f"Error discovering directory {path}: {e}")
            await self.server.core.sio.emit(
                "code:analysis:error",
                {
                    "request_id": request_id,
                    "path": path,
                    "error": str(e),
                },
                room=sid,
            )

    async def handle_analyze_file(self, sid: str, data: Dict[str, Any]):
        """Handle file analysis request for lazy loading.

        Args:
            sid: Socket ID of the requesting client
            data: Request data containing file path
        """
        self.logger.info(f"File analysis requested from {sid}: {data}")

        path = data.get("path")
        request_id = data.get("request_id")
        show_hidden_files = data.get("show_hidden_files", False)

        if not path:
            await self.server.core.sio.emit(
                "code:analysis:error",
                {
                    "request_id": request_id,
                    "error": "Path is required",
                },
                room=sid,
            )
            return

        # CRITICAL SECURITY FIX: Add path validation to prevent filesystem traversal
        if path in (".", "..", "/") or not Path(path).is_absolute():
            self.logger.warning(f"Invalid path for file analysis: {path}")
            await self.server.core.sio.emit(
                "code:analysis:error",
                {
                    "error": f"Invalid path for analysis: {path}. Must be an absolute path.",
                    "request_id": request_id,
                    "path": path,
                },
                room=sid,
            )
            return

        # ADDITIONAL SECURITY: Ensure file is within working directory bounds
        working_dir = Path.cwd().absolute()
        try:
            requested_path = Path(path).absolute()
            # This will raise ValueError if path is not within working_dir
            requested_path.relative_to(working_dir)
        except ValueError:
            self.logger.warning(
                f"Access denied - file outside working directory: {path}"
            )
            await self.server.core.sio.emit(
                "code:analysis:error",
                {
                    "error": f"Access denied: File outside working directory: {path}",
                    "request_id": request_id,
                    "path": path,
                },
                room=sid,
            )
            return

        try:
            # Ensure analyzer exists or recreate if show_hidden_files changed
            current_show_hidden = getattr(self.code_analyzer, 'show_hidden_files', None) if self.code_analyzer else None
            need_recreate = (
                not self.code_analyzer or 
                current_show_hidden != show_hidden_files
            )
            
            self.logger.info(f"[DEBUG] Analyzer recreation check:")
            self.logger.info(f"[DEBUG]   - Analyzer exists: {self.code_analyzer is not None}")
            self.logger.info(f"[DEBUG]   - Current show_hidden: {current_show_hidden}")
            self.logger.info(f"[DEBUG]   - Requested show_hidden: {show_hidden_files}")
            self.logger.info(f"[DEBUG]   - Need recreate: {need_recreate}")
            
            if need_recreate:
                emitter = CodeTreeEventEmitter(use_stdout=False)
                # Override emit method to send to Socket.IO
                original_emit = emitter.emit

                def socket_emit(
                    event_type: str, event_data: Dict[str, Any], batch: bool = False
                ):
                    # Keep the original event format with colons - frontend expects this!
                    # The frontend listens for 'code:file:analyzed' not 'code.file.analyzed'
                    
                    # Special handling for 'info' events - they should be passed through directly
                    if event_type == 'info':
                        # INFO events for granular tracking
                        loop = asyncio.get_event_loop()
                        loop.create_task(
                            self.server.core.sio.emit(
                                'info', {"request_id": request_id, **event_data}
                            )
                        )
                    else:
                        # Regular code analysis events
                        loop = asyncio.get_event_loop()
                        loop.create_task(
                            self.server.core.sio.emit(
                                event_type, {"request_id": request_id, **event_data}
                            )
                        )
                    original_emit(event_type, event_data, batch)

                emitter.emit = socket_emit
                # Initialize CodeTreeAnalyzer with emitter keyword argument and show_hidden_files
                self.logger.info(f"[DEBUG] Creating new CodeTreeAnalyzer with show_hidden_files={show_hidden_files}")
                self.code_analyzer = CodeTreeAnalyzer(emitter=emitter, show_hidden_files=show_hidden_files)
                self.logger.info(f"[DEBUG] CodeTreeAnalyzer created, analyzer.show_hidden_files={self.code_analyzer.show_hidden_files}")
                self.logger.info(f"[DEBUG] GitignoreManager.show_hidden_files={self.code_analyzer.gitignore_manager.show_hidden_files}")
            else:
                self.logger.info(f"[DEBUG] Reusing analyzer with show_hidden_files={self.code_analyzer.show_hidden_files}")

            # Analyze file
            result = self.code_analyzer.analyze_file(path)

            # Send result with correct event name (using colons, not dots!)
            await self.server.core.sio.emit(
                "code:file:analyzed",
                {
                    "request_id": request_id,
                    "path": path,
                    **result,
                },
                room=sid,
            )

        except Exception as e:
            self.logger.error(f"Error analyzing file {path}: {e}")
            await self.server.core.sio.emit(
                "code:analysis:error",
                {
                    "request_id": request_id,
                    "path": path,
                    "error": str(e),
                },
                room=sid,
            )
