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

import uuid
from typing import Any, Dict, Optional

from ....core.logging_config import get_logger
from ....dashboard.analysis_runner import CodeAnalysisRunner
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
            "code:analyze:request": self.handle_analyze_request,
            "code:analyze:cancel": self.handle_cancel_request,
            "code:analyze:status": self.handle_status_request,
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
                    "request_id": data.get("request_id")
                },
                room=sid
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
            ignore_patterns=ignore_patterns
        )
        
        if success:
            # Send acknowledgment to requesting client
            await self.server.sio.emit(
                "code:analysis:accepted",
                {
                    "request_id": request_id,
                    "path": path,
                    "message": "Analysis request queued"
                },
                room=sid
            )
        else:
            # Send error if request failed
            await self.server.sio.emit(
                "code:analysis:error",
                {
                    "request_id": request_id,
                    "message": "Failed to queue analysis request"
                },
                room=sid
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
            {
                "message": "Analysis cancelled",
                "request_id": data.get("request_id")
            },
            room=sid
        )
        
    async def handle_status_request(self, sid: str, data: Dict[str, Any]):
        """Handle status request from client.
        
        Args:
            sid: Socket ID of the requesting client
            data: Request data (unused)
        """
        status = self.analysis_runner.get_status()
        
        # Send status to requesting client
        await self.server.sio.emit(
            "code:analysis:status",
            status,
            room=sid
        )