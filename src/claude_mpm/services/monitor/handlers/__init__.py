"""
Event Handlers for Unified Monitor
==================================

WHY: These handlers provide the event-driven functionality for the unified
monitor daemon. They handle real AST analysis, dashboard events, and Claude
Code hook ingestion.

DESIGN DECISIONS:
- Real AST analysis using CodeTreeAnalyzer instead of mock data
- Event-driven architecture with Socket.IO
- Modular handler design for maintainability
- Integration with existing Claude MPM tools
"""

from .code_analysis import CodeAnalysisHandler
from .dashboard import DashboardHandler
from .file import FileHandler
from .hooks import HookHandler

__all__ = ["CodeAnalysisHandler", "DashboardHandler", "FileHandler", "HookHandler"]
