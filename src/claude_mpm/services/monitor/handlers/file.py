"""
File Handler for Unified Monitor Server
========================================

WHY: Provides file reading capabilities for the dashboard file viewer.
This handler allows the dashboard to display file contents when users
click on files in the code tree or other file references.

DESIGN DECISIONS:
- Secure file reading with path validation
- Size limits to prevent memory issues
- Compatible with UnifiedMonitorServer architecture
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import socketio

from ....core.logging_config import get_logger
from ....core.unified_paths import get_project_root


class FileHandler:
    """Socket.IO handler for file operations in the unified monitor server.

    WHY: The dashboard needs to display file contents when users click on files,
    but we must ensure secure file access with proper validation and size limits.
    """

    def __init__(self, sio: socketio.AsyncServer):
        """Initialize the file handler.

        Args:
            sio: Socket.IO server instance
        """
        self.sio = sio
        self.logger = get_logger(__name__)

    def register(self):
        """Register Socket.IO event handlers for file operations."""
        self.logger.info("[FileHandler] Registering file event handlers")

        @self.sio.event
        async def read_file(sid, data):
            """Handle file read requests from dashboard clients.

            WHY: The dashboard needs to display file contents when users
            click on files, but we must ensure secure file access with
            proper validation and size limits.
            """
            self.logger.info(
                f"[FileHandler] Received read_file event from {sid} with data: {data}"
            )

            try:
                file_path = data.get("file_path")
                working_dir = data.get("working_dir", os.getcwd())
                max_size = data.get("max_size", 1024 * 1024)  # 1MB default limit

                if not file_path:
                    self.logger.warning(
                        f"[FileHandler] Missing file_path in request from {sid}"
                    )
                    await self.sio.emit(
                        "file_content_response",
                        {
                            "success": False,
                            "error": "file_path is required",
                            "file_path": file_path,
                        },
                        room=sid,
                    )
                    return

                # Read the file safely
                self.logger.info(
                    f"[FileHandler] Reading file: {file_path} from working_dir: {working_dir}"
                )
                result = await self._read_file_safely(file_path, working_dir, max_size)

                # Send the result back to the client
                self.logger.info(
                    f"[FileHandler] Sending file_content_response to {sid}, success: {result.get('success', False)}"
                )
                await self.sio.emit("file_content_response", result, room=sid)
                self.logger.info(f"[FileHandler] Response sent successfully to {sid}")

            except Exception as e:
                self.logger.error(
                    f"[FileHandler] Exception in read_file handler: {e}", exc_info=True
                )
                await self.sio.emit(
                    "file_content_response",
                    {
                        "success": False,
                        "error": str(e),
                        "file_path": data.get("file_path", "unknown"),
                    },
                    room=sid,
                )
                self.logger.info(f"[FileHandler] Error response sent to {sid}")

        self.logger.info("[FileHandler] File event handlers registered successfully")

    async def _read_file_safely(
        self,
        file_path: str,
        working_dir: Optional[str] = None,
        max_size: int = 1024 * 1024,
    ) -> Dict[str, Any]:
        """Safely read file content with security checks.

        WHY: File reading must be secure to prevent directory traversal attacks
        and resource exhaustion. This method centralizes all security checks
        and provides consistent error handling.

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
            file_path_obj = Path(file_path)
            if not file_path_obj.is_absolute():
                full_path = Path(working_dir) / file_path
            else:
                full_path = file_path_obj

            # Security check: ensure file is within working directory or project
            try:
                real_path = full_path.resolve()
                real_working_dir = Path(working_dir).resolve()

                # Allow access to files within working directory or the project root
                project_root = Path(get_project_root()).resolve()
                allowed_paths = [real_working_dir, project_root]

                is_allowed = any(
                    str(real_path).startswith(str(allowed_path))
                    for allowed_path in allowed_paths
                )

                if not is_allowed:
                    return {
                        "success": False,
                        "error": "Access denied: file is outside allowed directories",
                        "file_path": file_path,
                    }

            except Exception as path_error:
                self.logger.error(f"Path validation error: {path_error}")
                return {
                    "success": False,
                    "error": "Invalid file path",
                    "file_path": file_path,
                }

            # Check if file exists
            if not real_path.exists():
                return {
                    "success": False,
                    "error": "File does not exist",
                    "file_path": file_path,
                }

            # Check if it's a file (not directory)
            if not real_path.is_file():
                return {
                    "success": False,
                    "error": "Path is not a file",
                    "file_path": file_path,
                }

            # Check file size
            file_size = real_path.stat().st_size
            if file_size > max_size:
                return {
                    "success": False,
                    "error": f"File too large ({file_size} bytes). Maximum allowed: {max_size} bytes",
                    "file_path": file_path,
                    "file_size": file_size,
                }

            # Read file content
            try:
                with open(real_path, encoding="utf-8") as f:
                    content = f.read()

                # Get file extension for syntax highlighting hint
                ext = real_path.suffix

                return {
                    "success": True,
                    "file_path": file_path,
                    "content": content,
                    "file_size": file_size,
                    "extension": ext.lower(),
                    "encoding": "utf-8",
                }

            except UnicodeDecodeError:
                # Try reading as binary if UTF-8 fails
                return self._read_binary_file(real_path, file_path, file_size)

        except Exception as e:
            self.logger.error(f"Error in _read_file_safely: {e}")
            return {"success": False, "error": str(e), "file_path": file_path}

    def _read_binary_file(
        self, real_path: Path, file_path: str, file_size: int
    ) -> Dict[str, Any]:
        """Handle binary or non-UTF8 files.

        WHY: Not all files are UTF-8 encoded. We need to handle other
        encodings gracefully and detect binary files that shouldn't
        be displayed as text.
        """
        try:
            with open(real_path, "rb") as f:
                binary_content = f.read()

            # Check if it's a text file by looking for common text patterns
            try:
                text_content = binary_content.decode("latin-1")
                if "\x00" in text_content:
                    # Binary file
                    return {
                        "success": False,
                        "error": "File appears to be binary and cannot be displayed as text",
                        "file_path": file_path,
                        "file_size": file_size,
                    }
                # Text file with different encoding
                ext = real_path.suffix
                return {
                    "success": True,
                    "file_path": file_path,
                    "content": text_content,
                    "file_size": file_size,
                    "extension": ext.lower(),
                    "encoding": "latin-1",
                }
            except Exception:
                return {
                    "success": False,
                    "error": "File encoding not supported",
                    "file_path": file_path,
                }
        except Exception as read_error:
            return {
                "success": False,
                "error": f"Failed to read file: {read_error!s}",
                "file_path": file_path,
            }
