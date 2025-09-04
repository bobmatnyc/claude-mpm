"""
Daemon Management for Unified Monitor
=====================================

WHY: These modules provide daemon lifecycle management, health monitoring,
and process supervision for the unified monitor daemon.

DESIGN DECISIONS:
- Proper daemon process management with PID files
- Health monitoring and auto-restart capabilities
- Graceful shutdown and cleanup
- Production-ready daemon operation
"""

from .health import HealthMonitor
from .lifecycle import DaemonLifecycle

__all__ = ["DaemonLifecycle", "HealthMonitor"]
