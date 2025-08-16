"""
Infrastructure Services Module
=============================

This module contains infrastructure-related services including
logging, monitoring, and system health management.

Part of TSK-0046: Service Layer Architecture Reorganization

Services:
- LoggingService: Centralized logging with structured output
- HealthMonitor: System health monitoring and alerting
- MemoryGuardian: Memory monitoring and process restart management
"""

from .logging import LoggingService
from .monitoring import AdvancedHealthMonitor as HealthMonitor
from .memory_guardian import MemoryGuardian

__all__ = [
    'LoggingService',
    'HealthMonitor',
    'MemoryGuardian',
]