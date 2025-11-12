#!/usr/bin/env python3
"""
Analysis Module
===============

Coordinates file analysis across different language analyzers.

WHY: Centralizes file analysis logic and result processing,
separating it from directory traversal and caching concerns.
"""

import time
from pathlib import Path
from typing import Dict, List, Tuple

from ...core.logging_config import get_logger
from .cache import CacheManager
from .events import EventManager
from .models import CodeNode
from .multilang_analyzer import MultiLanguageAnalyzer
from .python_analyzer import PythonAnalyzer


class FileAnalyzer:
    """Coordinates file analysis using appropriate language analyzers."""

    def __init__(
        self,
        python_analyzer: PythonAnalyzer,
        multilang_analyzer: MultiLanguageAnalyzer,
        cache_manager: CacheManager,
        event_manager: EventManager,
    ):
        """Initialize file analyzer.

        Args:
            python_analyzer: Python analyzer instance
            multilang_analyzer: Multi-language analyzer instance
            cache_manager: Cache manager instance
            event_manager: Event manager instance
        """
        self.logger = get_logger(__name__)
        self.python_analyzer = python_analyzer
        self.multilang_analyzer = multilang_analyzer
        self.cache_manager = cache_manager
        self.event_manager = event_manager

    def analyze_file(self, file_path: str) -> Dict[str, any]:
        """Analyze a specific file and return its AST structure.

        Args:
            file_path: Path to file to analyze

        Returns:
            Dictionary with file analysis results
        """
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return {"error": f"Invalid file: {file_path}"}

        language = self._get_language(path)
        self.event_manager.emit_analysis_start(path, language)

        # Check cache
        cache_key = self.cache_manager.get_cache_key(path)

        if cached_nodes := self.cache_manager.get(cache_key):
            self.event_manager.emit_cache_hit(path)
            filtered_nodes = self._filter_nodes(cached_nodes)
        else:
            _nodes, filtered_nodes, duration = self._analyze_and_cache_file(
                path, language, cache_key
            )
            self.event_manager.emit_analysis_complete(path, filtered_nodes, duration)

        # Prepare final data structures
        final_nodes = filtered_nodes if filtered_nodes else []
        elements = self._convert_nodes_to_elements(final_nodes)

        return self._build_result(file_path, language, final_nodes, elements)

    def _analyze_and_cache_file(
        self, path: Path, language: str, cache_key: str
    ) -> Tuple[List[CodeNode], List[dict], float]:
        """Analyze file content and cache results.

        Args:
            path: File path
            language: Programming language
            cache_key: Cache key for storing results

        Returns:
            Tuple of (all_nodes, filtered_nodes, duration)
        """
        self.event_manager.emit_cache_miss(path)
        self.event_manager.emit_parsing_start(path)

        # Select analyzer based on language
        analyzer = self._select_analyzer(language)

        # Perform analysis
        start_time = time.time()
        nodes = analyzer.analyze_file(path) if analyzer else []
        duration = time.time() - start_time

        # Cache results
        self.cache_manager.set(cache_key, nodes)

        # Filter and process nodes
        filtered_nodes = self._filter_and_emit_nodes(nodes, path)

        return nodes, filtered_nodes, duration

    def _select_analyzer(self, language: str):
        """Select appropriate analyzer for language.

        Args:
            language: Programming language

        Returns:
            Analyzer instance or None
        """
        if language == "python":
            return self.python_analyzer
        if language in {"javascript", "typescript"}:
            return self.multilang_analyzer
        return self.multilang_analyzer

    def _filter_nodes(self, nodes: List[CodeNode]) -> List[dict]:
        """Filter nodes without emitting events.

        Args:
            nodes: List of CodeNode objects

        Returns:
            List of filtered node dictionaries
        """
        return [self._node_to_dict(n) for n in nodes if not self._is_internal_node(n)]

    def _filter_and_emit_nodes(self, nodes: List[CodeNode], path: Path) -> List[dict]:
        """Filter nodes and emit events for each.

        Args:
            nodes: List of CodeNode objects
            path: File path being analyzed

        Returns:
            List of filtered node dictionaries
        """
        filtered_nodes = []
        for node in nodes:
            if not self._is_internal_node(node):
                self.event_manager.emit_node_found(node, path)
                filtered_nodes.append(self._node_to_dict(node))
        return filtered_nodes

    def _node_to_dict(self, node: CodeNode) -> dict:
        """Convert CodeNode to dictionary.

        Args:
            node: CodeNode object

        Returns:
            Dictionary representation
        """
        return {
            "name": node.name,
            "type": node.node_type,
            "line_start": node.line_start,
            "line_end": node.line_end,
            "complexity": node.complexity,
            "has_docstring": node.has_docstring,
            "signature": node.signature,
        }

    def _convert_nodes_to_elements(self, final_nodes: List[dict]) -> List[dict]:
        """Convert nodes to elements format for dashboard.

        Args:
            final_nodes: List of node dictionaries

        Returns:
            List of element dictionaries
        """
        elements = []
        for node in final_nodes:
            element = {
                "name": node["name"],
                "type": node["type"],
                "line": node["line_start"],
                "complexity": node["complexity"],
                "signature": node.get("signature", ""),
                "has_docstring": node.get("has_docstring", False),
            }
            if node["type"] == "class":
                element["methods"] = []
            elements.append(element)
        return elements

    def _build_result(
        self,
        file_path: str,
        language: str,
        final_nodes: List[dict],
        elements: List[dict],
    ) -> dict:
        """Build final result dictionary.

        Args:
            file_path: File path
            language: Programming language
            final_nodes: List of node dictionaries
            elements: List of element dictionaries

        Returns:
            Complete result dictionary
        """
        return {
            "path": file_path,
            "language": language,
            "nodes": final_nodes,
            "elements": elements,
            "complexity": sum(e["complexity"] for e in elements),
            "lines": len(elements),
            "stats": {
                "classes": len([e for e in elements if e["type"] == "class"]),
                "functions": len([e for e in elements if e["type"] == "function"]),
                "methods": len([e for e in elements if e["type"] == "method"]),
                "variables": len([e for e in elements if e["type"] == "variable"]),
                "imports": len([e for e in elements if e["type"] == "import"]),
                "total": len(elements),
            },
        }

    def _is_internal_node(self, node: CodeNode) -> bool:
        """Check if node is an internal function that should be filtered.

        Args:
            node: CodeNode to check

        Returns:
            True if node should be filtered out
        """
        # Don't filter classes - always show them
        if node.node_type == "class":
            return False

        # Don't filter variables or imports - they're useful for tree view
        if node.node_type in ["variable", "import"]:
            return False

        name_lower = node.name.lower()

        # Filter only very specific internal patterns
        # Be more conservative - only filter obvious internal handlers
        if name_lower.startswith(("handle_", "on_")):
            return True

        # Filter Python magic methods except important ones
        if name_lower.startswith("__") and name_lower.endswith("__"):
            # Keep important magic methods
            important_magic = [
                "__init__",
                "__call__",
                "__enter__",
                "__exit__",
                "__str__",
                "__repr__",
            ]
            return node.name not in important_magic

        # Filter very generic getters/setters only if they're trivial
        if (name_lower.startswith(("get_", "set_"))) and len(node.name) <= 8:
            return True

        # Don't filter single underscore functions - they're often important
        # (like _setup_logging, _validate_input, etc.)
        return False

    def _get_language(self, file_path: Path) -> str:
        """Determine language from file extension.

        Args:
            file_path: Path to file

        Returns:
            Language string
        """
        ext = file_path.suffix.lower()
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".mjs": "javascript",
            ".cjs": "javascript",
        }
        return language_map.get(ext, "unknown")
