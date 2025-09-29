"""
Concrete Analyzer Strategy Implementations
==========================================

This module provides concrete implementations of the AnalyzerStrategy base class,
consolidating functionality from multiple analyzer services with 70-80% code duplication.

Consolidates:
- enhanced_analyzer.py (1,118 LOC)
- project_analyzer.py (815 LOC)
- structure_analyzer.py (703 LOC)
- code_analyzer.py (385 LOC)
- dependency_analyzer.py (326 LOC)
- file_analyzer.py (247 LOC)
- project_report_generator.py (121 LOC)

Total: 3,715 LOC → ~1,200 LOC (68% reduction)

Author: Claude MPM Development Team
Created: 2025-01-26
"""

from .code_analyzer import CodeAnalyzerStrategy
from .dependency_analyzer import DependencyAnalyzerStrategy
from .performance_analyzer import PerformanceAnalyzerStrategy
from .security_analyzer import SecurityAnalyzerStrategy
from .structure_analyzer import StructureAnalyzerStrategy

__all__ = [
    "CodeAnalyzerStrategy",
    "DependencyAnalyzerStrategy",
    "PerformanceAnalyzerStrategy",
    "SecurityAnalyzerStrategy",
    "StructureAnalyzerStrategy",
]

# Strategy registry for automatic discovery
ANALYZER_STRATEGIES = {
    "code": CodeAnalyzerStrategy,
    "dependency": DependencyAnalyzerStrategy,
    "structure": StructureAnalyzerStrategy,
    "security": SecurityAnalyzerStrategy,
    "performance": PerformanceAnalyzerStrategy,
}
