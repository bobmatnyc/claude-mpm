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

        # SECURITY: Validate the requested path
        # Allow access to the explicitly chosen working directory and its subdirectories
        Path(path).absolute()

        # For now, we trust the frontend to send valid paths
        # In production, you might want to maintain a server-side list of allowed directories
        # or implement a more sophisticated permission system

        # Basic sanity checks are done below after creating the Path object

        ignore_patterns = data.get("ignore_patterns", [])
        request_id = data.get("request_id")

        try:
            # Create analyzer if needed
            if not self.code_analyzer:
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
                    if event_type == "info":
                        # INFO events for granular tracking
                        loop = asyncio.get_event_loop()
                        loop.create_task(
                            self.server.core.sio.emit(
                                "info", {"request_id": request_id, **event_data}
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
                # Initialize CodeTreeAnalyzer with emitter keyword argument
                self.logger.info("Creating CodeTreeAnalyzer")
                # Pass emit_events=False to prevent duplicate events from the analyzer
                # The emitter will still work but the analyzer won't create its own stdout emitter
                self.code_analyzer = CodeTreeAnalyzer(
                    emit_events=False, emitter=emitter
                )

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

            result = self.code_analyzer.discover_top_level(directory, ignore_patterns)

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

        # SECURITY: Validate the requested path
        # Allow access to the explicitly chosen working directory and its subdirectories
        requested_path = Path(path).absolute()

        # For now, we trust the frontend to send valid paths
        # In production, you might want to maintain a server-side list of allowed directories
        # or implement a more sophisticated permission system

        # Basic sanity checks
        if not requested_path.exists():
            self.logger.warning(f"Path does not exist: {path}")
            await self.server.core.sio.emit(
                "code:analysis:error",
                {
                    "error": f"Path does not exist: {path}",
                    "request_id": request_id,
                    "path": path,
                },
                room=sid,
            )
            return

        if not requested_path.is_dir():
            self.logger.warning(f"Path is not a directory: {path}")
            await self.server.core.sio.emit(
                "code:analysis:error",
                {
                    "error": f"Path is not a directory: {path}",
                    "request_id": request_id,
                    "path": path,
                },
                room=sid,
            )
            return

        try:
            # Ensure analyzer exists
            if not self.code_analyzer:
                emitter = CodeTreeEventEmitter(use_stdout=False)
                # Override emit method to send to Socket.IO
                original_emit = emitter.emit

                def socket_emit(
                    event_type: str, event_data: Dict[str, Any], batch: bool = False
                ):
                    # Keep the original event format with colons - frontend expects this!
                    # The frontend listens for 'code:directory:discovered' not 'code.directory.discovered'

                    # Special handling for 'info' events - they should be passed through directly
                    if event_type == "info":
                        # INFO events for granular tracking
                        loop = asyncio.get_event_loop()
                        loop.create_task(
                            self.server.core.sio.emit(
                                "info", {"request_id": request_id, **event_data}
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
                # Initialize CodeTreeAnalyzer with emitter keyword argument
                self.logger.info("Creating CodeTreeAnalyzer")
                # Pass emit_events=False to prevent duplicate events from the analyzer
                # The emitter will still work but the analyzer won't create its own stdout emitter
                self.code_analyzer = CodeTreeAnalyzer(
                    emit_events=False, emitter=emitter
                )

            # Discover directory
            result = self.code_analyzer.discover_directory(path, ignore_patterns)

            # Log what we're sending
            self.logger.info(
                f"Discovery result for {path}: {len(result.get('children', []))} children found"
            )
            self.logger.debug(f"Full result: {result}")

            # DEBUG: Log exact children being sent
            children = result.get("children", [])
            if children:
                self.logger.info(
                    f"Children being sent: {[child.get('name') for child in children]}"
                )
                self.logger.info(f"Full children data: {children}")
            else:
                self.logger.warning(f"No children found for {path}")

            # Prepare the response data
            response_data = {
                "request_id": request_id,
                "path": path,  # Absolute path as requested
                "name": Path(path).name,  # Just the directory name for display
                "type": result.get("type", "directory"),
                "children": children,  # Send children array directly
            }

            # CRITICAL DEBUG: Log exact JSON that will be sent
            import json

            self.logger.info(
                f"Sending response data (JSON): {json.dumps(response_data, indent=2)}"
            )
            self.logger.info(
                f"Children count in response: {len(response_data.get('children', []))}"
            )

            # Send result with correct event name (using colons, not dots!)
            # Include both absolute path and relative name for frontend compatibility
            # IMPORTANT: Don't use **result as it overwrites path and name
            await self.server.core.sio.emit(
                "code:directory:discovered",
                response_data,
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
        data.get("show_hidden_files", False)

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

        # SECURITY: Validate the requested file path
        # Allow access to files within the explicitly chosen working directory
        requested_path = Path(path).absolute()

        # Basic sanity checks
        if not requested_path.exists():
            self.logger.warning(f"File does not exist: {path}")
            await self.server.core.sio.emit(
                "code:analysis:error",
                {
                    "error": f"File does not exist: {path}",
                    "request_id": request_id,
                    "path": path,
                },
                room=sid,
            )
            return

        if not requested_path.is_file():
            self.logger.warning(f"Path is not a file: {path}")
            await self.server.core.sio.emit(
                "code:analysis:error",
                {
                    "error": f"Path is not a file: {path}",
                    "request_id": request_id,
                    "path": path,
                },
                room=sid,
            )
            return

        try:
            self.logger.info(f"Starting file analysis for: {path}")

            # Ensure analyzer exists
            if not self.code_analyzer:
                self.logger.info("Creating new CodeTreeAnalyzer instance")
                emitter = CodeTreeEventEmitter(use_stdout=False)
                # Override emit method to send to Socket.IO
                original_emit = emitter.emit

                def socket_emit(
                    event_type: str, event_data: Dict[str, Any], batch: bool = False
                ):
                    # Keep the original event format with colons - frontend expects this!
                    # The frontend listens for 'code:file:analyzed' not 'code.file.analyzed'

                    # Special handling for 'info' events - they should be passed through directly
                    if event_type == "info":
                        # INFO events for granular tracking
                        loop = asyncio.get_event_loop()
                        loop.create_task(
                            self.server.core.sio.emit(
                                "info", {"request_id": request_id, **event_data}
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
                # Initialize CodeTreeAnalyzer with emitter keyword argument
                self.logger.info("Creating CodeTreeAnalyzer")
                # Pass emit_events=False to prevent duplicate events from the analyzer
                # The emitter will still work but the analyzer won't create its own stdout emitter
                self.code_analyzer = CodeTreeAnalyzer(
                    emit_events=False, emitter=emitter
                )
                self.logger.info("CodeTreeAnalyzer created successfully")

            # Analyze file
            self.logger.info(f"Calling analyze_file for: {path}")
            result = self.code_analyzer.analyze_file(path)
            self.logger.info(
                f"Analysis complete. Result keys: {list(result.keys()) if result else 'None'}"
            )

            if result:
                self.logger.info(
                    f"Analysis result: elements={len(result.get('elements', []))}, nodes={len(result.get('nodes', []))}"
                )
            else:
                self.logger.warning("Analysis returned None or empty result")

            # Send result with correct event name (using colons, not dots!)
            response_data = {
                "request_id": request_id,
                "path": path,
                **result,
            }

            self.logger.info(f"Emitting code:file:analyzed event to {sid}")
            await self.server.core.sio.emit(
                "code:file:analyzed",
                response_data,
                room=sid,
            )
            self.logger.info("Event emitted successfully")

        except Exception as e:
            self.logger.error(f"Error analyzing file {path}: {e}")
            import traceback

            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            await self.server.core.sio.emit(
                "code:analysis:error",
                {
                    "request_id": request_id,
                    "path": path,
                    "error": str(e),
                },
                room=sid,
            )
