#!/usr/bin/env python3
"""
Code Analysis Runner for Dashboard
===================================

WHY: Manages subprocess execution of code analysis, streaming results to
Socket.IO clients in real-time while handling cancellation and error recovery.

DESIGN DECISIONS:
- Use subprocess for isolation and cancellation support
- Stream output line-by-line for real-time updates
- Queue multiple analysis requests
- Handle process lifecycle management
- Convert analyzer events to Socket.IO events
"""

import json
import os
import subprocess
import sys
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Any, Dict, List, Optional

from ..core.logging_config import get_logger


@dataclass
class AnalysisRequest:
    """Represents a code analysis request."""

    request_id: str
    path: str
    languages: Optional[List[str]] = None
    max_depth: Optional[int] = None
    ignore_patterns: Optional[List[str]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class CodeAnalysisRunner:
    """Manages code analysis subprocess execution for the dashboard.

    WHY: Provides isolation between the dashboard server and analysis process,
    allowing for cancellation, resource limits, and crash recovery.
    """

    def __init__(self, socketio_server):
        """Initialize the analysis runner.

        Args:
            socketio_server: SocketIOServer instance for broadcasting events
        """
        self.logger = get_logger(__name__)
        self.server = socketio_server
        self.current_process = None
        self.current_request = None
        self.request_queue = Queue()
        self.running = False
        self.worker_thread = None
        self.cancel_event = threading.Event()

        # Statistics
        self.stats = {
            "analyses_started": 0,
            "analyses_completed": 0,
            "analyses_cancelled": 0,
            "analyses_failed": 0,
            "total_files": 0,
            "total_nodes": 0,
        }

    def start(self):
        """Start the analysis runner worker thread."""
        if self.running:
            return

        self.running = True
        self.cancel_event.clear()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        self.logger.info("Code analysis runner started")

    def stop(self):
        """Stop the analysis runner and cleanup."""
        self.running = False
        self.cancel_current()

        # Add sentinel to queue to wake up worker
        self.request_queue.put(None)

        if self.worker_thread:
            self.worker_thread.join(timeout=5)

        self.logger.info("Code analysis runner stopped")

    def request_analysis(
        self,
        request_id: str,
        path: str,
        languages: Optional[List[str]] = None,
        max_depth: Optional[int] = None,
        ignore_patterns: Optional[List[str]] = None,
    ) -> bool:
        """Queue a new analysis request.

        Args:
            request_id: Unique request identifier
            path: Directory path to analyze
            languages: Optional list of languages to filter
            max_depth: Optional maximum directory depth
            ignore_patterns: Optional list of patterns to ignore

        Returns:
            True if request was queued successfully
        """
        # Validate path
        analysis_path = Path(path).resolve()
        if not analysis_path.exists():
            self._emit_error(request_id, f"Path does not exist: {path}")
            return False

        if not analysis_path.is_dir():
            self._emit_error(request_id, f"Path is not a directory: {path}")
            return False

        # Create request
        request = AnalysisRequest(
            request_id=request_id,
            path=str(analysis_path),
            languages=languages,
            max_depth=max_depth,
            ignore_patterns=ignore_patterns,
        )

        # Queue request
        self.request_queue.put(request)
        self.logger.info(f"Queued analysis request {request_id} for {path}")

        # Emit queued event
        self._emit_event(
            "code:analysis:queued",
            {
                "request_id": request_id,
                "path": str(analysis_path),
                "queue_size": self.request_queue.qsize(),
            },
        )

        return True

    def cancel_current(self):
        """Cancel the currently running analysis."""
        if self.current_process and self.current_process.poll() is None:
            self.cancel_event.set()

            # Try graceful termination first
            self.current_process.terminate()
            try:
                self.current_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                # Force kill if needed
                self.current_process.kill()
                self.current_process.wait()

            self.stats["analyses_cancelled"] += 1

            if self.current_request:
                self._emit_event(
                    "code:analysis:cancelled",
                    {
                        "request_id": self.current_request.request_id,
                        "path": self.current_request.path,
                    },
                )

            self.logger.info("Cancelled current analysis")

    def get_status(self) -> Dict[str, Any]:
        """Get current runner status.

        Returns:
            Dictionary with current status and statistics
        """
        return {
            "running": self.running,
            "current_request": (
                asdict(self.current_request) if self.current_request else None
            ),
            "queue_size": self.request_queue.qsize(),
            "stats": self.stats.copy(),
        }

    def _worker_loop(self):
        """Worker thread loop for processing analysis requests."""
        while self.running:
            try:
                # Get next request (blocking with timeout)
                request = self.request_queue.get(timeout=1)

                if request is None:  # Sentinel value
                    break

                # Reset cancel event
                self.cancel_event.clear()

                # Process request
                self._process_request(request)

            except Exception as e:
                self.logger.error(f"Error in worker loop: {e}")

    def _process_request(self, request: AnalysisRequest):
        """Process a single analysis request.

        Args:
            request: The analysis request to process
        """
        self.current_request = request
        self.stats["analyses_started"] += 1

        try:
            # Emit start event
            self._emit_event(
                "code:analysis:start",
                {
                    "request_id": request.request_id,
                    "path": request.path,
                    "languages": request.languages,
                    "timestamp": request.timestamp.isoformat(),
                },
            )

            # Build command
            cmd = self._build_command(request)
            self.logger.info(f"Starting analysis subprocess: {' '.join(cmd)}")

            # Start subprocess
            try:
                self.current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    env=self._get_subprocess_env(),
                )
                self.logger.debug(
                    f"Subprocess started with PID: {self.current_process.pid}"
                )
            except FileNotFoundError as e:
                raise subprocess.SubprocessError(
                    f"Python executable not found: {cmd[0]}"
                ) from e
            except Exception as e:
                raise subprocess.SubprocessError(
                    f"Failed to start subprocess: {e}"
                ) from e

            # Process output
            self._process_output(request)

            # Wait for completion
            return_code = self.current_process.wait()

            if self.cancel_event.is_set():
                # Analysis was cancelled
                pass  # Event already emitted in cancel_current
            elif return_code == 0:
                # Success
                self.stats["analyses_completed"] += 1
                self._emit_event(
                    "code:analysis:complete",
                    {
                        "request_id": request.request_id,
                        "path": request.path,
                        "stats": {
                            "total_files": self.stats["total_files"],
                            "total_nodes": self.stats["total_nodes"],
                        },
                    },
                )
            else:
                # Failure - capture any remaining stderr
                stderr_output = ""
                if self.current_process.stderr:
                    try:
                        # Read any remaining stderr output
                        stderr_lines = []
                        for line in self.current_process.stderr:
                            stderr_lines.append(line.strip())
                        stderr_output = "\n".join(stderr_lines)
                    except Exception as e:
                        stderr_output = f"Failed to read stderr: {e}"

                self.stats["analyses_failed"] += 1
                error_msg = f"Analysis failed with code {return_code}"
                if stderr_output:
                    error_msg += f": {stderr_output}"

                self.logger.error(f"Subprocess failed: {error_msg}")
                self._emit_error(request.request_id, error_msg)

        except subprocess.SubprocessError as e:
            self.logger.error(f"Subprocess error for request {request.request_id}: {e}")
            self.stats["analyses_failed"] += 1
            self._emit_error(request.request_id, f"Failed to start analyzer: {e}")
        except Exception as e:
            self.logger.error(
                f"Error processing request {request.request_id}: {e}", exc_info=True
            )
            self.stats["analyses_failed"] += 1
            self._emit_error(request.request_id, str(e))

        finally:
            self.current_process = None
            self.current_request = None

    def _build_command(self, request: AnalysisRequest) -> List[str]:
        """Build the subprocess command for analysis.

        Args:
            request: The analysis request

        Returns:
            Command list for subprocess.Popen
        """
        # Get Python executable
        python_exe = sys.executable

        # Build command - use the CLI analyze-code command
        cmd = [
            python_exe,
            "-m",
            "claude_mpm",
            "analyze-code",
            request.path,
            "--emit-events",
            "--output",
            "json",
        ]

        # Add optional parameters
        if request.languages:
            cmd.extend(["--languages", ",".join(request.languages)])

        if request.max_depth:
            cmd.extend(["--max-depth", str(request.max_depth)])

        if request.ignore_patterns:
            for pattern in request.ignore_patterns:
                cmd.extend(["--ignore", pattern])

        return cmd

    def _get_subprocess_env(self) -> Dict[str, str]:
        """Get environment variables for subprocess.

        Returns:
            Environment dictionary for subprocess
        """
        env = os.environ.copy()

        # Ensure Socket.IO URL is set for event emission
        env["SOCKETIO_URL"] = f"http://localhost:{self.server.port}"

        # Set Python path to include our modules
        python_path = env.get("PYTHONPATH", "")
        src_path = str(Path(__file__).parent.parent.parent)
        if src_path not in python_path:
            env["PYTHONPATH"] = f"{src_path}:{python_path}" if python_path else src_path

        return env

    def _process_output(self, request: AnalysisRequest):
        """Process subprocess output and emit events.

        Args:
            request: The current analysis request
        """
        if not self.current_process:
            return

        # Read output line by line
        for line in iter(self.current_process.stdout.readline, ""):
            if self.cancel_event.is_set():
                break

            line = line.strip()
            if not line:
                continue

            try:
                # Parse JSON event
                event = json.loads(line)

                # Route event to appropriate handler
                event_type = event.get("type")
                event_data = event.get("data", {})

                # Add request ID to event data
                event_data["request_id"] = request.request_id

                # Update statistics based on event type
                if event_type == "code:file:complete":
                    self.stats["total_files"] += 1
                elif event_type == "code:node:found":
                    self.stats["total_nodes"] += 1

                # Emit to Socket.IO clients
                self._emit_event(event_type, event_data)

            except json.JSONDecodeError:
                # Not JSON, treat as log message
                self.logger.debug(f"Analyzer output: {line}")
            except Exception as e:
                self.logger.warning(f"Error processing analyzer output: {e}")

    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit an event to Socket.IO clients.

        Args:
            event_type: Type of event
            data: Event data
        """
        if self.server:
            # Add timestamp if not present
            if "timestamp" not in data:
                data["timestamp"] = datetime.utcnow().isoformat()

            # Broadcast to all clients
            self.server.broadcast_event(event_type, data)

    def _emit_error(self, request_id: str, message: str):
        """Emit an error event.

        Args:
            request_id: Request that caused the error
            message: Error message
        """
        self._emit_event(
            "code:analysis:error",
            {
                "request_id": request_id,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
