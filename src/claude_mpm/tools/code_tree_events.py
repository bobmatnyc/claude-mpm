#!/usr/bin/env python3
"""
Code Tree Event Emitter
=======================

WHY: Provides incremental event emission for real-time code tree visualization
in the dashboard. Uses Socket.IO to stream events as code is analyzed.

DESIGN DECISIONS:
- Batch events for performance (emit every 10 nodes or 100ms)
- Include progress tracking for large codebases
- Use structured event format for dashboard consumption
- Support resumable processing with event checkpoints
"""

import asyncio
import json
import sys
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    socketio = None

from ..core.logging_config import get_logger


@dataclass
class CodeNodeEvent:
    """Represents a code node discovery event."""
    file_path: str
    node_type: str  # 'class', 'function', 'method', 'module', 'import'
    name: str
    line_start: int
    line_end: int
    complexity: int = 0
    has_docstring: bool = False
    decorators: List[str] = None
    parent: Optional[str] = None
    children_count: int = 0
    language: str = "python"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['timestamp'] = datetime.utcnow().isoformat()
        return data


class CodeTreeEventEmitter:
    """Emits code analysis events to dashboard via Socket.IO.
    
    WHY: Real-time streaming of analysis progress allows users to see
    the tree building incrementally, providing feedback for large codebases.
    """
    
    # Event types
    EVENT_FILE_START = "code:file:start"
    EVENT_FILE_COMPLETE = "code:file:complete"
    EVENT_NODE_FOUND = "code:node:found"
    EVENT_ANALYSIS_START = "code:analysis:start"
    EVENT_ANALYSIS_COMPLETE = "code:analysis:complete"
    EVENT_PROGRESS = "code:progress"
    EVENT_ERROR = "code:error"
    
    def __init__(self, socketio_url: str = "http://localhost:8765", 
                 batch_size: int = 10, batch_timeout: float = 0.1,
                 use_stdout: bool = False):
        """Initialize event emitter.
        
        Args:
            socketio_url: Socket.IO server URL
            batch_size: Number of events to batch before emitting
            batch_timeout: Maximum time to wait before emitting batch (seconds)
            use_stdout: If True, emit to stdout instead of Socket.IO
        """
        self.logger = get_logger(__name__)
        self.socketio_url = socketio_url
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.use_stdout = use_stdout
        
        # Event buffer for batching
        self.event_buffer = deque()
        self.buffer_lock = threading.Lock()
        self.last_emit_time = time.time()
        
        # Socket.IO client
        self.sio = None
        self.connected = False
        if not use_stdout:
            self._init_socketio()
        
        # Statistics
        self.stats = {
            "events_sent": 0,
            "events_buffered": 0,
            "files_processed": 0,
            "nodes_found": 0,
            "errors": 0,
            "start_time": None
        }
        
        # Background task for periodic emission
        self._emit_task = None
        self._stop_event = threading.Event()
        
    def _init_socketio(self):
        """Initialize Socket.IO client connection."""
        if not SOCKETIO_AVAILABLE:
            self.logger.warning("Socket.IO not available - events will be logged only")
            return
            
        try:
            self.sio = socketio.Client(
                reconnection=True,
                reconnection_attempts=3,
                reconnection_delay=1,
                logger=False,
                engineio_logger=False
            )
            
            @self.sio.event
            def connect():
                self.connected = True
                self.logger.info(f"Connected to Socket.IO server at {self.socketio_url}")
                
            @self.sio.event
            def disconnect():
                self.connected = False
                self.logger.info("Disconnected from Socket.IO server")
                
            # Attempt connection
            self.sio.connect(self.socketio_url, wait_timeout=2)
            
        except Exception as e:
            self.logger.warning(f"Failed to connect to Socket.IO: {e}")
            self.sio = None
    
    def start(self):
        """Start the event emitter and background tasks."""
        self.stats["start_time"] = datetime.utcnow()
        self._stop_event.clear()
        
        # Start background emit task
        self._emit_task = threading.Thread(target=self._emit_loop, daemon=True)
        self._emit_task.start()
        
        # Emit analysis start event
        self.emit(self.EVENT_ANALYSIS_START, {
            "timestamp": datetime.utcnow().isoformat(),
            "batch_size": self.batch_size,
            "batch_timeout": self.batch_timeout
        })
        
    def stop(self):
        """Stop the event emitter and flush remaining events."""
        # Flush remaining events
        self._flush_events()
        
        # Emit analysis complete event with statistics
        self.emit(self.EVENT_ANALYSIS_COMPLETE, {
            "timestamp": datetime.utcnow().isoformat(),
            "duration": (datetime.utcnow() - self.stats["start_time"]).total_seconds()
                       if self.stats["start_time"] else 0,
            "stats": self.stats
        })
        
        # Stop background task
        self._stop_event.set()
        if self._emit_task:
            self._emit_task.join(timeout=1)
            
        # Disconnect Socket.IO
        if self.sio and self.connected:
            self.sio.disconnect()
            
    def emit(self, event_type: str, data: Dict[str, Any], batch: bool = False):
        """Emit an event, either immediately or batched.
        
        Args:
            event_type: Type of event to emit
            data: Event data
            batch: Whether to batch this event
        """
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if batch:
            with self.buffer_lock:
                self.event_buffer.append(event)
                self.stats["events_buffered"] += 1
                
                # Check if we should flush
                if len(self.event_buffer) >= self.batch_size:
                    self._flush_events()
        else:
            self._emit_event(event)
            
    def emit_file_start(self, file_path: str, language: str = None):
        """Emit file processing start event."""
        self.emit(self.EVENT_FILE_START, {
            "file": file_path,
            "language": language or "unknown"
        })
        
    def emit_file_complete(self, file_path: str, nodes_count: int = 0, 
                          duration: float = 0):
        """Emit file processing complete event."""
        self.stats["files_processed"] += 1
        self.emit(self.EVENT_FILE_COMPLETE, {
            "file": file_path,
            "nodes_count": nodes_count,
            "duration": duration
        })
        
    def emit_node(self, node: CodeNodeEvent):
        """Emit code node discovery event (batched)."""
        self.stats["nodes_found"] += 1
        # In stdout mode, don't batch - emit immediately for real-time updates
        batch_mode = not self.use_stdout
        self.emit(self.EVENT_NODE_FOUND, node.to_dict(), batch=batch_mode)
        
    def emit_progress(self, current: int, total: int, message: str = ""):
        """Emit progress update event."""
        self.emit(self.EVENT_PROGRESS, {
            "current": current,
            "total": total,
            "percentage": (current / total * 100) if total > 0 else 0,
            "message": message
        })
        
    def emit_error(self, file_path: str, error: str):
        """Emit error event."""
        self.stats["errors"] += 1
        self.emit(self.EVENT_ERROR, {
            "file": file_path,
            "error": str(error)
        })
        
    def _emit_event(self, event: Dict[str, Any]):
        """Emit a single event."""
        if self.use_stdout:
            # Emit to stdout as JSON for subprocess communication
            print(json.dumps(event), flush=True)
            self.stats["events_sent"] += 1
        elif self.sio and self.connected:
            try:
                self.sio.emit("code_tree_event", event)
                self.stats["events_sent"] += 1
            except Exception as e:
                self.logger.error(f"Failed to emit event: {e}")
        else:
            # Fallback to logging
            self.logger.debug(f"Event: {event['type']} - {json.dumps(event['data'])[:100]}")
            
    def _flush_events(self):
        """Flush all buffered events."""
        with self.buffer_lock:
            if not self.event_buffer:
                return
                
            # Emit as batch
            batch_event = {
                "type": "code:batch",
                "data": {
                    "events": list(self.event_buffer),
                    "count": len(self.event_buffer)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._emit_event(batch_event)
            self.event_buffer.clear()
            self.last_emit_time = time.time()
            
    def _emit_loop(self):
        """Background loop for periodic event emission."""
        while not self._stop_event.is_set():
            time.sleep(self.batch_timeout)
            
            # Check if enough time has passed since last emit
            if time.time() - self.last_emit_time >= self.batch_timeout:
                with self.buffer_lock:
                    if self.event_buffer:
                        self._flush_events()
                        
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        return self.stats.copy()