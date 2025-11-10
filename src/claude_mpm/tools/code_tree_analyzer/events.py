#!/usr/bin/env python3
"""
Events Module
=============

Handles event emission for code tree analysis progress updates.

WHY: Decouples event emission from analysis logic, allowing
flexible event handling and real-time UI updates.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from ...core.logging_config import get_logger
from ..code_tree_events import CodeTreeEventEmitter
from .models import CodeNode


class EventManager:
    """Manages event emission during code tree analysis."""

    def __init__(self, emitter: Optional[CodeTreeEventEmitter] = None):
        """Initialize event manager.

        Args:
            emitter: Optional event emitter
        """
        self.logger = get_logger(__name__)
        self.emitter = emitter

    def emit_analysis_start(self, path: Path, language: str) -> None:
        """Emit analysis start event.

        Args:
            path: File path being analyzed
            language: Programming language
        """
        if self.emitter:
            self.emitter.emit(
                "info",
                {
                    "type": "analysis.start",
                    "file": str(path),
                    "language": language,
                    "message": f"Analyzing: {path.name}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

    def emit_cache_hit(self, path: Path) -> None:
        """Emit cache hit event.

        Args:
            path: File path with cache hit
        """
        if self.emitter:
            self.emitter.emit(
                "info",
                {
                    "type": "cache.hit",
                    "file": str(path),
                    "message": f"Using cached analysis for {path.name}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

    def emit_cache_miss(self, path: Path) -> None:
        """Emit cache miss event.

        Args:
            path: File path with cache miss
        """
        if self.emitter:
            self.emitter.emit(
                "info",
                {
                    "type": "cache.miss",
                    "file": str(path),
                    "message": f"Cache miss, analyzing fresh: {path.name}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

    def emit_parsing_start(self, path: Path) -> None:
        """Emit parsing start event.

        Args:
            path: File path being parsed
        """
        if self.emitter:
            self.emitter.emit(
                "info",
                {
                    "type": "analysis.parse",
                    "file": str(path),
                    "message": f"Parsing file content: {path.name}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

    def emit_node_found(self, node: CodeNode, path: Path) -> None:
        """Emit node found event.

        Args:
            node: CodeNode that was found
            path: File path containing the node
        """
        if self.emitter:
            self.emitter.emit(
                "info",
                {
                    "type": f"analysis.{node.node_type}",
                    "name": node.name,
                    "file": str(path),
                    "line_start": node.line_start,
                    "complexity": node.complexity,
                    "message": f"Found {node.node_type}: {node.name}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

    def emit_analysis_complete(
        self, path: Path, filtered_nodes: List[dict], duration: float
    ) -> None:
        """Emit analysis complete event.

        Args:
            path: File path that was analyzed
            filtered_nodes: List of filtered node dictionaries
            duration: Analysis duration in seconds
        """
        if not self.emitter:
            return

        stats = self._calculate_node_stats(filtered_nodes)
        self.emitter.emit(
            "info",
            {
                "type": "analysis.complete",
                "file": str(path),
                "stats": stats,
                "duration": duration,
                "message": f"Analysis complete: {stats['classes']} classes, {stats['functions']} functions, {stats['methods']} methods",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        self.emitter.emit_file_analyzed(str(path), filtered_nodes, duration)

    def _calculate_node_stats(self, filtered_nodes: List[dict]) -> dict:
        """Calculate statistics from filtered nodes.

        Args:
            filtered_nodes: List of filtered node dictionaries

        Returns:
            Dictionary of node statistics
        """
        classes_count = sum(1 for n in filtered_nodes if n["type"] == "class")
        functions_count = sum(1 for n in filtered_nodes if n["type"] == "function")
        methods_count = sum(1 for n in filtered_nodes if n["type"] == "method")
        return {
            "classes": classes_count,
            "functions": functions_count,
            "methods": methods_count,
            "total_nodes": len(filtered_nodes),
        }
