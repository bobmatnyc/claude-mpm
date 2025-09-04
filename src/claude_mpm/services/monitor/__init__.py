"""
Unified Monitor Service for Claude MPM
=====================================

WHY: This module provides a single, stable daemon process that combines all
monitoring functionality into one cohesive service. It replaces the multiple
competing server implementations with a unified solution.

DESIGN DECISIONS:
- Single process handles HTTP dashboard, Socket.IO events, and real AST analysis
- Uses proven aiohttp + socketio foundation
- Integrates real CodeTreeAnalyzer instead of mock data
- Built for daemon operation with proper lifecycle management
- Single port (8765) for all functionality
"""

from .daemon import UnifiedMonitorDaemon
from .server import UnifiedMonitorServer

__all__ = ["UnifiedMonitorDaemon", "UnifiedMonitorServer"]
