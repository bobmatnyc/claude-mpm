"""
Browser Console Handler for Unified Monitor
===========================================

WHY: This handler manages browser console events from web pages that have
the browser console monitor script injected. It provides centralized logging
and debugging capabilities for client-side applications.

DESIGN DECISIONS:
- Creates separate log files per browser session for easy tracking
- Stores logs in .claude-mpm/logs/client/ directory
- Handles multiple concurrent browser connections
- Tracks active browser sessions with metadata
- Provides structured logging with timestamps and context
- Integrates with the unified monitor architecture
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Set

import socketio

from ....core.logging_config import get_logger


class BrowserHandler:
    """Event handler for browser console monitoring functionality.

    WHY: Manages browser console events from injected monitoring scripts
    and provides centralized logging for client-side debugging.
    """

    def __init__(self, sio: socketio.AsyncServer):
        """Initialize the browser handler.

        Args:
            sio: Socket.IO server instance
        """
        self.sio = sio
        self.logger = get_logger(__name__)

        # Browser session management
        self.active_browsers: Set[str] = set()
        self.browser_info: Dict[str, Dict] = {}

        # Logging configuration
        self.log_dir = Path.cwd() / ".claude-mpm" / "logs" / "client"
        self.log_files: Dict[str, Path] = {}

        # Ensure log directory exists
        self._ensure_log_directory()

    def register(self):
        """Register Socket.IO event handlers."""
        try:
            # Browser connection events
            self.sio.on("browser:connect", self.handle_browser_connect)
            self.sio.on("browser:disconnect", self.handle_browser_disconnect)
            self.sio.on("browser:hide", self.handle_browser_hide)

            # Console events
            self.sio.on("browser:console", self.handle_console_event)

            # Browser management events
            self.sio.on("browser:list", self.handle_browser_list)
            self.sio.on("browser:info", self.handle_browser_info)

            self.logger.info("Browser event handlers registered")

        except Exception as e:
            self.logger.error(f"Error registering browser handlers: {e}")
            raise

    def _ensure_log_directory(self):
        """Ensure the client logs directory exists."""
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Client logs directory ensured: {self.log_dir}")
        except Exception as e:
            self.logger.error(f"Error creating client logs directory: {e}")
            raise

    def _get_log_file_path(self, browser_id: str) -> Path:
        """Get log file path for a browser session.

        Args:
            browser_id: Unique browser identifier

        Returns:
            Path to the log file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{browser_id}_{timestamp}.log"
        return self.log_dir / log_filename

    def _write_log_entry(
        self,
        browser_id: str,
        level: str,
        message: str,
        timestamp: str = None,
        extra_data: Dict = None,
    ):
        """Write a log entry to the browser's log file.

        Args:
            browser_id: Browser identifier
            level: Log level (INFO, ERROR, etc.)
            message: Log message
            timestamp: Event timestamp (ISO format)
            extra_data: Additional event data
        """
        try:
            # Get or create log file for this browser
            if browser_id not in self.log_files:
                self.log_files[browser_id] = self._get_log_file_path(browser_id)

            log_file = self.log_files[browser_id]

            # Format timestamp
            if not timestamp:
                timestamp = datetime.now().isoformat()

            # Format log entry
            log_entry = f"[{timestamp}] [{level}] [{browser_id}] {message}"

            # Add extra data if provided
            if extra_data:
                filtered_data = {
                    k: v
                    for k, v in extra_data.items()
                    if k not in ["browser_id", "level", "timestamp", "message"]
                }
                if filtered_data:
                    log_entry += f"\n  Data: {json.dumps(filtered_data, indent=2)}"

            # Write to file
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")

            self.logger.debug(f"Log entry written for {browser_id}: {level}")

        except Exception as e:
            self.logger.error(f"Error writing log entry for {browser_id}: {e}")

    async def handle_browser_connect(self, sid: str, data: Dict):
        """Handle browser connection event.

        Args:
            sid: Socket.IO session ID
            data: Browser connection data
        """
        try:
            browser_id = data.get("browser_id")
            if not browser_id:
                self.logger.warning(f"Browser connect without ID from {sid}")
                return

            # Track browser session
            self.active_browsers.add(browser_id)

            # Store browser info
            browser_info = {
                "browser_id": browser_id,
                "socket_id": sid,
                "connected_at": datetime.now().isoformat(),
                "user_agent": data.get("user_agent", "Unknown"),
                "url": data.get("url", "Unknown"),
                "last_activity": datetime.now().isoformat(),
            }
            self.browser_info[browser_id] = browser_info

            # Log connection
            self._write_log_entry(
                browser_id,
                "INFO",
                f'Browser connected from {data.get("url", "unknown URL")}',
                data.get("timestamp"),
                browser_info,
            )

            self.logger.info(f"Browser connected: {browser_id} from {data.get('url')}")

            # Send acknowledgment
            await self.sio.emit(
                "browser:connected",
                {
                    "browser_id": browser_id,
                    "status": "connected",
                    "message": "Console monitoring active",
                },
                room=sid,
            )

            # Broadcast browser count update to dashboard
            await self._broadcast_browser_stats()

        except Exception as e:
            self.logger.error(f"Error handling browser connect: {e}")

    async def handle_browser_disconnect(self, sid: str, data: Dict):
        """Handle browser disconnection event.

        Args:
            sid: Socket.IO session ID
            data: Browser disconnection data
        """
        try:
            browser_id = data.get("browser_id")
            if not browser_id:
                return

            # Log disconnection
            self._write_log_entry(
                browser_id, "INFO", "Browser disconnected", data.get("timestamp")
            )

            # Update browser info
            if browser_id in self.browser_info:
                self.browser_info[browser_id][
                    "disconnected_at"
                ] = datetime.now().isoformat()
                self.browser_info[browser_id]["status"] = "disconnected"

            self.logger.info(f"Browser disconnected: {browser_id}")

            # Broadcast browser count update
            await self._broadcast_browser_stats()

        except Exception as e:
            self.logger.error(f"Error handling browser disconnect: {e}")

    async def handle_browser_hide(self, sid: str, data: Dict):
        """Handle browser hide event (tab hidden/mobile app backgrounded).

        Args:
            sid: Socket.IO session ID
            data: Browser hide data
        """
        try:
            browser_id = data.get("browser_id")
            if not browser_id:
                return

            # Log hide event
            self._write_log_entry(
                browser_id,
                "INFO",
                "Browser tab hidden/backgrounded",
                data.get("timestamp"),
            )

            # Update browser info
            if browser_id in self.browser_info:
                self.browser_info[browser_id]["hidden_at"] = datetime.now().isoformat()
                self.browser_info[browser_id]["status"] = "hidden"

            self.logger.debug(f"Browser hidden: {browser_id}")

        except Exception as e:
            self.logger.error(f"Error handling browser hide: {e}")

    async def handle_console_event(self, sid: str, data: Dict):
        """Handle console event from browser.

        Args:
            sid: Socket.IO session ID
            data: Console event data
        """
        try:
            browser_id = data.get("browser_id")
            level = data.get("level", "LOG")
            message = data.get("message", "")
            timestamp = data.get("timestamp")

            if not browser_id:
                self.logger.warning(f"Console event without browser ID from {sid}")
                return

            # Update last activity
            if browser_id in self.browser_info:
                self.browser_info[browser_id][
                    "last_activity"
                ] = datetime.now().isoformat()

            # Log console event
            self._write_log_entry(browser_id, level, message, timestamp, data)

            # Log to main logger based on level
            log_message = f"[{browser_id}] {message}"
            if level == "ERROR":
                self.logger.error(log_message)
            elif level == "WARN":
                self.logger.warning(log_message)
            else:
                self.logger.debug(log_message)

            # Format log entry for dashboard
            log_entry = {
                "browser_id": browser_id,
                "level": level,
                "message": message,
                "timestamp": timestamp,
                "url": data.get("url"),
                "line_info": data.get("line_info"),
            }

            # Forward event to dashboard clients using both event names for compatibility
            await self.sio.emit("dashboard:browser:console", log_entry)
            await self.sio.emit("browser_log", log_entry)

        except Exception as e:
            self.logger.error(f"Error handling console event: {e}")

    async def handle_browser_list(self, sid: str, data: Dict):
        """Handle browser list request.

        Args:
            sid: Socket.IO session ID
            data: Request data
        """
        try:
            browser_list = []
            for browser_id, info in self.browser_info.items():
                browser_list.append(
                    {
                        "browser_id": browser_id,
                        "url": info.get("url", "Unknown"),
                        "user_agent": info.get("user_agent", "Unknown"),
                        "connected_at": info.get("connected_at"),
                        "last_activity": info.get("last_activity"),
                        "status": info.get("status", "active"),
                    }
                )

            await self.sio.emit(
                "browser:list:response",
                {
                    "browsers": browser_list,
                    "total": len(browser_list),
                    "active": len(self.active_browsers),
                },
                room=sid,
            )

        except Exception as e:
            self.logger.error(f"Error getting browser list: {e}")
            await self.sio.emit(
                "browser:error", {"error": f"Browser list error: {e!s}"}, room=sid
            )

    async def handle_browser_info(self, sid: str, data: Dict):
        """Handle browser info request.

        Args:
            sid: Socket.IO session ID
            data: Request data containing browser_id
        """
        try:
            browser_id = data.get("browser_id")
            if not browser_id or browser_id not in self.browser_info:
                await self.sio.emit(
                    "browser:error", {"error": "Browser not found"}, room=sid
                )
                return

            info = self.browser_info[browser_id]

            # Add log file info
            log_file_path = self.log_files.get(browser_id)
            if log_file_path and log_file_path.exists():
                info["log_file"] = str(log_file_path)
                info["log_size"] = log_file_path.stat().st_size

            await self.sio.emit("browser:info:response", info, room=sid)

        except Exception as e:
            self.logger.error(f"Error getting browser info: {e}")
            await self.sio.emit(
                "browser:error", {"error": f"Browser info error: {e!s}"}, room=sid
            )

    async def _broadcast_browser_stats(self):
        """Broadcast browser statistics to all dashboard clients."""
        try:
            stats = {
                "total_browsers": len(self.browser_info),
                "active_browsers": len(self.active_browsers),
                "connected_browsers": len(
                    [
                        info
                        for info in self.browser_info.values()
                        if info.get("status") != "disconnected"
                    ]
                ),
            }

            await self.sio.emit("dashboard:browser:stats", stats)

        except Exception as e:
            self.logger.error(f"Error broadcasting browser stats: {e}")

    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Clean up old browser sessions and log files.

        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        try:
            from datetime import timedelta

            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            # Remove old browser info
            to_remove = []
            for browser_id, info in self.browser_info.items():
                try:
                    last_activity = datetime.fromisoformat(
                        info.get("last_activity", "")
                    )
                    if last_activity < cutoff_time:
                        to_remove.append(browser_id)
                except (ValueError, TypeError):
                    # Invalid timestamp, mark for removal
                    to_remove.append(browser_id)

            for browser_id in to_remove:
                self.browser_info.pop(browser_id, None)
                self.active_browsers.discard(browser_id)
                self.log_files.pop(browser_id, None)

            if to_remove:
                self.logger.info(f"Cleaned up {len(to_remove)} old browser sessions")

        except Exception as e:
            self.logger.error(f"Error cleaning up browser sessions: {e}")

    def get_stats(self) -> Dict:
        """Get handler statistics.

        Returns:
            Dictionary with handler stats
        """
        return {
            "total_browsers": len(self.browser_info),
            "active_browsers": len(self.active_browsers),
            "log_files": len(self.log_files),
            "log_directory": str(self.log_dir),
        }
