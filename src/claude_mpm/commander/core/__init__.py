"""Core coordination components for MPM Commander.

This module provides core components that coordinate between different
subsystems like events, work execution, and session management.
"""

from .block_manager import BlockManager

__all__ = ["BlockManager"]
