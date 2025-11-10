#!/usr/bin/env python3
"""
Code Tree Analyzer
==================

Analyzes source code using AST to extract structure and metrics,
supporting multiple languages and emitting incremental events for visualization.

This module has been refactored from a single 1,825-line file into focused,
maintainable components while preserving complete backward compatibility.

Public API:
-----------
- CodeTreeAnalyzer: Main analyzer class
- CodeNode: Data structure for code nodes
- GitignoreManager: Gitignore pattern matching
- PythonAnalyzer: Python AST analysis
- MultiLanguageAnalyzer: Multi-language support

Example Usage:
--------------
    from claude_mpm.tools.code_tree_analyzer import CodeTreeAnalyzer

    analyzer = CodeTreeAnalyzer(emit_events=True)
    result = analyzer.analyze_directory(Path("/path/to/code"))
    print(result['stats'])
"""

# Public API - Backward compatible imports
from .core import CodeTreeAnalyzer
from .gitignore import GitignoreManager
from .models import CodeNode
from .multilang_analyzer import MultiLanguageAnalyzer
from .python_analyzer import PythonAnalyzer

__all__ = [
    "CodeNode",
    "CodeTreeAnalyzer",
    "GitignoreManager",
    "MultiLanguageAnalyzer",
    "PythonAnalyzer",
]

# Version info
__version__ = "2.0.0"  # Major refactoring while maintaining API compatibility
