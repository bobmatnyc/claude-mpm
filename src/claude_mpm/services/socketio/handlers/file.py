"""File operation event handlers for Socket.IO.

WHY: This module handles file-related events including reading file content
safely with security checks. Separating file operations improves security
auditing and makes it easier to add file-related features.
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path

from .base import BaseEventHandler
from ....deployment_paths import get_project_root
from ....core.typing_utils import SocketId, EventData, PathLike


class FileEventHandler(BaseEventHandler):
    """Handles file operation Socket.IO events.
    
    WHY: File operations require careful security considerations and
    consistent error handling. Having a dedicated handler ensures
    all file operations follow the same security patterns.
    """
    
    def register_events(self) -> None:
        """Register file operation event handlers."""
        
        @self.sio.event
        async def read_file(sid, data):
            """Read file contents safely.
            
            WHY: The dashboard needs to display file contents when users
            click on files, but we must ensure secure file access with
            proper validation and size limits.
            """
            try:
                file_path = data.get('file_path')
                working_dir = data.get('working_dir', os.getcwd())
                max_size = data.get('max_size', 1024 * 1024)  # 1MB default limit
                
                if not file_path:
                    await self.emit_to_client(sid, 'file_content_response', {
                        'success': False,
                        'error': 'file_path is required',
                        'file_path': file_path
                    })
                    return
                
                # Use the shared file reading logic
                result = await self._read_file_safely(file_path, working_dir, max_size)
                
                # Send the result back to the client
                await self.emit_to_client(sid, 'file_content_response', result)
                        
            except Exception as e:
                self.log_error("read_file", e, data)
                await self.emit_to_client(sid, 'file_content_response', {
                    'success': False,
                    'error': str(e),
                    'file_path': data.get('file_path', 'unknown')
                })
    
    async def _read_file_safely(self, file_path: str, working_dir: Optional[str] = None, max_size: int = 1024 * 1024) -> EventData:
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
                return self._read_binary_file(real_path, file_path, file_size)
                    
        except Exception as e:
            self.logger.error(f"Error in _read_file_safely: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path
            }
    
    def _read_binary_file(self, real_path: str, file_path: str, file_size: int) -> Dict[str, Any]:
        """Handle binary or non-UTF8 files.
        
        WHY: Not all files are UTF-8 encoded. We need to handle other
        encodings gracefully and detect binary files that shouldn't
        be displayed as text.
        """
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