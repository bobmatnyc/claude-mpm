"""
Code Analysis Event Handler for Unified Monitor
===============================================

WHY: This handler provides real AST analysis functionality for the Code Tree
viewer. It uses the actual CodeTreeAnalyzer instead of mock data to generate
proper hierarchical data structures for 3D visualization.

DESIGN DECISIONS:
- Uses real CodeTreeAnalyzer for AST parsing
- Generates proper data structures for D3.js tree visualization
- Handles file analysis requests via Socket.IO events
- Provides real-time code analysis updates
"""

import asyncio
from typing import Dict, Optional

import socketio

from ....core.logging_config import get_logger

try:
    from ....tools.code_tree_analyzer import CodeTreeAnalyzer
    from ....tools.code_tree_builder import CodeTreeBuilder
except ImportError:
    # Fallback if tools are not available
    CodeTreeAnalyzer = None
    CodeTreeBuilder = None


class CodeAnalysisHandler:
    """Event handler for real code analysis functionality.

    WHY: Provides real AST analysis for the Code Tree viewer instead of mock data.
    Integrates the existing CodeTreeAnalyzer with the unified monitor daemon.
    """

    def __init__(self, sio: socketio.AsyncServer):
        """Initialize the code analysis handler.

        Args:
            sio: Socket.IO server instance
        """
        self.sio = sio
        self.logger = get_logger(__name__)

        # Analysis tools (with fallback)
        self.analyzer = CodeTreeAnalyzer() if CodeTreeAnalyzer else None
        self.builder = CodeTreeBuilder() if CodeTreeBuilder else None

        # Cache for analysis results
        self.analysis_cache = {}

    def register(self):
        """Register Socket.IO event handlers."""
        try:
            # File analysis events
            self.sio.on("code:analyze:file", self.handle_analyze_file)
            self.sio.on("code:analyze:directory", self.handle_analyze_directory)
            self.sio.on("code:get:tree", self.handle_get_tree)

            # Cache management
            self.sio.on("code:clear:cache", self.handle_clear_cache)

            self.logger.info("Code analysis event handlers registered")

        except Exception as e:
            self.logger.error(f"Error registering code analysis handlers: {e}")
            raise

    async def handle_analyze_file(self, sid: str, data: Dict):
        """Handle file analysis request.

        Args:
            sid: Socket.IO session ID
            data: Request data containing file path
        """
        try:
            file_path = data.get("path")
            if not file_path:
                await self.sio.emit(
                    "code:error", {"error": "No file path provided"}, room=sid
                )
                return

            self.logger.info(f"Analyzing file: {file_path}")

            # Check cache first
            cache_key = f"file:{file_path}"
            if cache_key in self.analysis_cache:
                self.logger.debug(f"Using cached analysis for {file_path}")
                # Send cached result in same format as fresh analysis
                cached_result = self.analysis_cache[cache_key]
                response_data = {
                    "path": file_path,
                    "cached": True,
                    **cached_result,  # Spread cached analysis result at top level
                }

                await self.sio.emit(
                    "code:file:analyzed",
                    response_data,
                    room=sid,
                )
                return

            # Perform real analysis
            analysis_result = await self._analyze_file_async(file_path)

            if analysis_result:
                # Cache the result
                self.analysis_cache[cache_key] = analysis_result

                # Emit the result in the same format as legacy server
                # Frontend expects analysis data at top level, not wrapped in "analysis" field
                response_data = {
                    "path": file_path,
                    "cached": False,
                    **analysis_result,  # Spread analysis result at top level
                }

                await self.sio.emit(
                    "code:file:analyzed",
                    response_data,
                    room=sid,
                )

                self.logger.info(f"File analysis completed: {file_path}")
            else:
                await self.sio.emit(
                    "code:error",
                    {"error": f"Failed to analyze file: {file_path}"},
                    room=sid,
                )

        except Exception as e:
            self.logger.error(f"Error analyzing file: {e}")
            await self.sio.emit(
                "code:error", {"error": f"Analysis error: {e!s}"}, room=sid
            )

    async def handle_analyze_directory(self, sid: str, data: Dict):
        """Handle directory analysis request.

        Args:
            sid: Socket.IO session ID
            data: Request data containing directory path
        """
        try:
            dir_path = data.get("path", ".")
            max_depth = data.get("max_depth", 3)

            self.logger.info(f"Analyzing directory: {dir_path}")

            # Check cache first
            cache_key = f"dir:{dir_path}:{max_depth}"
            if cache_key in self.analysis_cache:
                self.logger.debug(f"Using cached analysis for {dir_path}")
                await self.sio.emit(
                    "code:directory:analyzed",
                    {
                        "path": dir_path,
                        "tree": self.analysis_cache[cache_key],
                        "cached": True,
                    },
                    room=sid,
                )
                return

            # Build directory tree with analysis
            tree_result = await self._build_directory_tree_async(dir_path, max_depth)

            if tree_result:
                # Cache the result
                self.analysis_cache[cache_key] = tree_result

                # Emit the result
                await self.sio.emit(
                    "code:directory:analyzed",
                    {"path": dir_path, "tree": tree_result, "cached": False},
                    room=sid,
                )

                self.logger.info(f"Directory analysis completed: {dir_path}")
            else:
                await self.sio.emit(
                    "code:error",
                    {"error": f"Failed to analyze directory: {dir_path}"},
                    room=sid,
                )

        except Exception as e:
            self.logger.error(f"Error analyzing directory: {e}")
            await self.sio.emit(
                "code:error", {"error": f"Directory analysis error: {e!s}"}, room=sid
            )

    async def handle_get_tree(self, sid: str, data: Dict):
        """Handle request for code tree visualization data.

        Args:
            sid: Socket.IO session ID
            data: Request data
        """
        try:
            path = data.get("path", ".")
            format_type = data.get("format", "d3")  # d3, json, etc.

            self.logger.info(f"Getting tree for: {path}")

            # Get or build tree data
            tree_data = await self._get_tree_data_async(path, format_type)

            if tree_data:
                await self.sio.emit(
                    "code:tree:data",
                    {"path": path, "format": format_type, "tree": tree_data},
                    room=sid,
                )

                self.logger.info(f"Tree data sent for: {path}")
            else:
                await self.sio.emit(
                    "code:error",
                    {"error": f"Failed to get tree data for: {path}"},
                    room=sid,
                )

        except Exception as e:
            self.logger.error(f"Error getting tree data: {e}")
            await self.sio.emit(
                "code:error", {"error": f"Tree data error: {e!s}"}, room=sid
            )

    async def handle_clear_cache(self, sid: str, data: Dict):
        """Handle cache clearing request.

        Args:
            sid: Socket.IO session ID
            data: Request data
        """
        try:
            cache_type = data.get("type", "all")  # all, file, directory

            if cache_type == "all":
                self.analysis_cache.clear()
                self.logger.info("All analysis cache cleared")
            elif cache_type == "file":
                keys_to_remove = [
                    k for k in self.analysis_cache if k.startswith("file:")
                ]
                for key in keys_to_remove:
                    del self.analysis_cache[key]
                self.logger.info("File analysis cache cleared")
            elif cache_type == "directory":
                keys_to_remove = [
                    k for k in self.analysis_cache if k.startswith("dir:")
                ]
                for key in keys_to_remove:
                    del self.analysis_cache[key]
                self.logger.info("Directory analysis cache cleared")

            await self.sio.emit("code:cache:cleared", {"type": cache_type}, room=sid)

        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
            await self.sio.emit(
                "code:error", {"error": f"Cache clear error: {e!s}"}, room=sid
            )

    async def _analyze_file_async(self, file_path: str) -> Optional[Dict]:
        """Perform file analysis asynchronously.

        Args:
            file_path: Path to file to analyze

        Returns:
            Analysis result or None if failed
        """
        try:
            # Run analysis in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self.analyzer.analyze_file, file_path
            )

        except Exception as e:
            self.logger.error(f"Error in async file analysis: {e}")
            return None

    async def _build_directory_tree_async(
        self, dir_path: str, max_depth: int
    ) -> Optional[Dict]:
        """Build directory tree asynchronously.

        Args:
            dir_path: Path to directory
            max_depth: Maximum depth to analyze

        Returns:
            Tree result or None if failed
        """
        try:
            # Run tree building in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self.builder.build_tree, dir_path, max_depth
            )

        except Exception as e:
            self.logger.error(f"Error in async directory tree building: {e}")
            return None

    async def _get_tree_data_async(self, path: str, format_type: str) -> Optional[Dict]:
        """Get tree data in specified format asynchronously.

        Args:
            path: Path to analyze
            format_type: Format for tree data (d3, json, etc.)

        Returns:
            Tree data or None if failed
        """
        try:
            # For now, use directory analysis
            # TODO: Add format-specific tree generation
            return await self._build_directory_tree_async(path, 3)

        except Exception as e:
            self.logger.error(f"Error getting tree data: {e}")
            return None
